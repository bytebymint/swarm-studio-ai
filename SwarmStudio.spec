# PyInstaller's official PySide6 hook collects QtWebEngineProcess and Chromium resources.
from pathlib import Path
import os
import sys
root = Path(SPECPATH)
# Host tools can ship incompatible unversioned ICU DLLs. Restrict the native
# library search path to our Python/Qt environment and the target Windows OS.
python_root = Path(sys.base_prefix)
site_root = root / '.venv' / 'Lib' / 'site-packages'
windows_root = Path(os.environ.get('SystemRoot', 'C:/Windows'))
