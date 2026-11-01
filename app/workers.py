import json
import os
import threading
import zipfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.reconstruction import reconstruct_collection


class BuildWorker(QThread):
    progress = Signal(str, str)
