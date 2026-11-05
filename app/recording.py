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


def synthesize(events, start, samples, sample_rate=48000):
    """A bounded audio block. No microphone or desktop audio is captured."""
    import numpy as np
    output = np.zeros((2, samples), dtype=np.float32)
    times = (np.arange(samples, dtype=np.float64) + start) / sample_rate
    notes = [164.81, 185, 207.65, 246.94, 277.18]
    for event in events:
        kind, at = event['kind'], event['time']
        duration = .9 if kind == 'complete' else .09 if kind in ('type', 'click') else .2
        if at >= times[-1] + 1/sample_rate or at + duration < times[0]:
            continue
        t = times-at
        mask = (t >= 0) & (t < duration)
        local = t[mask]
        if kind in ('type', 'click'):
            hz = 190 if kind == 'type' else 420
            # Analytic noise avoids random state depending on block boundaries.
            noise = np.sin((np.floor(local*sample_rate)+at*7919)*12.9898)*43758.5453
            noise = 2*(noise-np.floor(noise))-1
            wave = (np.sin(2*np.pi*hz*local)*.6 + noise*.4)*np.exp(-local*95)
        else:
            tones = [164.81, 207.65, 246.94, 329.63] if kind == 'complete' else [notes[min(4,int(event['x']*5))]*2]
            wave = sum(np.sin(2*np.pi*hz*local) for hz in tones)/len(tones)*np.exp(-local*(5 if kind == 'complete' else 22))
        wave *= min(1,max(0,event.get('volume',.25)))*.13
        pan = min(1,max(0,event.get('x',.5)))
        output[0,mask] += wave*(1-pan)**.5
        output[1,mask] += wave*pan**.5
    return np.ascontiguousarray(np.clip(output,-.95,.95))


