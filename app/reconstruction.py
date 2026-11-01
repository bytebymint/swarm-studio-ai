import asyncio
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.assets import AssetCollector, URL_PATTERN
from app.blueprint import build_blueprint
from app.projects import write_json
from app.urls import resource_url

SECURITY_POLICY = "default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; media-src 'self' data:; script-src 'self'; form-action 'none'; frame-src 'none'; connect-src 'none'; base-uri 'none'"
