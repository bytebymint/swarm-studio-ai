# PyInstaller's official PySide6 hook collects QtWebEngineProcess and Chromium resources.
from pathlib import Path
import os
import sys
root = Path(SPECPATH)
portable = os.environ.get('SWARM_STUDIO_ONEFILE') == '1'
bundle_data = [(str(root / 'web'), 'web')]
if portable:
    browser_root=root/'build/portable-browsers'
    notices=root/'build/portable-notices'
    if not browser_root.is_dir() or not notices.is_dir():
        raise RuntimeError('Run scripts/build_windows.ps1 -Portable to prepare browser and notices first.')
    bundle_data += [(str(browser_root),'browsers'),(str(notices),'Notices'),
                    (str(root/'docs'),'docs'),(str(root/'README.md'),'.'),
                    (str(root/'LICENSE'),'.'),(str(root/'THIRD_PARTY_NOTICES.md'),'.')]
# Host tools can ship incompatible unversioned ICU DLLs. Restrict the native
# library search path to our Python/Qt environment and the target Windows OS.
python_root = Path(sys.base_prefix)
site_root = root / '.venv' / 'Lib' / 'site-packages'
windows_root = Path(os.environ.get('SystemRoot', 'C:/Windows'))
os.environ['PATH'] = os.pathsep.join(map(str, [python_root, python_root/'DLLs',
    site_root/'PySide6', site_root/'shiboken6', windows_root/'System32', windows_root]))
a = Analysis([str(root / 'main.py')], pathex=[str(root)],
             binaries=[], datas=bundle_data,
             hiddenimports=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebChannel'],
             excludes=['app.local_credentials','pytest','tkinter','PySide6.QtPdf','PySide6.QtPdfWidgets'],
             noarchive=False)
for destination, source, kind in a.binaries:
    if 'OpenAI.Codex' in source:
        raise RuntimeError('Build rejected unrelated host runtime DLL: ' + source)
# Windows 11 supplies the unversioned ICU facade required by QtCore. It must
# resolve from System32, never a renamed third-party ICU build on PATH.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() not in {'icuuc.dll','icuin.dll','icu.dll'} and not Path(entry[0]).name.lower().startswith('icudt')]
pyz = PYZ(a.pure)
if portable:
    a.datas=[entry for entry in a.datas if '/.links/' not in entry[0].replace('\\','/')]
    exe = EXE(pyz,a.scripts,a.binaries,a.datas,[],name='SwarmStudioAI-Portable',
              debug=False,bootloader_ignore_signals=False,strip=False,upx=False,
              console=False,disable_windowed_traceback=False,icon=str(root/'assets/studio.ico'))
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SwarmStudio',
              debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
              console=False, disable_windowed_traceback=False, icon=str(root/'assets/studio.ico'))
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SwarmStudio')
