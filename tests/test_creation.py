import json
import os
import threading
import zipfile

import pytest

from app.creation import CommandStream, CreationStore, GenerationWorker, KeyVault, MODEL_DEFAULTS, QwenClient, WebsiteDocument, clean_html, endpoint_url
from scripts.creation_fixture import FixtureProvider, operations
from app.server import PreviewServer
import httpx


def test_document_targeted_edits_order_sanitization_and_atomic_failure():
    document=WebsiteDocument()
    for operation in operations():document.apply(operation)
    original=document.data['blocks'][2].copy()
    for operation in operations(True):document.apply(operation)
    assert [b['id'] for b in document.data['blocks']]==['header','hero','pricing','features']
    assert document.data['blocks'][-1]==original
    assert 'Make room for something better.' in document.render()
    assert '<script' not in clean_html('<script>alert(1)</script><img src="javascript:alert(1)" onerror="alert(1)"><iframe src="https://evil.test"></iframe><p>Safe</p>')
    assert 'onerror' not in clean_html('<img onerror="bad()" src="data:image/png;base64,AA==">')
    previous=json.dumps(document.data)
    with pytest.raises(ValueError):document.apply({'action':'upsert_block','id':'../bad','html':'bad'})
    assert json.dumps(document.data)==previous
    with pytest.raises(ValueError):document.apply({'action':'set_theme','css':'@import "https://bad.test";'})
    assert json.dumps(document.data)==previous


def test_incremental_parser_unicode_fences_and_incomplete_operations():
    parser=CommandStream();result=[]
    source='```json\n'+json.dumps({'action':'plan','steps':['Créer une page']},ensure_ascii=False)+'\n'+json.dumps({'action':'finish','summary':'Done'})+'\n```'
    for char in source:result.extend(parser.feed(char))
    result.extend(parser.feed('',True))
    assert [c['action'] for c in result]==['plan','finish']
    with pytest.raises(ValueError):CommandStream().feed('{"action":',True)
    with pytest.raises(ValueError):CommandStream().feed('x'*250001)


def test_store_revision_undo_redo_export_no_credentials(tmp_path):
    store=CreationStore(tmp_path);project=store.new();document=WebsiteDocument()
    for op in operations():document.apply(op)
    store.commit(project,document.data,'Create')
    for op in operations(True):document.apply(op)
    store.commit(project,document.data,'Edit')
    project['chat'].append({'role':'user','text':'PRIVATE PROMPT SHOULD NOT BE EXPORTED'})
    store.restore(project,0);assert any(b['id']=='footer' for b in project['document']['blocks'])
    store.restore(project,1);assert not any(b['id']=='footer' for b in project['document']['blocks'])
    store.save(project);assert store.load(project['id'])['document']==project['document']
    target=tmp_path/'site.zip';store.export(project,target)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())=={'index.html','README.txt'}
        html=archive.read('index.html').decode()
        assert 'Make room for something better.' in html
        assert 'PRIVATE PROMPT' not in html and 'API_KEY' not in html
    with pytest.raises(ValueError):store.load('../outside')
    project['draft_active']=True;store.save(project)
    document.apply({'action':'set_title','title':'Recovered title'})
    from app.projects import write_json
    write_json(store.path(project['id'])/'draft.json',document.data)
    recovered=store.load(project['id'])
    assert recovered['_recovered'] and recovered['document']['title']=='Recovered title'
    store.restore(recovered,recovered['cursor']-1)
    assert recovered['document']['title']!='Recovered title'


def test_streaming_provider_and_transport_errors():
    provider=FixtureProvider()
    try:
        client=QwenClient(dict(MODEL_DEFAULTS,endpoint=provider.endpoint),'SYNTHETIC')
        messages=[{'role':'system','content':'test'},{'role':'user','content':json.dumps({'instruction':'Create a studio website'})}]
        content=''.join(client.stream(messages));assert 'upsert_block' in content
        assert provider.requests[0]['stream'] is True and provider.requests[0]['enable_thinking'] is False
        event=threading.Event();event.set()
        with pytest.raises(InterruptedError):list(QwenClient(dict(MODEL_DEFAULTS,endpoint=provider.endpoint),'SYNTHETIC',event).stream(messages))
    finally:provider.close()
    provider=FixtureProvider(status=401)
    try:
        with pytest.raises(ValueError,match='key was rejected'):list(QwenClient(dict(MODEL_DEFAULTS,endpoint=provider.endpoint),'SECRET').stream(messages))
    finally:provider.close()
    for value in ['http://remote.test/v1','https://user:secret@host.test/v1','https://host.test/v1?key=secret','file:///private']:
        with pytest.raises(ValueError):endpoint_url(value)


