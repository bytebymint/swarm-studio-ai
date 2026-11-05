"""Real native layout and end-to-end playback regression for the canvas-first UI."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
