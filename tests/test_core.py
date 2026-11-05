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
