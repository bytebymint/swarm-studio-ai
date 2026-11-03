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
os.environ['PATH'] = os.pathsep.join(map(str, [python_root, python_root/'DLLs',
    site_root/'PySide6', site_root/'shiboken6', windows_root/'System32', windows_root]))
a = Analysis([str(root / 'main.py')], pathex=[str(root)],
             binaries=[], datas=[(str(root / 'web'), 'web')],
             hiddenimports=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebChannel'],
             excludes=['pytest','tkinter','PySide6.QtPdf','PySide6.QtPdfWidgets'],
             noarchive=False)
