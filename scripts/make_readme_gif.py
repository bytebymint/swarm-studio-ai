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


def make_gif(source,destination,start=0,duration=10,fps=20,width=800,colors=128):
    if start<0 or not 1<=duration<=20 or not 1<=fps<=25 or not 320<=width<=1280:
        raise ValueError('Use a nonnegative start, 1–20 seconds, 1–25 fps and width 320–1280.')
    count=round(duration*fps)
    if not 16<=colors<=256:raise ValueError('Choose a palette size between 16 and 256.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with av.open(str(source)) as movie:
        stream=movie.streams.video[0]
        total=float(stream.duration*stream.time_base) if stream.duration else movie.duration/av.time_base
        if start+duration>total+.001:raise ValueError('The selected segment extends beyond the movie.')
        height=round(width*stream.height/stream.width)
        # One palette across the sequence avoids flickering colors between frames.
        atlas=Image.new('RGB',(5*192,3*108))
        for i in range(15):
            thumbnail=frame_at(movie,stream,start+(duration-.1)*i/14)
            thumbnail=thumbnail.resize((192,108),Image.Resampling.LANCZOS)
            atlas.paste(thumbnail,((i%5)*192,(i//5)*108))
        palette=atlas.quantize(colors=colors,method=Image.Quantize.MEDIANCUT)
        frames=[]
        movie.seek(max(0,int(start/stream.time_base)),stream=stream,backward=True)
        for frame in movie.decode(stream):
            if frame.time is None:continue
            while len(frames)<count and frame.time+1e-6>=start+len(frames)/fps:
                image=frame.to_image().convert('RGB').resize((width,height),Image.Resampling.LANCZOS)
                frames.append(image.quantize(palette=palette,dither=Image.Dither.NONE))
            if len(frames)==count:break
        if len(frames)!=count:raise ValueError('The movie ended before the selected segment was complete.')
    delays=[round((i+1)*100/fps)*10-round(i*100/fps)*10 for i in range(count)]
    frames[0].save(destination,save_all=True,append_images=frames[1:],duration=delays,
                   loop=0,optimize=True,disposal=1)
    with Image.open(destination) as gif:
        actual_duration=0
        for i in range(gif.n_frames):
            gif.seek(i);actual_duration+=gif.info.get('duration',0)
        assert actual_duration==round(duration*1000),(actual_duration,duration)
        result={'filename':destination.name,'width':gif.width,'height':gif.height,
                'frames':gif.n_frames,'duration_ms':actual_duration,'source_start_seconds':start,
                'fps':fps,'bytes':destination.stat().st_size}
    print(json.dumps(result,indent=2))
    return result
