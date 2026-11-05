"""Small real-public-URL Qt capture test. Network and GUI access required."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication
