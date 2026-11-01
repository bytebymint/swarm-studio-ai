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

    async def fetch(self, client, url, depth=0):
        url = url.split('#')[0]
        if url in self.mapping:
            return self.mapping[url]
        if depth > 5 or self.cancel.is_set():
            return None
        if not resource_url(url):
            self.warnings.append("Skipped unsafe resource address.")
            return None
        if url in self.inflight:
            return await self.inflight[url]
        task = asyncio.create_task(self._fetch(client, url, depth))
        self.inflight[url] = task
        try:
            return await task
        finally:
            self.inflight.pop(url, None)