def test_worker_repairs_protocol_and_validates_javascript():
    provider=FixtureProvider()
    try:
        worker=GenerationWorker(WebsiteDocument().data,'Create a studio website',dict(MODEL_DEFAULTS,endpoint=provider.endpoint,review=False),'SYNTHETIC')
        completed=[];problems=[];commands=[]
        worker.changed.connect(commands.append);worker.ready.connect(lambda d,s:completed.append(d));worker.problem.connect(lambda m,d:problems.append(m))
        worker.audit_requested.connect(lambda:worker.audit_event.set())
        worker.run()
        assert completed and not problems and len(commands)>5
        worker.document.data['script']='const = broken;'
        assert worker.script_error()
    finally:provider.close()


def test_agent_continues_single_operation_responses_and_cancels_stream():
    provider=FixtureProvider(single_operation=True)
    try:
        worker=GenerationWorker(WebsiteDocument().data,'Create',dict(MODEL_DEFAULTS,endpoint=provider.endpoint,review=False),'SYNTHETIC')
        completed=[];errors=[];worker.ready.connect(lambda d,s:completed.append(d));worker.problem.connect(lambda m,d:errors.append(m))
        worker.audit_requested.connect(lambda:worker.audit_event.set());worker.run()
        assert completed and not errors and len(provider.requests)>=8
        assert len(completed[0]['blocks'])==4
    finally:provider.close()
    provider=FixtureProvider(pause_first=True)
    client=QwenClient(dict(MODEL_DEFAULTS,endpoint=provider.endpoint),'SYNTHETIC')
    def consume():
        try:list(client.stream([{'role':'system','content':'test'},{'role':'user','content':json.dumps({'instruction':'Create'})}]))
        except Exception:pass
    thread=threading.Thread(target=consume,daemon=True);thread.start()
    try:
        assert provider.hero_sent.wait(10)
        client.stop();thread.join(3);assert not thread.is_alive(),'Cancelling must unblock an active stream'
    finally:
        provider.release.set();thread.join(5);provider.close()
    provider=FixtureProvider(malformed=True)
    try:
        worker=GenerationWorker(WebsiteDocument().data,'Create',dict(MODEL_DEFAULTS,endpoint=provider.endpoint,review=False),'SYNTHETIC')
        errors=[];worker.problem.connect(lambda m,d:errors.append(m));worker.run()
        assert errors and len(provider.requests)==4
    finally:provider.close()


@pytest.mark.skipif(os.name!='nt',reason='Windows DPAPI')
def test_key_encryption_and_uploaded_assets(tmp_path,monkeypatch):
    monkeypatch.delenv('QWEN_API_KEY',raising=False)
    vault=KeyVault(tmp_path);vault.save('SECRET-SYNTHETIC-KEY');assert vault.get()=='SECRET-SYNTHETIC-KEY'
    assert b'SECRET' not in vault.path.read_bytes()
    server=PreviewServer(tmp_path)
    try:
        with httpx.Client(trust_env=False) as client:
            assert client.get(server.url('.private/qwen.key')).status_code==403
            assert client.head(server.url('.private/qwen.key')).status_code==403
    finally:server.close()
    document=WebsiteDocument();document.data['assets']['photo']={'name':'photo.png','width':1,'height':1,'data':'data:image/png;base64,AA=='}
    result=document.apply({'action':'upsert_block','id':'hero','html':'<section><img alt="Original" src="asset:photo"></section>'})
    assert 'data:image/png' in result['html']
    with pytest.raises(ValueError):document.apply({'action':'upsert_block','id':'bad','html':'<img src="asset:missing">'})


def test_plan_only_responses_are_redirected_to_actual_construction():
    worker = GenerationWorker(WebsiteDocument().data, 'Create a complete website', dict(MODEL_DEFAULTS, review=False), 'SYNTHETIC')
    requests = []
    def stream(messages):
        requests.append(messages)
        if len(requests) <= 2:
            yield json.dumps({'action': 'plan', 'steps': ['Build the website with complete responsive interactions. ' * 4]})
        else:
            assert 'upsert_block operation NOW' in messages[-1]['content']
            yield json.dumps({'action': 'upsert_block', 'id': 'hero', 'html': '<section><h1>Built</h1></section>'})
            yield json.dumps({'action': 'finish', 'summary': 'Built the requested page.'})
    worker.client.stream = stream
    completed = []; errors = []
    worker.ready.connect(lambda d,s: completed.append(d))
    worker.problem.connect(lambda m,d: errors.append(m))
    worker.audit_requested.connect(lambda: worker.audit_event.set())
    worker.run()
    assert completed and not errors and len(requests) == 3
    assert completed[0]['blocks'][0]['id'] == 'hero'


def test_public_source_does_not_load_a_private_bootstrap(tmp_path, monkeypatch):
    import sys
    import types
    monkeypatch.delenv('QWEN_API_KEY', raising=False)
    private = types.ModuleType('app.local_credentials')
    private.ENCRYPTED_API_KEY = 'PRIVATE-BOOTSTRAP-MUST-NOT-BE-READ'
    monkeypatch.setitem(sys.modules, 'app.local_credentials', private)
    assert KeyVault(tmp_path).get() == ''
