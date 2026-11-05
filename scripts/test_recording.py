"""Exercise the real director, compositor, MP4/audio encoder and cancellation."""
import json
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import av
import numpy as np
from playwright.sync_api import sync_playwright
from app.config import WEB
from app.reconstruction import reconstruct
from app.recording import render_movie
from app.server import PreviewServer

root=Path('test-results/recording').resolve();root.mkdir(parents=True,exist_ok=True)
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
shutil.copytree(WEB/'demo',root/'fixture',dirs_exist_ok=True)
server=PreviewServer(root)
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1280,'height':720})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(server.url('fixture/index.html'));page.evaluate((WEB/'capture.js').read_text('utf-8'))
        page.evaluate('StudioCapture.start({lazy_load:true,timeout:15,max_elements:1000})')
        page.wait_for_function('StudioCapture.state.status==="complete"')
        capture=page.evaluate('StudioCapture.state.result')
        with ThreadPoolExecutor(max_workers=1) as pool:pool.submit(reconstruct,capture,root/'project',{'timeout':15}).result()
        page.goto(server.url('ui/player.html'))
        page.evaluate('async url=>{await Studio.load(url,{agents:8,sound:true,intro:true,auto_tour:true,names:true});Studio.pause(true)}',server.url('project')+'/')
        scene={'width':1280,'height':720,'zoom':3}
        page.evaluate('s=>Studio.startCapture(s)',scene)
        metrics=page.evaluate('''()=>{
          const s=Studio;let maxZoom=1,maxZoomStep=0,maxPanStep=0,maxScrollZoom=1,prev={...s.director.pose},samples=[];
          for(let i=0;i<18000;i++){
            const v=s.advanceCaptureFrame(i,60,1,false),p=v.pose;
            maxZoom=Math.max(maxZoom,p.zoom);maxZoomStep=Math.max(maxZoomStep,Math.abs(Math.log(p.zoom/prev.zoom)));
            maxPanStep=Math.max(maxPanStep,Math.hypot(p.x-prev.x,p.y-prev.y));
            if(s.camera.move)maxScrollZoom=Math.max(maxScrollZoom,p.zoom);
            if(i%30===0)samples.push({frame:i,...p});prev={...p};
            if(v.finished)return {frames:i+1,maxZoom,maxZoomStep,maxPanStep,maxScrollZoom,finalZoom:p.zoom,done:s.done,total:s.tasks.length,failed:s.failed,shots:s.director.shots,samples,scrollShots:s.camera.shots};
          }throw new Error('Camera never completed');
        }''')
        assert metrics['done']==metrics['total'] and metrics['failed']==0,metrics
        assert 2<metrics['maxZoom']<=3 and len(metrics['shots'])>=3,metrics
        assert metrics['maxZoomStep']<.02 and metrics['maxPanStep']<5,metrics
        assert metrics['maxScrollZoom']<1.04 and metrics['scrollShots']>=2,metrics
        assert metrics['finalZoom']<1.02,metrics
        # Resetting must reproduce the same plan, regardless of wall-clock time.
        page.evaluate('s=>Studio.startCapture(s)',scene)
        repeated=page.evaluate('''()=>{for(let i=0;i<18000;i++){const v=Studio.advanceCaptureFrame(i,60,1,false);if(v.finished)return {frames:i+1,shots:Studio.director.shots}}}''')
        assert repeated['frames']==metrics['frames'] and repeated['shots']==metrics['shots'],(repeated,metrics)
        assert not errors,errors
        browser.close()
    options=dict(width=1280,height=720,output_width=1280,output_height=720,fps=30,speed=1,zoom=3,sound=True)
    last=[-1]
    def progress(value,message):
        if value//10!=last[0]:last[0]=value//10;print(message,flush=True)
    report=render_movie(server.url('ui/player.html'),server.url('project')+'/',root/'swarm-cinematic.mp4',{'agents':8,'names':True,'intro':True,'volume':.4},options,progress=progress)
    video=av.open(report['path']);stream=video.streams.video[0]
    assert stream.average_rate==30 and stream.width==1280 and stream.height==720
    previous=-1;count=0
    inspect={min(report['frames']-1,at*30):at for at in (0,3,7,12,20,int(report['duration'])-1)}
    for index,frame in enumerate(video.decode(video=0)):
        assert frame.time>previous;previous=frame.time;count+=1
        if index in inspect:frame.to_image().save(root/f'frame-{inspect[index]:02}.png')
    assert count==report['frames'];video.close()
    audio=av.open(report['path']);sound=np.concatenate([f.to_ndarray() for f in audio.decode(audio=0)],axis=1)
    assert float(np.max(np.abs(sound)))>.005
    assert abs(sound.shape[1]/48000-report['duration'])<.08;audio.close()
    destination=root/'preserved.mp4';destination.write_bytes(b'existing user movie')
    cancelled=threading.Event()
    def stop(value,message):
        if value>=1:cancelled.set()
    try:
        render_movie(server.url('ui/player.html'),server.url('project')+'/',destination,{},dict(options,speed=5),cancelled,stop)
        raise AssertionError('Cancellation did not stop the movie')
    except InterruptedError:pass
    assert destination.read_bytes()==b'existing user movie'
    assert not list(root.glob('*.partial.mp4'))
    report['metrics']=metrics;report['cancellation_preserves_destination']=True
    (root/'report.json').write_text(json.dumps(report,indent=2),'utf-8')
    print('PASS cinematic movie',json.dumps({k:v for k,v in report.items() if k not in ('camera','shots','metrics')}),flush=True)
finally:server.close()
