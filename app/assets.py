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

    async def _fetch(self, client, url, depth):
        try:
            async with self.semaphore:
                # Fresh unauthenticated requests: cookies and auth are never forwarded.
                for attempt in range(2):
                    try:
                        current = url
                        for _ in range(6):
                            async with client.stream("GET", current, follow_redirects=False, headers={"Cookie": ""}) as response:
                                if response.is_redirect:
                                    current = urljoin(current, response.headers.get("location", ""))
                                    if not resource_url(current):
                                        raise ValueError("Unsafe resource redirect")
                                    continue
                                response.raise_for_status()
                                ctype = response.headers.get("content-type", "").split(';')[0].lower()
                                if not (ctype.startswith(('image/', 'font/')) or ctype in {'text/css', 'application/font-woff', 'application/octet-stream', 'application/vnd.ms-fontobject', 'application/x-font-ttf'}):
                                    raise ValueError("Unsupported asset type " + ctype)
                                payload = bytearray()
                                async for chunk in response.aiter_bytes():
                                    if self.cancel.is_set():
                                        return None
                                    if len(payload) + len(chunk) > self.limit or self.total + len(chunk) > self.total_limit:
                                        raise ValueError("Asset size budget exceeded")
                                    payload.extend(chunk)
                                    self.total += len(chunk)
                                break
                        else:
                            raise ValueError("Too many redirects")
                        break
                    except httpx.TransportError:
                        if attempt:
                            raise
                        await asyncio.sleep(.2)
            ext = Path(unquote(urlsplit(url).path)).suffix.lower()
            if not re.fullmatch(r"\.[a-z0-9]{1,6}", ext) or ext in {'.html', '.php', '.js'}:
                ext = mimetypes.guess_extension(ctype) or '.bin'
            category = 'styles' if ctype == 'text/css' else 'fonts' if ctype.startswith('font/') or ext in {'.woff', '.woff2', '.ttf', '.otf'} else 'images'
            name = re.sub(r'[^a-zA-Z0-9_-]', '-', Path(unquote(urlsplit(url).path)).stem)[:45] or 'resource'
            relative = f"assets/{category}/{name}-{hashlib.sha256(url.encode()).hexdigest()[:12]}{ext}"
            self.mapping[url] = relative
            if ctype == 'text/css':
                text = bytes(payload).decode('utf-8', errors='replace')
                # Mapping already exists, so cyclic imports terminate.
                text = await self.rewrite_css(client, text, current, depth + 1, css_file=True)
                payload = text.encode('utf-8')
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            self.progress("asset", relative)
            return relative
        except (httpx.HTTPError, ValueError, OSError) as exc:
            self.mapping.pop(url, None)
            self.warnings.append(f"Asset unavailable: {urlsplit(url).hostname}{urlsplit(url).path[:90]} ({type(exc).__name__}: {str(exc)[:100]})")
            return None

    async def rewrite_css(self, client, css, base, depth=0, css_file=False):
        from posixpath import relpath
        refs = set(m.group(2) for m in URL_PATTERN.finditer(css)) | set(m.group(1) for m in IMPORT_PATTERN.finditer(css))
        replacements = {}
        for ref in refs:
            if ref.startswith(('data:', '#')):
                continue
            absolute = urljoin(base, ref)
            fragment = urlsplit(absolute).fragment
            local = await self.fetch(client, absolute, depth)
            replacements[ref] = (relpath(local, 'assets/styles') if css_file else local) + (('#' + fragment) if fragment else '') if local else ''
        css = URL_PATTERN.sub(lambda m: f'url("{replacements.get(m.group(2), m.group(2))}")', css)
        css = IMPORT_PATTERN.sub(lambda m: f'@import url("{replacements.get(m.group(1), m.group(1))}");' if replacements.get(m.group(1), m.group(1)) else '', css)
        return css

    async def collect(self, capture):
        timeout = httpx.Timeout(12, connect=6)
        async with httpx.AsyncClient(timeout=timeout, trust_env=False, headers={"User-Agent": "SwarmStudio/0.1 local-reconstruction"}) as client:
            # Limit task creation as well as network concurrency.
            resources = capture.get('resources', [])[:1500]
            if len(capture.get('resources', [])) > 1500:
                self.warnings.append('Resource list limited to 1,500 entries.')
            for offset in range(0, len(resources), 24):
                if self.cancel.is_set():
                    break
                await asyncio.gather(*(self.fetch(client, url) for url in resources[offset:offset+24]))
            sheets = []
            for sheet in capture.get('sheets', []):
                if self.cancel.is_set():
                    break
                sheets.append(await self.rewrite_css(client, sheet['text'], sheet['base']))
            computed = await self.rewrite_css(client, capture.get('computedCSS', ''), capture['url'])
            return '\n'.join(sheets), computed
