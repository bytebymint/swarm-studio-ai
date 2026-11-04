"""Create a compact, exactly timed README GIF from a local Swarm movie."""
import argparse
import json
from pathlib import Path

import av
from PIL import Image, ImageDraw
