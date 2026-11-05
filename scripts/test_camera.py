"""Regression: Auto Tour must visibly scroll, not just complete offscreen tasks."""
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from app.config import WEB
from app.reconstruction import reconstruct
from app.server import PreviewServer

root=Path('test-results/camera').resolve();root.mkdir(parents=True,exist_ok=True)
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
sections=''.join(f'<section style="height:720px;padding:60px;background:{color}"><h2>Section {i+1}</h2><p>Actual section text for the camera to follow.</p><article>Component {i+1}</article></section>' for i,color in enumerate(['#e8e4d9','#cdddcf','#d6d9e9','#e9d9cc','#d5e4e8','#e4decf']))
