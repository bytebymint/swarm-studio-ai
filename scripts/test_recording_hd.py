"""Encode the full demo at the shipping 1080p/60 fps settings after test_recording."""
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import av
from app.config import WEB
from app.recording import render_movie
from app.server import PreviewServer

root=Path('test-results/recording').resolve()
metadata=json.loads((root/'project/metadata/project.json').read_text('utf-8'))
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
server=PreviewServer(root)
last=[-1]
def progress(value,message):
    if value//10!=last[0]:last[0]=value//10;print(message,flush=True)
try:
    options=dict(width=metadata['viewport']['width'],height=metadata['viewport']['height'],output_width=1920,output_height=1080,fps=60,speed=2,zoom=3,sound=True)
    report=render_movie(server.url('ui/player.html'),server.url('project')+'/',root/'swarm-cinematic-hd.mp4',{'agents':8,'intro':True,'names':True,'volume':.4},options,progress=progress)
    with av.open(report['path']) as movie:
        stream=movie.streams.video[0]
        assert stream.width==1920 and stream.height==1080 and stream.average_rate==60
        count=0;previous=-1
        for frame in movie.decode(video=0):
            assert frame.time>previous;previous=frame.time;count+=1
            if count in (601,961,1441):frame.to_image().save(root/f'hd-frame-{count}.png')
        assert count==report['frames']
    assert report['camera'][-1]['zoom']<1.02
    assert report['completed']==report['total']
    (root/'hd-report.json').write_text(json.dumps(report,indent=2),'utf-8')
    print('PASS 1080p/60 movie',json.dumps({k:v for k,v in report.items() if k not in ('shots','camera')}),flush=True)
finally:server.close()
