"""Generate original, silent moving-color fixtures; no external media or rights required."""
from pathlib import Path
import av
import numpy as np
from PIL import Image


def create_media(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    for extension,codec in [('mp4','libx264'),('webm','libvpx-vp9')]:
        with av.open(str(root/('original.'+extension)),'w') as output:
            stream=output.add_stream(codec,rate=12);stream.width=160;stream.height=90;stream.pix_fmt='yuv420p'
            for index in range(36):
                pixels=np.zeros((90,160,3),dtype=np.uint8);pixels[:]=[(index*17)%240,50,(index*41)%240]
                pixels[20:60,(index*4)%130:(index*4)%130+25]=[255,240,30]
                frame=av.VideoFrame.from_ndarray(pixels,format='rgb24');frame.pts=index
                for packet in stream.encode(frame):output.mux(packet)
            for packet in stream.encode():output.mux(packet)
    Image.new('RGB',(160,90),'#264f3a').save(root/'poster.png')
    (root/'index.html').write_text('''<!doctype html><html><head><title>Original video fixture</title>
    <style>body{margin:0;background:#ddd;font:16px Arial}video{width:30vw;max-width:320px;aspect-ratio:16/9;object-fit:cover}section{display:flex;gap:8px}x-media{display:block}</style></head>
    <body><section><video src="original.mp4" autoplay muted loop playsinline poster="poster.png"></video>
    <video controls muted preload="metadata" poster="poster.png"><source src="original.webm" type="video/webm"></video>
    <video data-src="original.mp4" muted autoplay loop></video></section>
    <video src="missing.mp4" poster="poster.png"></video><video src="stream.m3u8"></video>
    <x-media></x-media><script>document.querySelector('x-media').attachShadow({mode:'open'}).innerHTML='<video style="width:160px;height:90px" muted loop autoplay src="original.webm"></video>';
    setTimeout(()=>{document.querySelector('[data-src]').src='original.mp4'},30);</script></body></html>''',encoding='utf-8')
    return root
