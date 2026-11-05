"""Independent Chrome tests of real capture, export, scheduling and reference media."""
import json
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright

from app.config import WEB
from app.reconstruction import reconstruct_collection
from app.server import PreviewServer
from app.validation import compare_images

root=Path('test-results/browser').resolve();root.mkdir(parents=True,exist_ok=True)
source=root/'source';source.mkdir(exist_ok=True)
asset=root/'remote-css';asset.mkdir(exist_ok=True)
(asset/'site.css').write_text('body{margin:0;color:#173c33;font:16px/1.5 Arial;background:#f8f5ed} main{padding:40px;max-width:900px} h1{font-size:44px} .cards{display:flex;gap:20px}.card{padding:24px;background:#d9e5cf;border-radius:8px}.hover:hover{color:red}img{width:120px;height:100px}@media(max-width:500px){.cards{display:block}h1{font-size:30px}}')
with (asset/'site.css').open('a') as css:
  css.write('main{background-image:url(image.svg);background-size:40px 40px;background-repeat:no-repeat;background-position:right top}')
shutil.copyfile(WEB/'demo/field.svg',asset/'image.svg')
assets_server=PreviewServer(asset)
(source/'index.html').write_text(f'<!doctype html><html lang="en"><head><title>Local capture fixture</title><link rel="stylesheet" href="{assets_server.origin}/site.css"></head><body><main><h1>Actual captured words</h1><p class="hover">Selectable text in the real DOM.</p><div class="cards"><article class="card">First repeated card</article><article class="card">Second repeated card</article></div><img src="{assets_server.origin}/image.svg" width="120" height="100" alt="Test illustration"><details><summary>Native interaction</summary><p>Expandable content</p></details><a href="second.html">Second page</a><input value="PRIVATE-VALUE"><textarea>PRIVATE-TEXT</textarea><script>window.sourceSecret="NEVER EXPORT"</script></main></body></html>')
(source/'second.html').write_text('<!doctype html><html lang="en"><head><title>Second</title></head><body><main><h1>Second page</h1><a href="index.html">Return home</a></main></body></html>')
source_server=PreviewServer(source)
output=root/'output';output.mkdir(exist_ok=True)
shutil.copytree(WEB,output/'ui',dirs_exist_ok=True)
output_server=PreviewServer(output)
results=[]
def record(name):results.append(name);print('PASS',name,flush=True)

