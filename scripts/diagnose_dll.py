"""Inspect bundled import/export mismatches without executing downloaded code."""
from pathlib import Path
import pefile
root=Path('dist/SwarmStudio/_internal')
folders=[root,root/'shiboken6',root/'PySide6',Path('C:/Windows/System32')]
