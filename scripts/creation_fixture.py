"""Original website and a local streaming model simulator; never used by production."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CSS = '''body{background:#f2f0e8;color:#243c32;font-family:Arial,sans-serif}header,section,footer{padding:28px max(6vw,24px)}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #243c3222}a{color:inherit;text-decoration:none}nav{display:flex;gap:24px}h1{font:500 clamp(44px,6.4vw,88px)/1.04 Georgia,serif;letter-spacing:-3px;margin:20px 0}h2{font:500 36px Georgia,serif}p{line-height:1.7;max-width:520px}.hero{display:grid;grid-template-columns:1.1fr 1fr;align-items:center;gap:7vw;min-height:520px}.eyebrow{font-size:11px;letter-spacing:2px;text-transform:uppercase}.art{border-radius:48% 48% 8px 8px;background:#dce4d0;padding:24px}.art svg{display:block;width:100%}button,.button{display:inline-block;background:#244d3c;color:#fff;padding:14px 22px;border:0;border-radius:5px;cursor:pointer}button:hover,.button:hover{background:#38664f}button:focus-visible,a:focus-visible{outline:3px solid #a87b45;outline-offset:4px}.features{display:grid;grid-template-columns:1fr 1fr;gap:24px;border-top:1px solid #243c3222}footer{border-top:1px solid #243c3222;font-size:13px;display:flex;justify-content:space-between}.price{background:#dae3d3}.price strong{font-size:38px}@media(max-width:600px){.hero,.features{grid-template-columns:1fr}.hero{padding-top:28px}nav{gap:10px;font-size:12px}h1{letter-spacing:-1.5px}footer{display:block}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}'''
ART = '<div class="art"><svg viewBox="0 0 300 300" role="img" aria-label="Original illustration of shared growth"><circle cx="150" cy="150" r="128" fill="#6e895b"/><circle cx="150" cy="150" r="92" fill="#a2b58a"/><circle cx="150" cy="150" r="52" fill="#e9ead1"/><path d="M150 10v280M10 150h280" stroke="#f2f0e8" stroke-width="2"/></svg></div>'


def hero(edited=False):
    return '<section class="hero" id="hero"><div><span class="eyebrow">A studio for good work</span><h1>' + ('Make room for something better.' if edited else 'Good things grow together.') + '</h1><p>We help thoughtful teams turn small beginnings into lasting places, products and ideas.</p><button id="counter" type="button">Start a conversation</button></div>' + ART + '</section>'


def operations(edit=False):
    if edit:
        return [dict(action='plan', steps=['Refine the headline', 'Add pricing', 'Remove the footer']),
                dict(action='upsert_block', id='hero', html=hero(True), css='', js=''),
                dict(action='upsert_block', id='pricing', before='features', html='<section class="price" id="pricing"><span class="eyebrow">A clear starting point</span><h2>A focused first step.</h2><strong>$900</strong><p>A working session, a practical direction and room to grow.</p></section>', css='', js=''),
                dict(action='remove_block', id='footer'),dict(action='finish', summary='Refined the hero headline, added pricing and removed the footer. The other sections are unchanged.')]
    return [dict(action='plan', steps=['Set the visual direction', 'Build the opening', 'Add the details']),
            dict(action='set_title', title='Fieldwork Studio'),dict(action='set_theme', css=CSS),
            dict(action='upsert_block', id='header', html='<header><a href="#hero"><strong>fieldwork.</strong></a><nav aria-label="Main"><a href="#features">Our approach</a><a href="#footer">Contact</a></nav></header>', css='', js=''),
            dict(action='upsert_block', id='hero', html=hero(), css='', js=''),
            dict(action='upsert_block', id='features', html='<section class="features" id="features"><div><span class="eyebrow">01 / Practice</span><h2>Begin with care.</h2><p>Good work starts by understanding the people and places it is for.</p></div><div><span class="eyebrow">02 / Partnership</span><h2>Build it together.</h2><p>A shared process makes room for better questions and stronger ideas.</p></div></section>', css='', js=''),
            dict(action='upsert_block', id='footer', html='<footer id="footer"><span>Fieldwork Studio · Original test website</span><span>Made with care, together.</span></footer>', css='', js=''),
            dict(action='set_script', js="document.addEventListener('click',event=>{if(event.target.id==='counter'){event.target.textContent='Conversation started locally';event.target.dataset.clicked='true'}})"),
            dict(action='finish', summary='Built the responsive studio website with navigation, custom SVG artwork and an interactive local button.')]


class FixtureProvider:
    def __init__(self, pause_first=False, status=200, malformed=False, single_operation=False):
        self.requests = [];self.hero_sent = threading.Event();self.release = threading.Event()
        self.pause_first, self.status, self.malformed = pause_first, status, malformed
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append(body)
                self.send_response(owner.status);self.send_header('Content-Type', 'text/event-stream');self.end_headers()
                if owner.status != 200:return
                last = body['messages'][-1]['content']
                review = isinstance(last, str) and last.startswith('Final quality pass')
                content = body['messages'][1]['content']
                if isinstance(content, list):content=next(part['text'] for part in content if part['type']=='text')
                context = json.loads(content)
                edit = 'change' in context['instruction'].lower() or 'remove' in context['instruction'].lower()
                commands = [dict(action='finish', summary='Checked the responsive layout and interactions.')] if review else operations(edit)
                if single_operation and not review:
                    commands=[commands[min(len(owner.requests)-1,len(commands)-1)]]
                if owner.malformed:
                    commands = []
                    chunks = ['not valid authoring output']
                else:
                    chunks = [(json.dumps(command, ensure_ascii=False) + '\n', command) for command in commands]
                try:
                    for item in chunks:
                        text, command = item if isinstance(item, tuple) else (item, {})
                        for offset in range(0, len(text), 113):
                            event = {'choices': [{'delta': {'content': text[offset:offset+113]}, 'finish_reason': None}]}
                            self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode());self.wfile.flush()
                            time.sleep(.001)
                        if command.get('id') == 'hero' and not edit and not review:
                            owner.hero_sent.set()
                            if owner.pause_first:owner.release.wait(20)
                    self.wfile.write(b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n');self.wfile.flush()
                except OSError:pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler);self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.endpoint=f'http://127.0.0.1:{self.server.server_port}/v1'

    def close(self):
        self.release.set();self.server.shutdown();self.server.server_close();self.thread.join(2)
