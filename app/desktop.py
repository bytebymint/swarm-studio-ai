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
