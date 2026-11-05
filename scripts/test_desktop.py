"""Real Qt/Chromium integration test. Run from the repository root."""
import json
import os
import sys
import time
import zipfile
import faulthandler
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication, QTimer, Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
from app.desktop import MainWindow

output=Path('test-results').resolve();output.mkdir(exist_ok=True)
faulthandler.dump_traceback_later(35, repeat=True)
window=MainWindow(output/'desktop-data')
window.show()
