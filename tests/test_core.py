import json
import threading
import zipfile
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.blueprint import DependencyGraph, build_blueprint
from app.config import Settings
from app.projects import ProjectStore
from app.reconstruction import reconstruct
from app.server import PreviewServer
from app.urls import normalize_url
from app.validation import compare_images


def test_urls():
    assert normalize_url('example.com') == 'https://example.com'
    assert normalize_url(' localhost:8000/a ') == 'http://localhost:8000/a'
    assert normalize_url('127.0.0.1:3000') == 'http://127.0.0.1:3000'
    for value in ['file:///C:/secret','javascript:alert(1)','https://me:password@example.com','https://x.test/?access_token=secret','https://example.com:bad','']:
        with pytest.raises(ValueError):normalize_url(value)


def test_graph_dependencies_failures_cancellation():
    tasks=[{'id':'a','dependencies':[]},{'id':'b','dependencies':['a']},{'id':'c','dependencies':['b']}]
    graph=DependencyGraph(tasks)
    assert graph.assign('Ada')['id']=='a'
    assert graph.assign('Ada') is None
    assert graph.assign('Grace') is None
    graph.finish('Ada')
    assert graph.assign('Grace')['id']=='b'
    graph.finish('Grace',False)
    assert graph.tasks['c']['status']=='blocked'
    assert not graph.complete
    graph=DependencyGraph(tasks)
    graph.assign('Ada');graph.cancel()
    assert graph.assign('Grace') is None
    assert not graph.owners
    assert DependencyGraph([]).complete
    with pytest.raises(ValueError):DependencyGraph([{'id':'a','dependencies':['a']}])
    with pytest.raises(ValueError):DependencyGraph([{'id':'a','dependencies':['missing']}])


def test_projects_and_settings(tmp_path):
    settings=Settings(tmp_path/'settings.json')
    settings.save({'speed':3.0,'names':False})
    assert Settings(settings.path).values['speed']==3.0
    store=ProjectStore(tmp_path)
    project_id,folder=store.allocate()
    (folder/'metadata').mkdir()
    (folder/'metadata/project.json').write_text(json.dumps({'name':'Fixture','url':'https://example.com'}))
    (folder/'metadata/blueprint.json').write_text('{"elements":[]}')
    (folder/'index.html').write_text('<html></html>')
    store.register(project_id,{'name':'Fixture','url':'https://example.com'})
    assert store.load(project_id)[1]['name']=='Fixture'
    assert store.recent()[0][0]==project_id
    with pytest.raises(ValueError):store.load('../outside')
    (folder/'index.html').unlink()
    with pytest.raises(ValueError):store.load(project_id)
    store.close()


def test_crew_migration_and_frame_handoff(tmp_path):
    path=tmp_path/'settings.json'
    path.write_text('{"agents":24}',encoding='utf-8')
    assert Settings(path).values['agents']==8
    path.write_text('{"agents":4}',encoding='utf-8')
    assert Settings(path).values['agents']==4
    tasks=[{'id':'frame','dependencies':[]},
           {'id':'text','dependencies':['frame'],'dependencyPhases':{'frame':'frame'}},
           {'id':'copy','dependencies':['frame','text'],'dependencyPhases':{'frame':'frame','text':'complete'}}]
    graph=DependencyGraph(tasks)
    assert graph.assign('Ada')['id']=='frame'
    assert not graph.ready()
    graph.mark_frame('Ada')
    assert graph.assign('Grace')['id']=='text'
    assert graph.assign('Linus') is None
    graph.finish('Grace')
    assert graph.assign('Linus')['id']=='copy'
    graph.finish('Ada');graph.finish('Linus')
    assert graph.complete


def test_pixel_difference(tmp_path):
    a=tmp_path/'a.png';b=tmp_path/'b.png';diff=tmp_path/'diff.png'
    Image.new('RGB',(20,20),'white').save(a)
    Image.new('RGB',(20,20),'white').save(b)
    assert compare_images(a,b,diff)['mean_absolute_rgb_difference']==0
    Image.new('RGB',(20,20),'black').save(b)
    assert compare_images(a,b,diff)['mean_absolute_rgb_difference']==255
    assert diff.exists()


def test_reconstruction_local_assets_privacy_and_css(tmp_path):
    source=tmp_path/'source';source.mkdir()
    (source/'image.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><rect width="12" height="12" fill="red"/></svg>')
    (source/'font.woff2').write_bytes(b'font-fixture')
    (source/'nested.css').write_text('@font-face{font-family:Fixture;src:url(font.woff2)}')
    server=PreviewServer(source)
    try:
        capture={'title':'Fixture','url':server.origin+'/index.html','viewport':{'width':800,'height':600,'dpr':1},'height':600,'elements':[
            {'id':'s1','parent':None,'tag':'main','kind':'container','class':'','text':'','rect':{'x':0,'y':0,'w':800,'h':600}},
            {'id':'s2','parent':'s1','tag':'h1','kind':'text','class':'','text':'Actual text','rect':{'x':0,'y':0,'w':200,'h':50}}],
            'sheets':[{'text':'@import "nested.css"; .hero{background:url(image.svg)}','base':server.origin+'/'}],
            'computedCSS':'','resources':[server.origin+'/image.svg'],'fonts':[],'warnings':[],
            'html':f'<html><head><title>Fixture</title></head><body><main data-sw-id="s1"><h1 data-sw-id="s2">Actual text</h1><img src="{server.origin}/image.svg"><input value="SECRET" name="password"><textarea>SECRET</textarea><input type="hidden" value="TOKEN"><script>alert(1)</script><a href="javascript:alert(1)" onclick="alert(2)">Bad</a><form action="https://bad.test"><button>Submit</button></form></main></body></html>'}
        metadata,blueprint=reconstruct(capture,tmp_path/'output',{})
        html=(tmp_path/'output/index.html').read_text('utf-8')
        assert 'SECRET' not in html and 'TOKEN' not in html and '<script' not in html and 'onclick=' not in html
        assert 'javascript:' not in html and '<h1 data-sw-id="s2">Actual text</h1>' in html
        assert 'assets/images/image-' in html
        assert len(list((tmp_path/'output/assets').rglob('*.*')))==3
        assert metadata['assets']==3
        assert blueprint['tasks'][1]['dependencies']==['s1']
        assert 'http://' not in (tmp_path/'output/styles/reconstructed.css').read_text()
        from app.assets import URL_PATTERN
        for stylesheet in (tmp_path/'output').rglob('*.css'):
            for match in URL_PATTERN.finditer(stylesheet.read_text()):
                ref=match.group(2)
                if ref and not ref.startswith(('data:','#')):
                    assert (stylesheet.parent/ref).is_file(), f'Broken CSS resource: {stylesheet}: {ref}'
        cancel=threading.Event();cancel.set()
        with pytest.raises(InterruptedError):reconstruct(capture,tmp_path/'cancelled',{},cancel)
        with httpx.Client(trust_env=False) as client:
            assert client.get(server.origin+'/image.svg').status_code==200
            assert client.get(server.origin+'/.secret').status_code==403
            assert client.post(server.origin+'/image.svg').status_code==501
    finally:server.close()
