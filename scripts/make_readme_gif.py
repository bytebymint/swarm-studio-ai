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


def contact_sheet(source, destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with av.open(str(source)) as movie:
        stream=movie.streams.video[0]
        duration=float(stream.duration*stream.time_base) if stream.duration else movie.duration/av.time_base
        times=[min(duration-.1,5+10*i) for i in range(min(10,max(1,int(duration/10))))]
        sheet=Image.new('RGB',(960,290*((len(times)+1)//2)),'#15171b')
        draw=ImageDraw.Draw(sheet)
        for i,seconds in enumerate(times):
            picture=frame_at(movie,stream,seconds)
            picture.thumbnail((480,264),Image.Resampling.LANCZOS)
            left,top=(i%2)*480,(i//2)*290
            sheet.paste(picture,(left,top))
            draw.text((left+12,top+268),f'{seconds:.1f} s',fill='white')
        sheet.save(destination)
