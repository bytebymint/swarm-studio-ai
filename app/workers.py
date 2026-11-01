import json
import os
import threading
import zipfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.reconstruction import reconstruct_collection


class BuildWorker(QThread):
    progress = Signal(str, str)
    ready = Signal(object, object)
    error = Signal(str)

    def __init__(self, capture, root, settings):
        super().__init__()
        self.capture, self.root, self.settings = capture, root, settings
        self.cancel_event = threading.Event()

    def run(self):
        try:
            captures = self.capture if isinstance(self.capture, list) else [self.capture]
            metadata, blueprint = reconstruct_collection(captures, self.root, self.settings, self.cancel_event, self.progress.emit)
            self.ready.emit(metadata, blueprint)
        except InterruptedError:
            self.error.emit('Capture cancelled. No project was registered.')
        except Exception as exc:
            import logging
            logging.exception('Reconstruction failed')
            self.error.emit(f'Could not save reconstruction: {type(exc).__name__}: {exc}')


class ExportWorker(QThread):
    ready = Signal(str)
    error = Signal(str)

    def __init__(self, root, destination, settings):
        super().__init__()
        self.root, self.destination, self.settings = Path(root), Path(destination), settings

    def run(self):
        tmp = self.destination.with_suffix('.partial.zip')
        try:
            files = list(self.root.rglob('*'))
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
                for file in files:
                    if not file.is_file() or file.is_symlink():
                        continue
                    rel = file.relative_to(self.root)
                    if rel.parts[0] == 'screenshots' and not self.settings.get('include_screenshots', True):
                        continue
                    if rel.as_posix() == 'metadata/blueprint.json' and not self.settings.get('include_blueprint', True):
                        continue
                    archive.write(file, rel.as_posix())
            os.replace(tmp, self.destination)
            history = self.root / 'metadata/export-history.json'
            from datetime import datetime, timezone
            from app.projects import write_json
            entries = json.loads(history.read_text('utf-8')) if history.exists() else []
            entries.append({'date': datetime.now(timezone.utc).isoformat(), 'filename': self.destination.name})
            write_json(history, entries)
            self.ready.emit(str(self.destination))
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            tmp.unlink(missing_ok=True)
            self.error.emit(f'Export failed: {exc}. Choose a writable folder with enough free space.')
