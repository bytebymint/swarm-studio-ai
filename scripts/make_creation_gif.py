"""Record the real Qt Create workspace with an original local SaaS fixture.

No provider API is called. The README labels this as an accelerated local demo.
"""
import io
import json
import os
from pathlib import Path
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import QBuffer, QCoreApplication, QIODevice, Qt
from PySide6.QtWidgets import QApplication
from scripts import creation_fixture

PROMPT = 'Build a SaaS website for Relay, a workflow automation business. Use 4 sections: hero, features, pricing, and contact. Dark navy, mint accents, a dashboard visual, and responsive layouts.'
CSS = '''body{background:#101c24;color:#eaf3ef;font-family:Arial,sans-serif}section{padding:58px 6%}nav{display:flex;justify-content:space-between;align-items:center;margin-bottom:65px}nav strong{font-size:26px;letter-spacing:-1px}nav span{font-size:13px;color:#9eb6b1}h1{font-size:clamp(38px,5vw,68px);line-height:1.04;letter-spacing:-3px;font-weight:500;margin:20px 0}h2{font-size:36px;letter-spacing:-1.5px;font-weight:500;margin:12px 0 24px}p{color:#9eb6b1;line-height:1.7;font-size:15px;max-width:440px}.eyebrow{font-size:11px;letter-spacing:2px;color:#9de3bf}.hero-grid{display:grid;grid-template-columns:1fr 1fr;gap:45px;align-items:center}.hero-grid em{color:#a6eac9;font-style:normal}button,.cta{display:inline-block;padding:14px 22px;border:0;border-radius:7px;background:#b9e7ce;color:#142c23;font-weight:bold;text-decoration:none;margin-top:16px}.dashboard{background:#192c34;border:1px solid #365049;border-radius:14px;padding:25px}.dashboard small{color:#a7bcb5}.metric{font-size:44px;margin:20px 0 6px;letter-spacing:-2px}.bars{height:130px;display:flex;align-items:end;gap:12px;margin:25px 0}.bars i{flex:1;background:#9ddcba;border-radius:4px 4px 0 0}.row{display:flex;justify-content:space-between;padding:12px 0;border-top:1px solid #365049;font-size:12px;color:#bdd1c9}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.card{border-top:1px solid #3c5551;padding:24px 0}.card h3{font-size:21px;font-weight:500}.card b{color:#b9e7ce;font-size:12px}#features{background:#e4ece4;color:#142c23}#features p{color:#53645b}#pricing{border-bottom:1px solid #365049}.price{padding:28px;border:1px solid #365049;border-radius:12px;background:#192c34}.price strong{font-size:42px;font-weight:500}#contact{display:flex;justify-content:space-between;gap:24px;align-items:center}footer{margin-top:35px;color:#92aaa0;font-size:11px}@media(max-width:650px){.hero-grid,.grid{grid-template-columns:1fr}#contact{display:block}h1{letter-spacing:-1.5px}}'''


def operations(_edit=False):
    sections = [
        ('hero', '<section id="hero"><nav><strong>relay<span style="color:#a6eac9">.</span></strong><span>WORK BETTER, TOGETHER</span></nav><div class="hero-grid"><div><span class="eyebrow">LESS BUSYWORK. MORE MOMENTUM.</span><h1>Your work.<br><em>In a better flow.</em></h1><p>Connect your tools, automate the repetitive, and give your team room to do its best work.</p><a class="cta" href="#pricing">Find your plan →</a></div><div class="dashboard"><small>YOUR WORKSPACE / THIS WEEK</small><div class="metric">2,480 <span style="font-size:13px;color:#a6eac9">+24%</span></div><small>hours returned to your team</small><div class="bars"><i style="height:25%"></i><i style="height:45%"></i><i style="height:38%"></i><i style="height:62%"></i><i style="height:55%"></i><i style="height:83%"></i><i style="height:100%"></i></div><div class="row"><span>Customer onboarding</span><span>● Running</span></div><div class="row"><span>Weekly reporting</span><span>● Complete</span></div></div></div></section>'),
        ('features', '<section id="features"><span class="eyebrow" style="color:#436952">01 / MAKE SPACE FOR GOOD WORK</span><h2>One workspace. Fewer moving parts.</h2><div class="grid"><article class="card"><b>01 — CONNECT</b><h3>Bring your tools together.</h3><p>Keep the handoffs clear with connected workflows built around your team.</p></article><article class="card"><b>02 — AUTOMATE</b><h3>Let the routine run itself.</h3><p>Build repeatable processes and spend less of your day chasing updates.</p></article><article class="card"><b>03 — UNDERSTAND</b><h3>See what moves you forward.</h3><p>Turn everyday activity into a clear picture of your team’s progress.</p></article></div></section>'),
        ('pricing', '<section id="pricing"><span class="eyebrow">02 / A CLEAR WAY TO START</span><h2>Small team. Big possibilities.</h2><div class="grid"><article class="price"><h3>Starter</h3><strong>$19</strong><p>Per month. Five workflows for finding your flow.</p><a class="cta" href="#contact">Talk to us</a></article><article class="price"><h3>Team</h3><strong>$49</strong><p>Per month. More room for teams building momentum.</p><a class="cta" href="#contact">Explore Team</a></article><article class="price"><h3>Scale</h3><strong>Let’s talk</strong><p>A considered setup for your next stage of growth.</p><a class="cta" href="#contact">Start a conversation</a></article></div></section>'),
        ('contact', '<section id="contact"><div><span class="eyebrow">03 / YOUR NEXT CHAPTER</span><h2>Make room for better work.</h2><p>A fictional SaaS business, built for this original SWARM STUDIO demo.</p><footer>relay. / ORIGINAL LOCAL DEMO / 2026</footer></div><a class="cta" href="#hero">Back to the top ↑</a></section>'),
    ]
    return [dict(action='plan', steps=['Design the hero', 'Build features', 'Add pricing', 'Finish contact']), dict(action='set_title', title='Relay — Workflow automation'), dict(action='set_theme', css=CSS)] + [dict(action='upsert_block', id=i, html=h, css='', js='') for i,h in sections] + [dict(action='finish', summary='Built four responsive sections: hero, features, pricing and contact.')]


