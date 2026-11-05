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
results=[]


def wait_for(predicate,timeout=40):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents()
        if predicate():return
        time.sleep(.02)  # Release the GIL for HTTP and reconstruction worker threads.
    raise AssertionError('Timed out waiting for desktop state: '+window.notice.text())


def js(code,view=None):
    result=[]
    (view or window.player).page().runJavaScript(code,lambda value:result.append(value))
    wait_for(lambda:bool(result),10)
    return result[0]
