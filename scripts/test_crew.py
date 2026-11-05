"""Motion/crew contracts: real work, bounded population and layout-stable typing."""
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
