"""Create a compact, exactly timed README GIF from a local Swarm movie."""
import argparse
import json
from pathlib import Path

import av
from PIL import Image, ImageDraw


def frame_at(movie, stream, seconds):
    movie.seek(max(0,int(seconds/stream.time_base)),stream=stream,backward=True)
    for frame in movie.decode(stream):
        if frame.time is not None and frame.time+1e-6>=seconds:
            return frame.to_image().convert('RGB')
    raise ValueError(f'The video has no frame at {seconds:g} seconds.')
