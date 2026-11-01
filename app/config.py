import json
import sys
from pathlib import Path

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
WEB = ROOT / "web"
DEFAULTS = {
    "width": 1280, "height": 800, "timeout": 25, "max_elements": 2500,
    "max_height": 30000, "max_asset_mb": 16, "max_total_mb": 160,
    "lazy_load": True, "agents": 8, "speed": 1.0, "intro": True,
    "reduced_motion": False, "auto_tour": True, "names": True,
    "cursor_size": 1.0, "overlay_opacity": 1.0, "smoothness": 1.0,
    "sound": False, "volume": 0.25, "reduced_audio": False,
    "include_screenshots": True, "include_blueprint": True,
    "export_directory": "", "open_export": False,
    "page_limit": 1, "crawl_depth": 1,
    "viewport_mode": "window",
}
