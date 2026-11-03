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
for destination, source, kind in a.binaries:
    if 'OpenAI.Codex' in source:
        raise RuntimeError('Build rejected unrelated host runtime DLL: ' + source)
# Windows 11 supplies the unversioned ICU facade required by QtCore. It must
# resolve from System32, never a renamed third-party ICU build on PATH.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() not in {'icuuc.dll','icuin.dll','icu.dll'} and not Path(entry[0]).name.lower().startswith('icudt')]
