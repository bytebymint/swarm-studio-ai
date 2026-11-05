"""Real Qt/Chromium integration test. Run from the repository root."""
import json
import os
import sys
import time
import zipfile
import faulthandler
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
