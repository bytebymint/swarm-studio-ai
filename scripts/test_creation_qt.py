"""Real native Create workflow against a local streaming model simulator."""
import json
import os
from pathlib import Path
import sys
import time
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from scripts.creation_fixture import FixtureProvider

QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
from app.desktop import MainWindow

root=Path('test-results/creation-native')/uuid.uuid4().hex[:10];root=root.resolve();root.mkdir(parents=True)
previous_key=os.environ.get('QWEN_API_KEY');os.environ['QWEN_API_KEY']='SYNTHETIC-LOCAL-MODEL-KEY'
provider=FixtureProvider(pause_first=True)
window=MainWindow(root/'data');window.showMaximized()


def wait(predicate, timeout=40):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError('Creation native check timed out: '+(window.creator.activity.text() if window.creator else 'launcher'))


def js(expression):
    result=[];window.creator.view.page().runJavaScript(expression,result.append)
    wait(lambda:bool(result),10);return result[0]


def drain():
    js('for(let i=0;i<300&&!Studio.finished;i++)Studio.tick(1/60);Studio.draw();Studio.report();true')


def settle():
    end=time.monotonic()+70
    while time.monotonic()<end:
        app.processEvents()
        if window.creator.browser_ready:drain()
        c=window.creator
        if c.worker and not c.worker.isRunning() and not c.visual_busy and not c.queue:return
        time.sleep(.05)
    raise AssertionError('Creation did not settle: '+window.creator.activity.text())


try:
    assert window.workspaces.currentWidget() is window.launcher
    assert window.rebuild_choice.isVisible() and window.create_choice.isVisible()
    window.grab().save(str(root/'startup.png'))
    QTest.mouseClick(window.create_choice,Qt.MouseButton.LeftButton)
    c=window.creator;wait(lambda:c.browser_ready)
    c.config.update(endpoint=provider.endpoint,model='local-fixture',review=True)
    c.prompt.setPlainText('Create an original responsive studio website with a hero, features, footer and working button.')
    QTest.mouseClick(c.send,Qt.MouseButton.LeftButton)
    wait(lambda:provider.hero_sent.is_set())
    wait(lambda:js('Boolean(Creator.block("hero"))'))
    assert c.worker.isRunning(),'The preview must update before the streaming response finishes'
    assert js('Studio.crew.constructor===WorkingCrew&&Studio.choreography.constructor===TaskChoreography')
    drain();window.grab().save(str(root/'live-shared-swarm.png'))
    provider.release.set();settle()
    assert c.project['document']['title']=='Fieldwork Studio'
    assert c.export.isEnabled() and c.undo.isEnabled()
    assert js('Studio.finished&&Studio.failed===0')
    assert provider.requests[0]['stream'] is True
    # Pick an actual element through the preview -> native bridge.
    c.select_button.setChecked(True)
    js('Creator.block("hero").querySelector("h1").click();true')
    wait(lambda:c.target is not None)
    assert c.target['block']=='hero' and c.target['tag']=='h1'
    original_features=next(b for b in c.project['document']['blocks'] if b['id']=='features').copy()
    c.prompt.setPlainText('Change the hero headline, add pricing before features and remove the footer.')
    c.submit();settle()
    assert [b['id'] for b in c.project['document']['blocks']]==['header','hero','pricing','features']
    assert next(b for b in c.project['document']['blocks'] if b['id']=='features')==original_features
    assert js('!Creator.block("footer")&&Boolean(Creator.block("pricing"))')
    context=next(json.loads(request['messages'][1]['content']) for request in provider.requests if 'Change the hero' in request['messages'][1]['content'])
    assert context['selected_element']['block']=='hero'
    window.grab().save(str(root/'edited-website.png'))
    c.restore(-1);wait(lambda:c.browser_ready)
    assert any(b['id']=='footer' for b in c.project['document']['blocks'])
    assert js('Boolean(Creator.block("footer"))')
    c.restore(1);wait(lambda:c.browser_ready)
    assert not any(b['id']=='footer' for b in c.project['document']['blocks'])
    c.devices.setCurrentIndex(2);app.processEvents();wait(lambda:c.view.width()<=390)
    window.grab().save(str(root/'mobile-preview.png'))
    c.devices.setCurrentIndex(0);c.preview_mode.setCurrentIndex(1);app.processEvents()
    assert js('document.querySelector("#interactive").getAttribute("sandbox")')=='allow-scripts'
    c.preview_mode.setCurrentIndex(0)
    export=root/'created-website.zip';c.store.export(c.project,export)
    with zipfile.ZipFile(export) as archive:
        assert archive.testzip() is None
        contents=archive.read('index.html').decode('utf-8')
        assert 'Make room for something better.' in contents
        assert 'SYNTHETIC' not in contents and 'recent_instructions' not in contents
    reopened=c.store.load(c.project['id']);assert reopened['document']==c.project['document']
    (root/'final-document.json').write_text(json.dumps(reopened['document']),encoding='utf-8')
    report={'native_startup_choices':True,'incremental_before_stream_finish':True,'shared_rebuild_renderer':True,
            'selection_context':True,'targeted_edit_add_remove':True,'unmodified_sections_preserved':True,
            'undo_redo':True,'mobile_viewport':True,'isolated_interactive_preview':True,'offline_zip_integrity':True,
            'project_reopen':True,'requests':len(provider.requests),'model':'local simulator; no real Qwen request', 'evidence':str(root)}
    (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    Path('test-results/creation-native/latest.json').write_text(json.dumps(str(root)),encoding='utf-8')
    print('PASS native creation',json.dumps(report),flush=True)
finally:
    provider.release.set()
    if window.creator and window.creator.worker and window.creator.worker.isRunning():
        window.creator.worker.cancel()
        wait(lambda:not window.creator.worker.isRunning(),35)
    window.close();app.processEvents();provider.close()
    if previous_key is None:os.environ.pop('QWEN_API_KEY',None)
    else:os.environ['QWEN_API_KEY']=previous_key
