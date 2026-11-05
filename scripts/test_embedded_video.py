"""Detect known embeds without loading their scripts or claiming offline video."""
import json
import sys
import httpx
from unittest.mock import patch
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright
from app.config import WEB
from app.reconstruction import reconstruct
from app.server import PreviewServer

root=Path('test-results/embedded-video').resolve();root.mkdir(parents=True,exist_ok=True)
server=PreviewServer(root)
Image.new('RGB',(160,90),'#264f3a').save(root/'fixture-poster.png')
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1280,'height':800})
        page.route('**/*',lambda r:r.abort() if 'youtube.com/embed/' in r.request.url else r.continue_())
        page.goto(server.url('missing.html'))
        page.set_content('<html><head><style>body{margin:0}iframe{border:0;position:absolute;inset:0;width:100%;height:720px;aspect-ratio:16/9}</style></head><body><iframe src="https://www.youtube.com/embed/fixture0001?autoplay=1&token=SYNTHETIC"></iframe></body></html>')
        page.evaluate((WEB/'capture.js').read_text('utf-8'));page.evaluate('StudioCapture.start({timeout:15})');page.wait_for_function('StudioCapture.state.status==="complete"')
        capture=page.evaluate('StudioCapture.state.result')
        assert len(capture['media'])==1 and 'SYNTHETIC' not in json.dumps(capture)
        element=next(e for e in capture['elements'] if e['kind']=='media')
        assert element['media']['provider']=='youtube' and not element['media']['sources']
        assert element['media']['embedUrl']=='https://www.youtube.com/embed/fixture0001'
        assert element['media']['hosting']=='third-party'
        original_client=httpx.AsyncClient
        def thumbnail(request):
            assert str(request.url)=='https://i.ytimg.com/vi/fixture0001/hqdefault.jpg'
            return httpx.Response(200,headers={'content-type':'image/png'},content=(root/'fixture-poster.png').read_bytes())
        with patch('app.assets.httpx.AsyncClient',lambda **kwargs:original_client(transport=httpx.MockTransport(thumbnail),**kwargs)):
            with ThreadPoolExecutor() as pool:meta,bp=pool.submit(reconstruct,capture,root/'fixture',{}).result()
        item=next(e for e in bp['elements'] if e['kind']=='media')
        assert item['media']['status']=='poster-only',meta['warnings']
        assert item['operation']=='place_media' and not list((root/'fixture').rglob('*.mp4'))
        page.goto(server.url('fixture/index.html'))
        assert page.locator('iframe,video').count()==0
        assert page.get_by_text('YouTube video — thumbnail only; video not downloaded').count()==1
        assert page.locator('img').evaluate('i=>i.complete&&i.naturalWidth>0')
        rect=page.locator('[role=img]').bounding_box();assert abs(rect['width']-1280)<2 and abs(rect['height']-720)<2,rect
        page.screenshot(path=str(root/'thumbnail-fallback.png'))
        print('PASS: known YouTube embed detection, safe canonical metadata, downloaded thumbnail, layout and explicit fallback; no player scripts or video download',flush=True)
        browser.close()
finally:server.close()
