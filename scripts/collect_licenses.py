"""Preserve installed dependency notices alongside the local Windows build."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

root=Path(__file__).resolve().parent.parent
destination=root/'dist/SwarmStudio/Notices'
destination.mkdir(parents=True,exist_ok=True)
names=['PySide6','PySide6_Essentials','PySide6_Addons','PySide6_WebEngine','shiboken6',
       'httpx','httpcore','anyio','h11','idna','certifi','beautifulsoup4','soupsieve',
       'lxml','Pillow','typing_extensions','pyinstaller','playwright','pyee','greenlet','av','numpy']
