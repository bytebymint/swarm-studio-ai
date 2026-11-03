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

    def build_ui(self):
        self.build_supporting_widgets()
        # Keep the existing project and diagnostic widgets available on demand,
        # but give the entire main workspace to the browser and one bottom dock.
        self.utility = self.takeCentralWidget()
        self.utility.setParent(self)
        self.utility.hide()
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack, 1)
        self.stack.installEventFilter(self)
        self.stack.currentChanged.connect(lambda _: QTimer.singleShot(0, self.resize_canvases))

        self.diagnostics = QDialog(self)
        self.diagnostics.setWindowTitle('Project diagnostics')
        self.diagnostics.resize(820, 620)
        details = QHBoxLayout(self.diagnostics)
        details.addWidget(self.left, 1)
        details.addWidget(self.right, 2)
        self.left.show()
        self.right.show()

        self.canvas_options = QDialog(self)
        self.canvas_options.setWindowTitle('Canvas options')
        self.canvas_options.resize(780, 150)
        options = QVBoxLayout(self.canvas_options)
        options.addWidget(self.center)
        self.tabs.hide()
        self.viewport.addItem('Window · fill available space')
        self.viewport.setCurrentIndex(5 if self.settings.values['viewport_mode'] == 'window' else 4)
        self.zoom.currentTextChanged.connect(self.resize_canvases)

        self.bottom = QFrame()
        self.bottom.setObjectName('focusdock')
        dock = QVBoxLayout(self.bottom)
        dock.setContentsMargins(8, 5, 8, 4)
        dock.setSpacing(3)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.studio_button = QPushButton('Studio')
        self.studio_button.setAccessibleName('Studio menu: projects, settings, canvas and diagnostics')
        self.studio_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.studio_menu = QMenu(self.studio_button)
        self.studio_button.setMenu(self.studio_menu)
        self.studio_menu.addAction('Try offline demo', self.open_demo)
        self.studio_menu.addSeparator()
        self.studio_menu.addAction('New project', self.new_project)
        self.studio_menu.addAction('Open saved project…', self.open_project)
        self.studio_menu.addAction('Settings…', self.show_settings)
        self.studio_menu.addAction('Canvas options…', self.canvas_options.show)
        self.studio_menu.addAction('Project diagnostics…', self.diagnostics.show)
        self.timeline_action = self.studio_menu.addAction('Show activity timeline')
        self.timeline_action.setCheckable(True)
        self.timeline_action.toggled.connect(self.toggle_timeline)
        playback = self.studio_menu.addMenu('Playback')
        playback.addAction('Step back two seconds', self.step_back.click)
        playback.addAction('Step forward half a second', self.step_forward.click)
        playback.addAction('Stop / cancel', self.cancel)
        playback.addAction('Run comparison', self.compare_button.click)
        navigation = self.studio_menu.addMenu('Navigation')
        navigation.addAction('Back', self.back.click)
        navigation.addAction('Forward', self.forward.click)
        navigation.addAction('Reload website', self.reload.click)
        self.studio_menu.addAction('Fullscreen (F11)', self.toggle_presentation)
        self.studio_menu.addAction('Cinematic recording…', self.show_recording)
        row.addWidget(self.studio_button)
        self.url.setMinimumWidth(120)
        row.addWidget(self.url, 1)
        self.go.setText('Open')
        row.addWidget(self.go)
        row.addWidget(self.initialize)
        self.mode = QComboBox()
        self.mode.addItems(['Original', 'Swarm', 'Reconstruction', 'Comparison'])
        self.mode.setAccessibleName('Canvas mode')
        self.mode.setFixedWidth(132)
        self.mode.currentIndexChanged.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.mode.setCurrentIndex)
        row.addWidget(self.mode)
        row.addWidget(self.play_button)
        row.addWidget(self.replay_button)
        self.speed.setFixedWidth(62)
        row.addWidget(self.speed)
        self.tour.setText('Tour')
        self.tour.setToolTip('Cinematic Auto Tour follows construction through the whole page')
        row.addWidget(self.tour)
        row.addWidget(self.audio)
        self.record_button=button('Record',self.show_recording,'Save a cinematic MP4 with smooth automatic zoom')
        self.record_button.setEnabled(False)
        row.addWidget(self.record_button)
        row.addWidget(self.export_button)
        dock.addLayout(row)
        self.status_text = QLabel('Open a website, or choose Studio > Try offline demo.')
        self.status_text.setObjectName('muted')
        self.status_text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 2, 0)
        footer.addWidget(self.status_text, 1)
        footer.addWidget(self.position)
        dock.addLayout(footer)
        dock.addWidget(self.progress)
        dock.addWidget(self.timeline)
        self.timeline.hide()
        layout.addWidget(self.bottom)
        # The old banner becomes a message source for the compact dock instead
        # of permanently consuming a row above the canvas.
        self.notice = NoticeLabel(self.utility)
        self.notice.message.connect(self.status)
        self.notice.hide()
        self.statusBar().hide()
        QTimer.singleShot(0, self.resize_canvases)
