import asyncio
import hashlib
import mimetypes
import re
import threading
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote

import httpx

from app.urls import resource_url

URL_PATTERN = re.compile(r'''url\(\s*(["']?)(.*?)\1\s*\)''', re.I)
IMPORT_PATTERN = re.compile(r'''@import\s+(?:url\(\s*)?["']([^"']+)["']\s*\)?[^;]*;''', re.I)


class AssetCollector:
    def __init__(self, root, settings, cancel=None, progress=None):
        self.root = Path(root)
        self.settings = settings
        self.cancel = cancel or threading.Event()
        self.progress = progress or (lambda *_: None)
        self.mapping = {}
        self.warnings = []
        self.total = 0
        self.limit = int(settings.get("max_asset_mb", 16)) * 1024 * 1024
        self.total_limit = int(settings.get("max_total_mb", 160)) * 1024 * 1024
        self.semaphore = asyncio.Semaphore(6)
        self.inflight = {}
