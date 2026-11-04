"""Preserve installed dependency notices alongside the local Windows build."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

root=Path(__file__).resolve().parent.parent
