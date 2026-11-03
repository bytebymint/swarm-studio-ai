import json
import logging
import shutil
import re
from pathlib import Path
from urllib.parse import urlsplit, urldefrag

from PySide6.QtCore import QEvent, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QStackedWidget, QTabBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from app.blueprint import COLORS, NAMES, ROLES
from app.browser import BrowserController, make_player
from app.comparison import ComparisonPanel
from app.config import Settings, WEB
from app.projects import ProjectStore
from app.server import PreviewServer
from app.settings_dialog import SettingsDialog
from app.timeline import Timeline
from app.urls import normalize_url
from app.validation import quality_report
from app.workers import BuildWorker, ExportWorker


def button(text, callback, tooltip=None, primary=False):
    control = QPushButton(text)
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    control.setAccessibleName(tooltip or text)
    if tooltip:
        control.setToolTip(tooltip)
    if primary:
        control.setObjectName('primary')
    control.clicked.connect(callback)
    return control


class NoticeLabel(QLabel):
    message = Signal(str)

    def setText(self, text):
        super().setText(text)
        self.message.emit(text)


class MainWindow(QMainWindow):
    def __init__(self, data_root):
        super().__init__()
        self.root = Path(data_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings = Settings(self.root / 'settings.json')
        self.store = ProjectStore(self.root)
        ui = self.root / 'ui'
        shutil.copytree(WEB, ui, dirs_exist_ok=True)
        self.server = PreviewServer(self.root)
        self.browser = BrowserController(self)
        self.source = self.browser.source
        self.player = make_player(self.browser.profile, self.server.origin)
        self.player.bridge.received.connect(self.engine_event)
        self.player.loadFinished.connect(self.player_loaded)
        self.player.page().renderProcessTerminated.connect(lambda *_: self.fail('The animation renderer stopped. Open the project again to recover.'))
        self.project = None
        self.blueprint = None
        self.metadata = None
        self.worker = self.export_worker = self.recording_worker = None
        self.pending_load = False
        self.loading_player = False
        self.engine_ready = False
        self.pending_comparison = False
        self.player_ready = False
        self.busy = False
        self.paused = False
        self.closing = False
        self.fit = True
        self.compare_busy = False
        self.comparison_viewport = False
        self.crawling = False
        self.setWindowTitle('SWARM STUDIO | Website reconstruction desk')
        self.setWindowIcon(QIcon(str(WEB/'studio.svg')))
        self.resize(1600, 1000)
        self.setMinimumSize(960, 540)
        self.setStyleSheet((WEB / 'application.qss').read_text('utf-8'))
        self.build_ui()
        self.browser.error.connect(self.browser_error)
        self.browser.phase.connect(self.status)
        self.browser.capture_ready.connect(self.captured)
        self.browser.navigated.connect(self.navigation_finished)
        self.source.urlChanged.connect(lambda url: self.url.setText(url.toString()))
        self.source.iconChanged.connect(lambda icon: self.go.setIcon(icon))
        self.player.setUrl(QUrl(self.server.url('ui/player.html')))
        self.load_recent()
        self.shortcuts()
