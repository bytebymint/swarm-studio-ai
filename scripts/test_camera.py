"""Regression: Auto Tour must visibly scroll, not just complete offscreen tasks."""
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
