"""Read-only capture and deterministic camera regression for a public URL."""
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
root=Path('test-results/site-tour').resolve();root.mkdir(parents=True,exist_ok=True)
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
server=PreviewServer(root)
try:
  with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':585})
    page.goto(sys.argv[1] if len(sys.argv)>1 else 'https://huzera.com/',wait_until='domcontentloaded',timeout=30000)
    page.wait_for_timeout(1200)
    page.evaluate((WEB/'capture.js').read_text('utf-8'))
    page.evaluate('StudioCapture.start({lazy_load:true,timeout:25,max_elements:2500})')
    page.wait_for_function('StudioCapture.state.status==="complete"',timeout=35000)
    capture=page.evaluate('StudioCapture.state.result')
    with ThreadPoolExecutor(max_workers=1) as pool:metadata,blueprint=pool.submit(reconstruct,capture,root/'project',{'timeout':25}).result()
    print('Captured',len(blueprint['tasks']),'tasks and',metadata['assets'],'assets',flush=True)
    page.goto(server.url('ui/player.html'))
    page.evaluate('(url)=>Studio.load(url,{agents:8,speed:1,auto_tour:true,intro:false})',server.url('project')+'/')
    page.evaluate('Studio.pause(true)')
    for _ in range(160):
      if page.evaluate('Studio.finished'):break
      page.evaluate('for(let i=0;i<240&&!Studio.finished;i++)Studio.tick(1/60)')
    report=page.evaluate('({finished:Studio.finished,done:Studio.done,failed:Studio.failed,total:Studio.tasks.length,time:Studio.time,shots:Studio.camera.shots,scroll:Studio.camera.primary?.scrollTop,max:Studio.camera.maximum(Studio.camera.primary),pending:Studio.tasks.filter(t=>t.status!=="complete").map(t=>({id:t.id,status:t.status,operation:t.operation,tag:Studio.elements.get(t.element)?.tag,box:Studio.box(Studio.elements.get(t.element)),visible:Studio.isVisible(Studio.elements.get(t.element))}))})')
    page.evaluate('Studio.draw()');page.screenshot(path=str(root/'tour-finish.png'))
    (root/'results.json').write_text(json.dumps(report,indent=2),'utf-8')
    assert report['finished'] and report['shots']>1,report
    assert report['failed']==0,report
    print('PASS Public site Auto Tour',json.dumps(report),flush=True)
    browser.close()
finally:server.close()
