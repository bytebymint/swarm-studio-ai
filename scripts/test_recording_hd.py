"""Encode the full demo at the shipping 1080p/60 fps settings after test_recording."""
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import av
from app.config import WEB
from app.recording import render_movie
from app.server import PreviewServer

root=Path('test-results/recording').resolve()
metadata=json.loads((root/'project/metadata/project.json').read_text('utf-8'))
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
server=PreviewServer(root)
last=[-1]
