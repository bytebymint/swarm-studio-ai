"""Deterministic browser frames, a continuous task-aware lens, and local MP4 encoding."""
import base64
from bisect import bisect_left, bisect_right
import io
import json
import os
import threading
import uuid
from fractions import Fraction
from pathlib import Path

from PySide6.QtCore import QThread, Signal