def main():
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication([])
    from app.desktop import MainWindow
    root = (Path('test-results/creation-gif') / uuid.uuid4().hex[:10]).resolve()
    root.mkdir(parents=True)
    # Local-only provider and synthetic process key; never touch the user's key.
    os.environ['QWEN_API_KEY'] = 'LOCAL-DEMO-NOT-A-REAL-KEY'
    creation_fixture.operations = operations
    provider = creation_fixture.FixtureProvider()
    window = MainWindow(root/'data'); window.resize(1440,900); window.show()

    def wait(predicate, timeout=40):
        until = time.monotonic()+timeout
        while time.monotonic()<until:
            app.processEvents()
            if predicate():return
            time.sleep(.01)
        raise RuntimeError('Demo timed out')

    def js(code):
        result=[]; c.view.page().runJavaScript(code,result.append)
        wait(lambda: bool(result));return result[0]

    frames=[]
    def grab(zoom=1, focus=None):
        app.processEvents();buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        window.grab().save(buffer,'PNG')
        picture=Image.open(io.BytesIO(bytes(buffer.data()))).convert('RGB')
        w,h=picture.size
        if zoom>1:
            x,y=focus;x*=w/window.width();y*=h/window.height();cw,ch=w/zoom,h/zoom
            left=max(0,min(w-cw,x-cw/2));top=max(0,min(h-ch,y-ch/2))
            picture=picture.crop((left,top,left+cw,top+ch))
        picture=picture.resize((960,600),Image.Resampling.LANCZOS)
        draw=ImageDraw.Draw(picture);draw.rectangle((0,575,960,600),fill='#101719')
        draw.text((16,581),'LOCAL DEMO RESPONSE  /  REAL SWARM RENDERER  /  ACCELERATED PLAYBACK',fill='#b9d5c9')
        frames.append(picture)

    try:
        window.create_choice.click();c=window.creator;wait(lambda:c.browser_ready)
        c.config.update(endpoint=provider.endpoint,model='local-demo',review=False)
        c.refresh();app.processEvents()
        point=c.prompt.mapTo(window,c.prompt.rect().center());focus=(point.x(),point.y())
        for i in range(45):
            c.prompt.setPlainText(PROMPT[:round(len(PROMPT)*min(1,(i+1)/30))])
            p=min(1,i/12);q=max(0,min(1,(i-30)/14))
            smooth=lambda x:x*x*(3-2*x)
            grab(1+1.15*smooth(p)*(1-smooth(q)),focus)
        c.submit()
        wait(lambda:c.worker and not c.worker.isRunning())
        js('Studio.externalClock=true;Studio.paused=false;Studio.settings.speed=1;true')
        total=js('Studio.tasks.length');assert total>20
        for i in range(135):
            # Fixed virtual steps keep capture smooth independent of machine speed.
            js('for(let n=0;n<70&&!Studio.finished;n++)Studio.tick(1/60);Studio.draw();true')
            app.processEvents();time.sleep(.025);grab()
        assert len(c.project['document']['blocks'])==4
        assert len(provider.requests)==1
        assert js('Studio.failed===0&&Studio.finished'), js('JSON.stringify({tasks:Studio.tasks.length,done:Studio.done,failed:Studio.failed,time:Studio.time,finished:Studio.finished})')
        atlas=Image.new('RGB',(960,600))
        for i,index in enumerate([0,15,30,45,60,75,90,105,120,135,150,165]):
            atlas.paste(frames[index].resize((240,200)),((i%4)*240,(i//4)*200))
        palette=atlas.quantize(colors=128,method=Image.Quantize.MEDIANCUT)
        result=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
        destination=Path('docs/media/create-saas-demo.gif');destination.parent.mkdir(parents=True,exist_ok=True)
        delays=[round((i+1)*100/15)*10-round(i*100/15)*10 for i in range(len(result))]
        result[0].save(destination,save_all=True,append_images=result[1:],duration=delays,loop=0,optimize=True,disposal=1)
        frames[30].save(root/'prompt-closeup.png');frames[85].save(root/'building.png');frames[-1].save(root/'finish.png')
        report={'file':str(destination),'duration_ms':sum(delays),'frames':len(frames),'sections':4,'tasks':total,'provider':'local simulator; no AI tokens used','bytes':destination.stat().st_size,'evidence':str(root)}
        (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report),flush=True)
    finally:
        if window.creator and window.creator.worker and window.creator.worker.isRunning():
            window.creator.worker.cancel();wait(lambda:not window.creator.worker.isRunning())
        window.close();app.processEvents();provider.close()


if __name__=='__main__':main()
