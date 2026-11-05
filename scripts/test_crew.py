"""Motion/crew contracts: real work, bounded population and layout-stable typing."""
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from PIL import Image
from app.config import WEB
from app.reconstruction import reconstruct
from app.server import PreviewServer

root=Path('test-results/crew').resolve();root.mkdir(parents=True,exist_ok=True)
shutil.copytree(WEB,root/'ui',dirs_exist_ok=True)
shutil.copytree(WEB/'demo',root/'fixture',dirs_exist_ok=True)
source=(root/'fixture/index.html').read_text('utf-8')
source=source.replace('<h1>','<h1 style="background:linear-gradient(90deg,#194837,#7b503c);background-clip:text;-webkit-text-fill-color:transparent">',1)
source=source.replace('<footer id="about">','<hr style="margin:10px 6%;border:0;border-top:1px solid #71857b"><footer id="about">')
(root/'fixture/index.html').write_text(source,'utf-8')
server=PreviewServer(root)
try:
  with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':650},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(server.url('fixture/index.html'));page.evaluate((WEB/'capture.js').read_text('utf-8'))
    page.evaluate('StudioCapture.start({lazy_load:true,timeout:15,max_elements:1000})')
    page.wait_for_function('StudioCapture.state.status==="complete"')
    capture=page.evaluate('StudioCapture.state.result')
    with ThreadPoolExecutor(max_workers=1) as pool:metadata,blueprint=pool.submit(reconstruct,capture,root/'project',{'timeout':15}).result()
    page.goto(server.url('ui/player.html'))
    page.evaluate('window.recorded=[];window.studioBridge={publish:raw=>recorded.push(JSON.parse(raw))}')
    page.evaluate('(url)=>Studio.load(url,{agents:8,speed:1,intro:true,auto_tour:true,names:true})',server.url('project')+'/')
    page.evaluate('''Studio.pause(true);window.metrics={frames:0,visible:0,busy:0,maxVisible:0,maxIdle:0,maxActive:0,maxStep:0,cursorError:0,textWidthError:0,textMutations:0,typedFrames:0,highlights:!!Studio.choreography.highlight};window.previous=new Map();window.savedFrames=[];
      window.sampleCrew=()=>{const s=Studio,m=metrics;const visible=s.agents.filter(a=>a.opacity>.18&&a.x>=0&&a.x<=innerWidth&&a.y>=0&&a.y<=innerHeight);const active=s.agents.filter(a=>a.task);if(s.time>s.introDuration+.5&&!s.finished){m.frames++;m.visible+=visible.length;m.busy+=visible.filter(a=>a.task).length;m.maxVisible=Math.max(m.maxVisible,visible.length);m.maxIdle=Math.max(m.maxIdle,visible.filter(a=>!a.task).length);m.maxActive=Math.max(m.maxActive,active.length);}for(const a of visible){const prev=previous.get(a.id);if(prev&&prev.visible){const step=Math.hypot(a.x-prev.x,a.y-prev.y);if(step>m.maxStep){m.maxStep=step;m.maxStepTrace={id:a.id,operation:a.task?.operation,phase:a.phase,progress:a.task?.progress,time:s.time,from:prev,to:{x:a.x,y:a.y}};}}previous.set(a.id,{x:a.x,y:a.y,visible:true,phase:a.phase,task:a.task?.id});if(a.task&&a.pose)m.cursorError=Math.max(m.cursorError,Math.hypot(a.x-a.pose.x,a.y-a.pose.y));}for(const a of s.agents)if(!visible.includes(a))previous.set(a.id,{visible:false});for(const e of s.elements.values()){if(e.typing){m.typedFrames++;for(const [node,text]of e.textNodes)if(node.textContent!==text)m.textMutations++;const r=e.node.getBoundingClientRect();if(e.referenceWidth!==undefined)m.textWidthError=Math.max(m.textWidthError,Math.abs(r.width-e.referenceWidth));}}};
      for(const e of Studio.elements.values())if(e.node)e.referenceWidth=e.node.getBoundingClientRect().width;''')
    captured=[]
    for batch in range(160):
      if page.evaluate('Studio.finished'):break
      page.evaluate('for(let i=0;i<90&&!Studio.finished;i++){Studio.tick(1/60);sampleCrew()}Studio.draw()')
      candidate=page.evaluate('({time:Studio.time,done:Studio.done,busy:Studio.agents.filter(a=>a.task).length,typing:Studio.agents.some(a=>a.phase==="Type"&&a.task?.progress>.4),image:Studio.agents.some(a=>a.task?.operation==="place"&&a.task.progress>.4),duplicate:Studio.agents.some(a=>a.task?.operation==="duplicate"&&a.task.progress>.2)})')
      tag='team' if candidate['busy']>=3 and 'team' not in captured else 'typing' if candidate['typing'] and 'typing' not in captured else 'image' if candidate['image'] and 'image' not in captured else 'duplicate' if candidate['duplicate'] and 'duplicate' not in captured else None
      if tag:page.screenshot(path=str(root/(tag+'.png')));captured.append(tag)
    result=page.evaluate('({...metrics,finished:Studio.finished,done:Studio.done,total:Studio.tasks.length,failed:Studio.failed,crew:Studio.agents.length,capacity:Studio.crew.capacity,handoffs:recorded.filter(e=>e.type==="handoff").length,framesPublished:recorded.filter(e=>e.type==="frame-ready").length,workingFraction:metrics.busy/Math.max(1,metrics.visible),operations:[...new Set(recorded.filter(e=>e.type==="assigned").map(e=>e.operation))]})')
    assert result['finished'] and result['failed']==0,result
    assert result['crew']==8 and result['maxActive']>=3,result
    assert result['maxVisible']<=result['capacity']+2 and result['maxIdle']<=2,result
    assert result['workingFraction']>.78,result
    assert result['maxStep']<75 and result['cursorError']<.01,result
    assert result['highlights'] and result['typedFrames']>30 and result['textMutations']==0 and result['textWidthError']<.1,result
    assert result['handoffs']>2 and result['framesPublished']>2,result
    assert {'draw','type','place','duplicate','stroke','verify'}<=set(result['operations']),result
    # The actual milestone events must precede every dependent assignment.
    events=page.evaluate('recorded');complete=set();frames=set();tasks={t['id']:t for t in blueprint['tasks']}
    for event in events:
      if event['type']=='completed':complete.add(event['task'])
      if event['type']=='frame-ready':frames.add(event['task'])
      if event['type']=='assigned':
        task=tasks[event['task']]
        for dependency in task['dependencies']:assert dependency in complete or task.get('dependencyPhases',{}).get(dependency)=='frame' and dependency in frames
    # Gradient text must also type progressively, without moving its glyphs.
    page.evaluate('Studio.showClone();Studio.doc.scrollingElement.scrollTop=0;Studio.boundsCache.clear();window.heading=[...Studio.elements.values()].find(e=>e.tag==="h1");Studio.choreography.prepareText(heading);Studio.choreography.type(heading,0,Studio.agents[1]);')
    page.locator('#site').content_frame.locator('h1').screenshot(path=str(root/'gradient-empty.png'))
    page.evaluate('Studio.choreography.type(heading,.6,Studio.agents[1]);')
    page.locator('#site').content_frame.locator('h1').screenshot(path=str(root/'gradient-partial.png'))
    empty=Image.open(root/'gradient-empty.png').convert('RGB');partial=Image.open(root/'gradient-partial.png').convert('RGB')
    if len(partial.getcolors(partial.width*partial.height) or [])<=20:
      print('GRADIENT DEBUG',page.evaluate('({box:Studio.box(heading),mask:heading.node.style.maskImage,offsets:heading.typingRuns.map(r=>[r.range.startOffset,r.text.length]),style:{fill:getComputedStyle(heading.node).webkitTextFillColor,background:getComputedStyle(heading.node).backgroundImage}})'),flush=True)
    assert len(empty.getcolors(empty.width*empty.height) or [])<4,'Untyped gradient text leaked into the page'
    assert len(partial.getcolors(partial.width*partial.height) or [])>20,'Gradient text was not progressively painted'
    page.evaluate('Studio.choreography.clearText(heading);Studio.replay();Studio.pause(true);for(let i=0;i<480;i++)Studio.tick(1/60);Studio.stop()')
    assert page.evaluate('Studio.doc.querySelectorAll("[data-sw-state]").length')==0
    assert page.evaluate('Studio.frame.contentWindow.CSS.highlights.has("swarm-untyped")') is False
    # Previously saved projects do not have explicit frame dependency phases.
    # They must receive the same crew behavior without needing recapture.
    shutil.copytree(root/'project',root/'legacy',dirs_exist_ok=True)
    legacy=json.loads((root/'legacy/metadata/blueprint.json').read_text('utf-8'))
    for task in legacy['tasks']:task.pop('dependencyPhases',None)
    (root/'legacy/metadata/blueprint.json').write_text(json.dumps(legacy),'utf-8')
    page.evaluate('(url)=>Studio.load(url,{agents:8,intro:false,auto_tour:true})',server.url('legacy')+'/')
    page.evaluate('Studio.pause(true)')
    for _ in range(160):
      if page.evaluate('Studio.finished'):break
      page.evaluate('for(let i=0;i<120&&!Studio.finished;i++)Studio.tick(1/60)')
    assert page.evaluate('Studio.finished&&Studio.failed===0')
    result['legacy_replay']=True
    assert not errors,errors
    (root/'results.json').write_text(json.dumps(result,indent=2),'utf-8')
    print('PASS Adaptive crew and exact choreography',json.dumps(result),flush=True)
    browser.close()
finally:server.close()
