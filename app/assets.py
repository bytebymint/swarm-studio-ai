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
