"""Real Chromium capture, offline ZIP playback, choreography and virtual video clock."""
import json
import shutil
import sys
import zipfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from app.config import WEB
from app.reconstruction import reconstruct
from app.recording import render_movie
from app.server import PreviewServer
from app.workers import ExportWorker
from scripts.media_fixture import create_media

base=Path('test-results/video').resolve();base.mkdir(parents=True,exist_ok=True)
root=base/'runs'/uuid.uuid4().hex;root.mkdir(parents=True)
(base/'latest.json').write_text(json.dumps(str(root)),'utf-8')
source=PreviewServer(create_media(root/'source'))
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True);output=PreviewServer(root)
report={}
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1000,'height':700})
        page.goto(source.url('index.html'));page.wait_for_timeout(200)
        page.evaluate((WEB/'capture.js').read_text('utf-8'))
        page.evaluate('StudioCapture.start({lazy_load:true,timeout:15})')
        page.wait_for_function('StudioCapture.state.status==="complete"')
        capture=page.evaluate('StudioCapture.state.result')
        media=[e for e in capture['elements'] if e['kind']=='media']
        assert len(media)==6 and all('media' in e for e in media)
        assert all(e['rect']['w']>0 and e['rect']['h']>0 for e in media)
        assert any(e['media']['autoplay'] and e['media']['muted'] and e['media']['loop'] for e in media)
        with ThreadPoolExecutor() as pool:meta,blueprint=pool.submit(reconstruct,capture,root/'project',{'timeout':30}).result()
        saved=[e for e in blueprint['elements'] if e['kind']=='media']
        assert sum(e['media']['status']=='downloaded' for e in saved)==4
        assert {e['media']['status'] for e in saved}=={'downloaded','poster-only','unsupported'}
        assert len(list((root/'project/assets/media').glob('*')))==2
        assert sum(t['operation']=='place_media' for t in blueprint['tasks'])==6
        html=(root/'project/index.html').read_text('utf-8')
        assert '<script' not in html and source.origin not in html
        page.evaluate('''()=>{for(const src of ['blob:'+location.origin+'/temporary','original.mp4?access_token=SYNTHETIC','stream.mpd']){const v=document.createElement('video');v.style.cssText='width:160px;height:90px';v.src=src;document.body.append(v);}const hidden=document.createElement('video');hidden.style.display='none';hidden.src='original.mp4';document.body.append(hidden);}''')
        page.evaluate('StudioCapture.start({timeout:15})')
        page.wait_for_function('StudioCapture.state.status==="complete"')
        extra=page.evaluate('StudioCapture.state.result')
        assert len(extra['media'])==10 and len([e for e in extra['elements'] if e['kind']=='media'])==9
        assert 'SYNTHETIC' not in json.dumps(extra) and 'blob:' not in extra['html']
        source.close();source=None
        archive=root/'website.zip';worker=ExportWorker(root/'project',archive,{});worker.run()
        assert archive.is_file()
        with zipfile.ZipFile(archive) as package:
            assert len([n for n in package.namelist() if n.startswith('assets/media/')])==2
            package.extractall(root/'unpacked')
        page.goto(output.url('unpacked/index.html'))
        page.wait_for_function('[...document.querySelectorAll("video")].every(v=>v.readyState>=2)')
        assert page.locator('video').count()==4
        width=page.locator('video').first.evaluate('v=>v.getBoundingClientRect().width')
        page.set_viewport_size({'width':500,'height':700})
        assert page.locator('video').first.evaluate('v=>v.getBoundingClientRect().width')<width
        page.set_viewport_size({'width':1000,'height':700})
        page.evaluate('async()=>{const v=document.querySelector("video");v.muted=true;await v.play()}')
        before=page.locator('video').first.evaluate('v=>v.currentTime');page.wait_for_timeout(200)
        assert page.locator('video').first.evaluate('v=>v.currentTime')!=before
        page.goto(output.url('ui/player.html'))
        page.evaluate('async url=>{await Studio.load(url,{agents:8,intro:false,auto_tour:true});Studio.pause(true)}',output.url('project')+'/')
        page.evaluate('for(let i=0;i<10000&&!Studio.finished;i++)Studio.tick(1/60);Studio.draw()')
        assert page.evaluate('Studio.finished&&Studio.failed===0')
        assert page.evaluate('Studio.history.filter(h=>Studio.byId.get(h.task).operation==="place_media").length')==6
        page.evaluate('Studio.startCapture({width:1000,height:700,zoom:3});for(const i of Studio.media.items){i.base=0;i.started=true}')
        def sample(time):
            state=page.evaluate('t=>Studio.media.sync(t)',time)
            assert not state['warnings'],state
            return page.evaluate('''()=>{const v=Studio.media.items[0].v,c=document.createElement('canvas');c.width=160;c.height=90;c.getContext('2d').drawImage(v,0,0);return {time:v.currentTime,pixel:[...c.getContext('2d').getImageData(80,10,1,1).data]}}''')
        a=sample(.25);b=sample(.75);loop=sample(3.25);again=sample(.75)
        assert a['pixel']!=b['pixel'] and a==loop and b==again,(a,b,loop,again)
        page.screenshot(path=str(root/'swarm-video.png'))
        report.update(captured_videos=6,downloaded_videos=4,unique_media_files=2,offline_zip_playback=True,media_tasks=6,deterministic_pixels=True)
        browser.close()
    movie=render_movie(output.url('ui/player.html'),output.url('project')+'/',root/'cinematic-video.mp4',{'agents':8,'intro':False},dict(width=1000,height=700,output_width=1280,output_height=720,fps=30,speed=5,zoom=3,sound=False),progress=lambda p,m:print(m,flush=True) if p%20==0 else None)
    assert not movie['media']['warnings'],movie['media']
    import av
    pixels=[]
    with av.open(movie['path']) as film:
        count=0
        for frame in film.decode(video=0):
            count+=1
            if count>movie['frames']-30:pixels.append(tuple(c//16 for c in frame.to_image().getpixel((210,30))))
        assert count==movie['frames']
    assert len(set(pixels))>=3,'Source video froze in the encoded movie'
    hd=render_movie(output.url('ui/player.html'),output.url('project')+'/',root/'cinematic-video-hd.mp4',{'agents':8,'intro':False},dict(width=1000,height=700,output_width=1920,output_height=1080,fps=60,speed=5,zoom=3,sound=False))
    with av.open(hd['path']) as film:
        assert film.streams.video[0].average_rate==60 and film.streams.video[0].width==1920
        assert sum(1 for _ in film.decode(video=0))==hd['frames']
    assert not hd['media']['warnings']
    report['hd_movie_frames']=hd['frames'];report['moving_encoded_pixels']=len(set(pixels))
    report['movie']={k:v for k,v in movie.items() if k not in ('camera','shots')}
    (root/'report.json').write_text(json.dumps(report,indent=2),'utf-8')
    print('PASS VIDEO',json.dumps(report),flush=True)
finally:
    if source:source.close()
    output.close()
