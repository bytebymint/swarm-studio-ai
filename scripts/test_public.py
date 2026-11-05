"""Small real-public-URL Qt capture test. Network and GUI access required."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
from app.desktop import MainWindow

root=Path('test-results/public').resolve();root.mkdir(exist_ok=True)
window=MainWindow(root/'data');window.show()
def wait(predicate,timeout=45):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError(window.notice.text())
