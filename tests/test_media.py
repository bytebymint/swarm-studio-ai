import asyncio
import json
import threading
import httpx
import pytest
from app.assets import AssetCollector
from app.server import PreviewServer
from scripts.media_fixture import create_media
from app.urls import resource_url


@pytest.mark.parametrize('query',['access_token=secret','Policy=secret','sig=secret','X-Amz-Credential=secret','Key-Pair-Id=secret'])
def test_secret_media_addresses(query):
    assert resource_url('https://example.test/movie.mp4?'+query) is None


@pytest.fixture
def media(tmp_path):
    root=create_media(tmp_path/'source');server=PreviewServer(root)
    yield root,server
    server.close()


def test_range_security_and_head(media):
    root,server=media;data=(root/'original.mp4').read_bytes()
    with httpx.Client(trust_env=False) as client:
        for header,start,end in [('bytes=0-9',0,9),('bytes=10-',10,len(data)-1),('bytes=-8',len(data)-8,len(data)-1)]:
            r=client.get(server.url('original.mp4'),headers={'Range':header})
            assert r.status_code==206 and r.content==data[start:end+1]
            assert r.headers['content-range']==f'bytes {start}-{end}/{len(data)}'
        assert client.head(server.url('original.mp4'),headers={'Range':'bytes=0-9'}).headers['content-length']=='10'
        assert client.get(server.url('original.mp4'),headers={'Range':'bytes=999999-'}).status_code==416
        assert client.get(server.url('original.mp4'),headers={'Range':'bytes=-0'}).status_code==416
        assert client.get(server.url('original.mp4'),headers={'Range':'bytes=0-1,4-5'}).status_code==400
        assert client.get(server.url('.hidden')).status_code==403
        assert client.get(server.url('../outside')).status_code!=200


def test_streaming_limits_dedup_and_failures(media,tmp_path):
    root,server=media
    urls=[server.url('original.mp4'),server.url('original.webm')]
    async def collect(settings,cancel=None):
        c=AssetCollector(tmp_path/str(len(settings)),settings,cancel)
        result=await c.collect({'resources':urls*2+[server.url('missing.mp4')],'elements':[],'url':server.origin})
        return c
    c=asyncio.run(collect({}))
    assert len(c.mapping)==2 and len(c.media_info)==2
    assert all('/media/' in p for p in c.mapping.values())
    assert {v['mime'] for v in c.media_info.values()}=={'video/mp4','video/webm'}
    assert c.warnings
    c=asyncio.run(collect({'max_video_mb':0}));assert not c.mapping
    c=asyncio.run(collect({'max_total_media_mb':0}));assert not c.mapping
    cancel=threading.Event();cancel.set();c=asyncio.run(collect({},cancel));assert not c.mapping
    assert not list(tmp_path.rglob('*.partial'))


def test_media_redirects_and_invalid_container(tmp_path):
    async def run():
        c=AssetCollector(tmp_path,{})
        def handler(request):
            if request.url.path=='/redirect':return httpx.Response(302,headers={'location':'https://example.test/file.mp4?token=SECRET'})
            return httpx.Response(200,headers={'content-type':'video/mp4'},content=b'not a video')
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert await c.fetch_video(client,'https://example.test/redirect') is None
            assert await c.fetch_video(client,'https://example.test/bad.mp4') is None
        assert 'SECRET' not in json.dumps(c.warnings)
        assert not c.mapping and c.media_total==0 and not list(tmp_path.rglob('*.partial'))
    asyncio.run(run())


def test_media_cookie_isolation_octet_stream_and_hls(media,tmp_path):
    root,_=media;payload=(root/'original.mp4').read_bytes();seen=[]
    async def run():
        c=AssetCollector(tmp_path/'downloads',{})
        def handler(request):
            seen.append(request)
            if request.url.path=='/stream':return httpx.Response(200,headers={'content-type':'application/vnd.apple.mpegurl'},content=b'#EXTM3U')
            return httpx.Response(200,headers={'content-type':'application/octet-stream','set-cookie':'private=secret'},content=payload)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler),cookies={'session':'private'}) as client:
            assert await c.fetch_video(client,'https://example.test/a.mp4')
            assert await c.fetch_video(client,'https://example.test/b.mp4')
            assert await c.fetch_video(client,'https://example.test/stream') is None
        assert all(not r.headers.get('cookie') and not r.headers.get('authorization') for r in seen)
        assert len(c.mapping)==2
    asyncio.run(run())


def test_cancel_mid_stream(media,tmp_path):
    root,_=media;cancel=threading.Event();payload=(root/'original.mp4').read_bytes()
    class InterruptedStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield payload[:64]
            cancel.set()
            yield payload[64:]
    async def run():
        c=AssetCollector(tmp_path/'cancel',{},cancel)
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,headers={'content-type':'video/mp4'},stream=InterruptedStream()))) as client:
            assert await c.fetch_video(client,'https://example.test/file.mp4') is None
        assert c.media_total==0 and not c.mapping and not list(tmp_path.rglob('*.partial'))
        assert list(c.media_failures.values())==['cancelled']
    asyncio.run(run())


def test_video_budget_does_not_consume_image_budget(media,tmp_path):
    root,server=media
    async def run():
        c=AssetCollector(tmp_path/'separate',{})
        c.total_limit=(root/'poster.png').stat().st_size+1
        url=server.url('original.mp4');c.media_urls.add(url)
        async with httpx.AsyncClient(trust_env=False) as client:
            assert await c.fetch(client,url)
            assert c.total>c.total_limit
            assert await c.fetch(client,server.url('poster.png'))
        assert c.non_media_total<c.total_limit and len(c.mapping)==2
    asyncio.run(run())
