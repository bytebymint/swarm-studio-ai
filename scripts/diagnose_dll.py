"""Inspect bundled import/export mismatches without executing downloaded code."""
from pathlib import Path
import pefile
root=Path('dist/SwarmStudio/_internal')
folders=[root,root/'shiboken6',root/'PySide6',Path('C:/Windows/System32')]
targets=[root/'PySide6/QtCore.pyd',root/'PySide6/Qt6Core.dll',root/'PySide6/pyside6.abi3.dll',root/'shiboken6/shiboken6.abi3.dll',root/'PySide6/MSVCP140.dll']