def render_movie(player_url, project_url, destination, settings, options, cancel=None, progress=None):
    import av
    from PIL import Image
    from playwright.sync_api import sync_playwright
    cancel = cancel or threading.Event()
    progress = progress or (lambda value, message: None)
    destination = Path(destination)
    fps = int(options.get('fps',60))
    width, height = int(options.get('output_width',1920)), int(options.get('output_height',1080))
    if fps not in (30,60) or width < 320 or height < 180 or width%2 or height%2:
        raise ValueError('Choose an even video size and 30 or 60 frames per second.')
    speed = min(5,max(.5,float(options.get('speed',1))))
    scene = dict(width=int(options.get('width',1280)),height=int(options.get('height',800)),zoom=min(3,max(1,float(options.get('zoom',3)))))
    tmp = destination.with_name('.'+destination.stem+'-'+uuid.uuid4().hex+'.partial.mp4')
    def check():
        if cancel.is_set():raise InterruptedError('Recording cancelled. No video was replaced.')
    try:
        with sync_playwright() as pw:
            check()
            browser = None
            for channel in ('msedge','chrome'):
                try:
                    browser=pw.chromium.launch(channel=channel,headless=True,args=['--disable-background-timer-throttling','--disable-renderer-backgrounding'])
                    break
                except Exception:
                    check()
            if browser is None:raise RuntimeError('Recording needs Microsoft Edge or Google Chrome installed. Install either browser and try again.')
            context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,reduced_motion='reduce')
            # Record only the trusted local player and its saved, local assets.
            from urllib.parse import urlsplit
            origin=urlsplit(player_url)
            context.route('**/*',lambda route: route.continue_() if urlsplit(route.request.url).netloc==origin.netloc or route.request.url.startswith(('data:','blob:')) else route.abort())
            page=context.new_page()
            page.set_default_timeout(30000)
            page.goto(player_url)
            movie_settings=dict(settings,sound=bool(options.get('sound',False)),auto_tour=True,speed=1)
            page.evaluate('async a=>{await Studio.load(a.url,a.settings);Studio.pause(true)}',{'url':project_url,'settings':movie_settings})
            page.evaluate('a=>Studio.startCapture(a)',scene)
            progress(0,'Planning camera moves…')
            total=0
            max_frames=int(options.get('max_seconds',600)*fps)
            state={}
            while total<max_frames:
                check()
                plan=page.evaluate('a=>{let state,count=0;for(;count<a.count;count++){state=Studio.advanceCaptureFrame(Studio.captureIndex,a.fps,a.speed,false);if(state.finished){count++;break}}return {count,state}}',{'count':fps*4,'fps':fps,'speed':speed})
                total+=plan['count'];state=plan['state']
                if state['finished']:break
            if not state.get('finished'):raise RuntimeError('The recording exceeded ten minutes or the task graph stalled. Try a faster playback speed.')
            events=page.evaluate('Studio.sound.ledger')
            event_times=[event['time'] for event in events]
            planned_shots=page.evaluate('Studio.director.shots')
            page.evaluate('a=>Studio.startCapture(a)',scene)
            check()
            progress(0,f'Rendering {total/fps:.1f}s at {fps} fps…')
            session=context.new_cdp_session(page)
            media_report={'warnings':[]}
            camera_samples=[]
            with av.open(str(tmp),'w',format='mp4',options={'movflags':'+faststart'}) as container:
                video=container.add_stream('libx264',rate=fps)
                video.width,video.height,video.pix_fmt=width,height,'yuv420p'
                video.options={'preset':'fast','crf':'18'}
                audio=None
                if options.get('sound'):
                    audio=container.add_stream('aac',rate=48000);audio.layout='stereo';audio.bit_rate=192000
                audio_samples=48000//fps
                for index in range(total):
                    check()
                    state=page.evaluate('a=>Studio.advanceCaptureFrame(a.index,a.fps,a.speed)',{'index':index,'fps':fps,'speed':speed})
                    media_report=page.evaluate('seconds=>Studio.media.sync(seconds)',index/fps)
                    # CDP waits for the compositor surface and captures only the player.
                    encoded=session.send('Page.captureScreenshot',{'format':'jpeg','quality':96,'fromSurface':True,'captureBeyondViewport':False})['data']
                    with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
                        frame=av.VideoFrame.from_image(image.convert('RGB'))
                    frame.pts=index;frame.time_base=Fraction(1,fps)
                    for packet in video.encode(frame):container.mux(packet)
                    if audio:
                        nearby=events[bisect_left(event_times,index/fps-.9):bisect_right(event_times,(index+1)/fps)]
                        block=synthesize(nearby,index*audio_samples,audio_samples)
                        aframe=av.AudioFrame.from_ndarray(block,format='fltp',layout='stereo')
                        aframe.sample_rate=48000;aframe.pts=index*audio_samples;aframe.time_base=Fraction(1,48000)
                        for packet in audio.encode(aframe):container.mux(packet)
                    if index%max(1,fps//4)==0 or index==total-1:
                        camera_samples.append({'frame':index,**state['pose'],'state':state['state']})
                        progress(round((index+1)*100/total),f'Rendering {(index+1)/fps:.1f} / {total/fps:.1f}s · {fps} fps')
                for packet in video.encode():container.mux(packet)
                if audio:
                    for packet in audio.encode():container.mux(packet)
            check()
            if not state.get('finished') or state['completed']!=state['total']:
                raise RuntimeError('The movie did not complete every task. The previous video was preserved.')
            os.replace(tmp,destination)
            browser.close()
            return {'path':str(destination),'frames':total,'fps':fps,'width':width,'height':height,'duration':total/fps,'shots':planned_shots,'camera':camera_samples,'media':media_report,'audio_events':len(events),'completed':state['completed'],'total':state['total']}
    finally:
        tmp.unlink(missing_ok=True)


class RecordingWorker(QThread):
    progress=Signal(int,str)
    ready=Signal(str,dict)
    error=Signal(str)

    def __init__(self, player_url, project_url, destination, settings, options, parent=None):
        super().__init__(parent)
        self.args=(player_url,project_url,destination,settings,options)
        self.cancel_event=threading.Event()

    def run(self):
        try:
            result=render_movie(*self.args,cancel=self.cancel_event,progress=self.progress.emit)
            self.ready.emit(result['path'],result)
        except InterruptedError as exc:self.error.emit(str(exc))
        except Exception as exc:
            import logging
            logging.exception('Movie export failed')
            self.error.emit(f'Recording failed: {exc}')
