"""Exercise the real director, compositor, MP4/audio encoder and cancellation."""
import json
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import av
import numpy as np
from playwright.sync_api import sync_playwright
from app.config import WEB
from app.reconstruction import reconstruct
from app.recording import render_movie
from app.server import PreviewServer

root=Path('test-results/recording').resolve();root.mkdir(parents=True,exist_ok=True)
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
shutil.copytree(WEB/'demo',root/'fixture',dirs_exist_ok=True)
