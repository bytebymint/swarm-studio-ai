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

    def run(self):
        try:
            captures = self.capture if isinstance(self.capture, list) else [self.capture]
            metadata, blueprint = reconstruct_collection(captures, self.root, self.settings, self.cancel_event, self.progress.emit)
            self.ready.emit(metadata, blueprint)
        except InterruptedError:
            self.error.emit('Capture cancelled. No project was registered.')
        except Exception as exc:
            import logging
            logging.exception('Reconstruction failed')
            self.error.emit(f'Could not save reconstruction: {type(exc).__name__}: {exc}')
