"""Motion/crew contracts: real work, bounded population and layout-stable typing."""
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from PIL import Image
from app.config import WEB
from app.reconstruction import reconstruct
from app.server import PreviewServer

root=Path('test-results/crew').resolve();root.mkdir(parents=True,exist_ok=True)
