"""Exercise the real director, compositor, MP4/audio encoder and cancellation."""
import json
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