try:
  with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1000,'height':800},device_scale_factor=1)
    captures=[]
    for path in ['index.html','second.html']:
      page.goto(source_server.url(path))
      page.evaluate((WEB/'capture.js').read_text('utf-8'))
      page.evaluate('window.StudioCapture.start({lazy_load:true,max_elements:500,timeout:10})')
      page.wait_for_function('window.StudioCapture.state.status==="complete"')
      captures.append(page.evaluate('window.StudioCapture.state.result'))
    assert captures[0]['computedCSS']
    assert any('inaccessible' in warning for warning in captures[0]['warnings'])
    with ThreadPoolExecutor(max_workers=1) as pool:
      metadata,blueprint=pool.submit(reconstruct_collection,captures,output/'project',{'timeout':10}).result()
    html=(output/'project/index.html').read_text('utf-8')
    assert 'PRIVATE-VALUE' not in html and 'PRIVATE-TEXT' not in html and 'NEVER EXPORT' not in html
    assert 'pages/page-002/index.html' in html
    assert metadata['pages'][captures[1]['url']]=='pages/page-002/index.html'
    # Check every URL relative to the actual stylesheet location, including
    # imports and fonts. HTML image success alone cannot prove CSS paths work.
    from app.assets import URL_PATTERN
    for stylesheet in (output/'project').rglob('*.css'):
      for match in URL_PATTERN.finditer(stylesheet.read_text('utf-8')):
        ref=match.group(2)
        if ref and not ref.startswith(('data:','#')):assert (stylesheet.parent/ref).is_file(),str(stylesheet)+': '+ref
    record('Real browser DOM capture, inaccessible CSS fallback, valid stylesheet-relative asset paths, input redaction and multi-page link rewriting')
    source_server.close();assets_server.close()
    requests=[];page.on('request',lambda req:requests.append(req.url))
    page.goto(output_server.url('project/index.html'))
    assert page.locator('h1').inner_text()=='Actual captured words'
    assert page.locator('input').input_value()==''
    assert page.locator('textarea').input_value()==''
    assert page.locator('img').evaluate('(img)=>img.complete&&img.naturalWidth>0')
    assert '/project/assets/images/' in page.locator('main').evaluate('(node)=>getComputedStyle(node).backgroundImage')
    page.locator('summary').click();assert page.locator('details').get_attribute('open') is not None
    page.get_by_role('link',name='Second page').click();assert page.locator('h1').inner_text()=='Second page'
    page.get_by_role('link',name='Return home').click();assert page.locator('h1').inner_text()=='Actual captured words'
    assert all(url.startswith(output_server.origin) or url.startswith('data:') for url in requests)
    page.screenshot(path=str(root/'independent-export.png'))
    record('Export works after both source servers stop: selectable text, image, native accordion and local navigation')
    page.goto(output_server.url('ui/player.html'))
    page.evaluate('window.studioBridge={publish:raw=>{(window.recordedEvents ||= []).push(JSON.parse(raw));}}')
    project=output_server.url('project')+'/'
    page.evaluate('(url)=>window.Studio.load(url,{agents:16,speed:5,auto_tour:true,intro:false})',project)
    page.wait_for_function('window.Studio.time>1')
    page.evaluate('window.Studio.pause(true)')
    time=page.evaluate('window.Studio.time');page.wait_for_timeout(150)
    assert page.evaluate('window.Studio.time')==time
    page.evaluate('window.Studio.step()');assert page.evaluate('window.Studio.time')>time
    page.evaluate('window.Studio.pause(false)');page.wait_for_function('window.Studio.finished',timeout=60000)
    assert page.evaluate('window.Studio.failed')==0
    events=page.evaluate('window.recordedEvents')
    completed=set();frames=set()
    tasks={task['id']:task for task in blueprint['tasks']}
    for event in events:
      if event['type']=='completed':completed.add(event['task'])
      if event['type']=='frame-ready':frames.add(event['task'])
      if event['type']=='assigned':
        task=tasks[event['task']]
        for dependency in task['dependencies']:
          assert dependency in completed or task.get('dependencyPhases',{}).get(dependency)=='frame' and dependency in frames
    assert len(completed)==len(blueprint['tasks'])
    record('JS scheduler observes completed dependencies and published parent frames; pause, step and completion work')
    page.evaluate('window.Studio.replay()');page.wait_for_function('!window.Studio.finished')
    page.evaluate('window.Studio.stop()');assert page.locator('#site').content_frame.locator('[data-sw-state]').count()==0
    record('Replay and cancellation clean all build masks')
    empty=output/'empty';empty.mkdir(exist_ok=True);(empty/'metadata').mkdir(exist_ok=True)
    (empty/'index.html').write_text('<html><body>Empty fixture</body></html>')
    (empty/'metadata/blueprint.json').write_text(json.dumps({'elements':[],'tasks':[],'viewport':{'width':1000,'height':800}}))
    page.evaluate('(url)=>window.Studio.load(url,{intro:false})',output_server.url('empty')+'/')
    assert page.evaluate('window.Studio.finished')
    broken={'elements':[{'id':'missing','rect':{'x':0,'y':0,'w':10,'h':10}}],'tasks':[{'id':'missing','element':'missing','dependencies':[],'operation':'draw','duration':.1}]}
    (empty/'metadata/blueprint.json').write_text(json.dumps(broken))
    page.evaluate('(url)=>window.Studio.load(url,{intro:false,speed:5,auto_tour:true})',output_server.url('empty')+'/')
    page.wait_for_function('window.Studio.finished')
    assert page.evaluate('window.Studio.failed')==1 and page.evaluate('window.Studio.done')==0
    record('Zero-task completion and missing-node failure reporting are explicit')
    # Read the supplied recordings locally; no reference asset enters our distribution.
    for filename in ['demo.mp4','demo-with-sound.mp4']:
      page.goto((Path('swarm-cursors-main/media')/filename).resolve().as_uri())
      page.locator('video').wait_for()
      page.locator('video').evaluate('(video)=>{video.muted=true;video.currentTime=8;video.pause();}')
      page.wait_for_timeout(300)
      page.screenshot(path=str(root/filename.replace('.mp4','-reference.png')))
      assert page.locator('video').evaluate('(video)=>video.duration')>20
    record('Inspected both supplied reference videos locally')
    browser.close()
  (root/'results.json').write_text(json.dumps({'passed':results},indent=2))
finally:
  output_server.close()
  # shutdown is idempotent at the server level, but avoid duplicate closes here.
  if source_server.thread.is_alive():source_server.close()
  if assets_server.thread.is_alive():assets_server.close()
