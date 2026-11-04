"""Inspect bundled import/export mismatches without executing downloaded code."""
from pathlib import Path
import pefile
root=Path('dist/SwarmStudio/_internal')
folders=[root,root/'shiboken6',root/'PySide6',Path('C:/Windows/System32')]
targets=[root/'PySide6/QtCore.pyd',root/'PySide6/Qt6Core.dll',root/'PySide6/pyside6.abi3.dll',root/'shiboken6/shiboken6.abi3.dll',root/'PySide6/MSVCP140.dll']
for path in targets:
    pe=pefile.PE(str(path),max_symbol_exports=65536)
    for entry in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
        name=entry.dll.decode()
        dependency=next((folder/name for folder in folders if(folder/name).exists()),None)
        if dependency is None:print('MISSING DLL',path.name,name);continue
        dep=pefile.PE(str(dependency),max_symbol_exports=65536)
        exports={item.name for item in getattr(dep,'DIRECTORY_ENTRY_EXPORT',type('X',(),{'symbols':[]})()).symbols}
        missing=[symbol.name.decode() for symbol in entry.imports if symbol.name and symbol.name not in exports]
        if missing:print('MISSING EXPORTS',path.name,'=>',dependency,missing[:20])
