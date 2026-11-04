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

root=Path('test-results/browser').resolve();root.mkdir(parents=True,exist_ok=True)
source=root/'source';source.mkdir(exist_ok=True)
asset=root/'remote-css';asset.mkdir(exist_ok=True)
(asset/'site.css').write_text('body{margin:0;color:#173c33;font:16px/1.5 Arial;background:#f8f5ed} main{padding:40px;max-width:900px} h1{font-size:44px} .cards{display:flex;gap:20px}.card{padding:24px;background:#d9e5cf;border-radius:8px}.hover:hover{color:red}img{width:120px;height:100px}@media(max-width:500px){.cards{display:block}h1{font-size:30px}}')
with (asset/'site.css').open('a') as css:
  css.write('main{background-image:url(image.svg);background-size:40px 40px;background-repeat:no-repeat;background-position:right top}')
