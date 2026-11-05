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
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
shutil.copytree(WEB/'demo',root/'fixture',dirs_exist_ok=True)
source=(root/'fixture/index.html').read_text('utf-8')
source=source.replace('<h1>','<h1 style="background:linear-gradient(90deg,#194837,#7b503c);background-clip:text;-webkit-text-fill-color:transparent">',1)
source=source.replace('<footer id="about">','<hr style="margin:10px 6%;border:0;border-top:1px solid #71857b"><footer id="about">')
(root/'fixture/index.html').write_text(source,'utf-8')
server=PreviewServer(root)
