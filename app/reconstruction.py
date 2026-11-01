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
