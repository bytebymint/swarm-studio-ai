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


class Settings:
    def __init__(self, path):
        self.path = Path(path)
        self.values = DEFAULTS.copy()
        try:
            raw = json.loads(self.path.read_text("utf-8"))
            for key, value in DEFAULTS.items():
                if key in raw and type(raw[key]) is type(value):
                    self.values[key] = raw[key]
        except (OSError, ValueError, TypeError):
            pass
        # Previous versions populated a 24-cursor cloud. Existing settings must
        # also adopt the smaller adaptive crew instead of retaining that default.
        if self.values['agents'] > 12:
            self.values['agents'] = 8
        self.values['agents'] = max(2, self.values['agents'])

    def save(self, values):
        self.values.update({k: v for k, v in values.items() if k in DEFAULTS})
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.values, indent=2), "utf-8")
        tmp.replace(self.path)
