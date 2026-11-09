"""Shared live choreography, responsive audit, sandboxed interactions and offline export."""
import json
from pathlib import Path
import shutil
import sys
import uuid
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright
from app.config import WEB
from app.creation import CreationStore,WebsiteDocument
from app.server import PreviewServer
from scripts.creation_fixture import operations

root=(Path('test-results/creation-browser')/uuid.uuid4().hex[:10]).resolve();root.mkdir(parents=True)
shutil.copytree(WEB,root/'ui');server=PreviewServer(root)
document=WebsiteDocument()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='msedge',headless=True)
  page=browser.new_page(viewport={'width':1280,'height':720})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(server.url('ui/create.html'));page.wait_for_function('Creator.ready')
  page.evaluate('window.recorded=[];window.studioBridge={publish:raw=>recorded.push(JSON.parse(raw))};Creator.begin();Studio.pause(true)')
  for op in operations():
   normalized=document.apply(op)
   if op['action']!='finish':page.evaluate('command=>Creator.patch(command)',normalized)
  # The renderer and visibility masks are the actual reconstruction engine.
  assert page.evaluate('Studio.crew instanceof WorkingCrew&&Studio.choreography instanceof TaskChoreography&&Studio.camera instanceof CinematicTour')
  page.evaluate('for(let i=0;i<200;i++)Studio.tick(1/60);Studio.draw()')
  assert page.evaluate('Studio.doc.querySelectorAll("[data-sw-state=pending]").length>0')
  assert page.evaluate('Studio.frame.contentWindow.getComputedStyle(Studio.doc.documentElement).scrollBehavior')=='auto'
  page.screenshot(path=str(root/'shared-swarm.png'))
  page.evaluate('Creator.end();for(let i=0;i<20000&&!Studio.finished;i++)Studio.tick(1/60);Studio.draw()')
  assert page.evaluate('Studio.finished&&Studio.failed===0')
  assert page.evaluate('recorded.some(e=>e.type==="inspected")&&recorded.some(e=>e.type==="handoff")')
  assert page.evaluate('Studio.history.some(h=>Studio.byId.get(h.task)?.operation==="duplicate")')
  # A one-line text edit keeps every surrounding node and animates only h1.
  page.evaluate('window.originalHero=Creator.block("hero").firstElementChild;window.originalArt=Creator.block("hero").querySelector("svg");window.originalButton=Studio.doc.querySelector("#counter");Creator.begin();Studio.pause(true)')
  hero_block=next(b for b in document.data['blocks'] if b['id']=='hero')
  edit=dict(hero_block,action='upsert_block',html=hero_block['html'].replace('Good things grow together.',"Don't Work Smarter!"))
  page.evaluate('command=>Creator.patch(command)',edit)
  assert page.evaluate('Creator.block("hero").firstElementChild===originalHero&&Creator.block("hero").querySelector("svg")===originalArt&&Studio.doc.querySelector("#counter")===originalButton')
  assert page.evaluate('Studio.tasks.length===1&&Studio.elements.get(Studio.tasks[0].element).tag==="h1"&&Studio.tasks[0].operation==="type"')
  assert page.evaluate('!originalArt.hasAttribute("data-sw-state")&&!originalButton.hasAttribute("data-sw-state")')
  page.evaluate('Creator.end();for(let i=0;i<20000&&!Studio.finished;i++)Studio.tick(1/60);Studio.draw()')
  assert page.evaluate('Creator.block("hero").querySelector("h1").textContent')=="Don't Work Smarter!"
  page.evaluate('Creator.begin();Studio.pause(true)')
  page.evaluate('command=>Creator.patch(command)',dict(hero_block,action='upsert_block'))
  page.evaluate('Creator.end();for(let i=0;i<20000&&!Studio.finished;i++)Studio.tick(1/60);Studio.draw()')
  # Real generated scripts run only in the opaque-origin interactive iframe.
  page.evaluate('Creator.preview(true)')
  interactive=page.frame_locator('#interactive')
  interactive.locator('#counter').click()
  assert interactive.locator('#counter').get_attribute('data-clicked')=='true'
  assert interactive.locator('body').evaluate('()=>typeof window.qt')=='undefined'
  assert interactive.locator('body').evaluate('()=>{try{void parent.document.body;return false}catch(e){return e.name==="SecurityError"}}')
  assert interactive.locator('body').evaluate('async()=>{try{await fetch("https://example.com/should-not-load");return false}catch(_){return true}}')
  page.evaluate('Creator.preview(false);Creator.begin();Studio.pause(true)')
  untouched=document.data['blocks'][2].copy()
  for op in operations(True):
   normalized=document.apply(op)
   if op['action']!='finish':page.evaluate('command=>Creator.patch(command)',normalized)
  page.evaluate('Creator.end();for(let i=0;i<20000&&!Studio.finished;i++)Studio.tick(1/60);Studio.draw()')
  assert page.evaluate('Studio.finished&&Studio.failed===0&&!Creator.block("footer")&&Boolean(Creator.block("pricing"))')
  assert document.data['blocks'][-1]==untouched
  assert page.evaluate('Studio.history.some(h=>Studio.byId.get(h.task)?.operation==="remove")')
  page.evaluate('Creator.requestAudit("browser-test")')
  page.wait_for_function('recorded.some(e=>e.type==="creator-audit"&&e.token==="browser-test")')
  audit=page.evaluate('recorded.find(e=>e.type==="creator-audit"&&e.token==="browser-test").report')
  assert audit['390']['horizontal_overflow']<=1 and audit['1280']['horizontal_overflow']<=1,audit
  store=CreationStore(root/'data');project=store.new();store.commit(project,document.data,'Browser fixture')
  store.export(project,root/'site.zip')
  with zipfile.ZipFile(root/'site.zip') as archive:archive.extractall(root/'exported')
  # No source model server is involved in loading or operating the exported site.
  page.goto(server.url('exported/index.html'));page.locator('#counter').click()
  assert page.locator('#counter').get_attribute('data-clicked')=='true'
  for width in [390,768,1440]:
   page.set_viewport_size({'width':width,'height':850})
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  page.screenshot(path=str(root/'offline-export.png'))
  assert not errors,errors
  report={'same_renderer_classes':True,'shared_typing_visibility_masks':True,'shared_handoffs_and_duplication':True,
          'animated_removal':True,'targeted_text_edit_preserves_dom':True,'opaque_interactive_origin':True,'native_bridge_inaccessible':True,'network_blocked':True,
          'working_interactions':True,'responsive_audit':audit,'offline_zip_interactions':True,'evidence':str(root)}
  (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  Path('test-results/creation-browser/latest.json').write_text(json.dumps(str(root)),encoding='utf-8')
  print('PASS creation browser',json.dumps(report),flush=True)
  browser.close()
finally:server.close()
