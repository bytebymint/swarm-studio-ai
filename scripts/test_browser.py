"""Independent Chrome tests of real capture, export, scheduling and reference media."""
import json
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright

from app.config import WEB
from app.reconstruction import reconstruct_collection
from app.server import PreviewServer
from app.validation import compare_images
