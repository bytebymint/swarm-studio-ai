import json
import os
import threading
import zipfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.reconstruction import reconstruct_collection


class BuildWorker(QThread):
    progress = Signal(str, str)
    ready = Signal(object, object)
    error = Signal(str)

    def __init__(self, capture, root, settings):
        super().__init__()
        self.capture, self.root, self.settings = capture, root, settings
        self.cancel_event = threading.Event()
