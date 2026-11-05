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
app=QApplication([])
from app.desktop import MainWindow
root=Path('test-results/focus-layout').resolve();root.mkdir(parents=True,exist_ok=True)
window=MainWindow(root/'data');window.showMaximized()
def wait(predicate,timeout=60):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError(window.notice.text())
