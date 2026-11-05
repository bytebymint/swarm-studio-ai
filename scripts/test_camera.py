"""Regression: Auto Tour must visibly scroll, not just complete offscreen tasks."""
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from app.config import WEB
from app.reconstruction import reconstruct
from app.server import PreviewServer

root=Path('test-results/camera').resolve();root.mkdir(parents=True,exist_ok=True)
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
sections=''.join(f'<section style="height:720px;padding:60px;background:{color}"><h2>Section {i+1}</h2><p>Actual section text for the camera to follow.</p><article>Component {i+1}</article></section>' for i,color in enumerate(['#e8e4d9','#cdddcf','#d6d9e9','#e9d9cc','#d5e4e8','#e4decf']))
document=f'<html><head><title>Document tour</title><style>body{{margin:0;font:20px Arial}}html{{scroll-behavior:smooth}}</style></head><body><main>{sections}</main></body></html>'
nested=f'<html><head><title>Nested tour</title><style>html,body{{height:100%;margin:0;overflow:hidden;font:20px Arial}}header{{height:50px;background:#24312a;color:white}}main{{height:calc(100% - 50px);overflow:auto;scroll-behavior:smooth}}</style></head><body><header>App shell</header><main>{sections}</main></body></html>'
(root/'document.html').write_text(document,'utf-8');(root/'nested.html').write_text(nested,'utf-8')
server=PreviewServer(root);reports=[]
try:
  with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1100,'height':650})
    for name in ['document','nested']:
      page.goto(server.url(name+'.html'))
      page.evaluate((WEB/'capture.js').read_text('utf-8'))
      page.evaluate('StudioCapture.start({lazy_load:false,timeout:10,max_elements:500})')
      page.wait_for_function('StudioCapture.state.status==="complete"')
      capture=page.evaluate('StudioCapture.state.result')
      with ThreadPoolExecutor(max_workers=1) as pool:pool.submit(reconstruct,capture,root/name,{'timeout':10}).result()
      page.goto(server.url('ui/player.html'))
      page.evaluate('window.cameraChecks={offscreen:[],shots:[]};window.studioBridge={publish:raw=>{const v=JSON.parse(raw);if(v.type==="assigned"&&v.operation!=="verify"&&!Studio.isVisible(Studio.elements.get(Studio.byId.get(v.task).element)))cameraChecks.offscreen.push(v.task);if(v.type==="camera-shot")cameraChecks.shots.push(v);}}')
      page.evaluate('(url)=>Studio.load(url,{agents:12,speed:1,intro:false,auto_tour:true})',server.url(name)+'/')
      page.evaluate('Studio.pause(true);window.cameraSamples=[];')
      # Enter the first camera move deterministically, then verify real RAF motion.
      for _ in range(80):
        if page.evaluate('Boolean(Studio.camera.move)'):break
        page.evaluate('for(let i=0;i<30;i++)Studio.tick(1/60)')
      assert page.evaluate('Boolean(Studio.camera.move)'),name+' never started a camera shot'
      before=page.evaluate('Studio.camera.primary.scrollTop')
      page.evaluate('Studio.pause(false)');page.wait_for_timeout(350)
      page.evaluate('Studio.pause(true)')
      after=page.evaluate('Studio.camera.primary.scrollTop')
      assert after>before,name+' did not move in real animation frames'
      page.wait_for_timeout(200)
      assert page.evaluate('Studio.camera.primary.scrollTop')==after,'Pause must freeze camera'
      page.screenshot(path=str(root/(name+'-tour.png')))
      page.evaluate('Studio.setOptions({auto_tour:false})')
      page.evaluate('for(let i=0;i<120;i++)Studio.tick(1/60)')
      assert page.evaluate('Studio.camera.primary.scrollTop')==after,'Manual mode must not scroll'
      page.evaluate('Studio.setOptions({auto_tour:true})')
      for _ in range(200):
        if page.evaluate('Studio.finished'):break
        page.evaluate('for(let i=0;i<120&&!Studio.finished;i++){Studio.tick(1/60);cameraSamples.push(Studio.camera.primary.scrollTop)}')
      report=page.evaluate('({name:document.title,finished:Studio.finished,failed:Studio.failed,completed:Studio.done,total:Studio.tasks.length,shots:Studio.camera.shots,scroll:Studio.camera.primary.scrollTop,maximum:Studio.camera.maximum(Studio.camera.primary),largestStep:cameraSamples.reduce((m,x,i)=>i?Math.max(m,Math.abs(x-cameraSamples[i-1])):m,0),offscreenAssignments:cameraChecks.offscreen})')
      report['fixture']=name
      assert report['finished'] and report['failed']==0,report
      assert report['completed']==report['total'],report
      assert report['shots']>=3 and report['scroll']>=report['maximum']-2,report
      assert report['largestStep']<65,report
      assert report['offscreenAssignments']==[],report
      reports.append(report);print('PASS Cinematic Auto Tour:',name,json.dumps(report),flush=True)
    browser.close()
  (root/'results.json').write_text(json.dumps(reports,indent=2),'utf-8')
finally:server.close()
