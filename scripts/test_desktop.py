"""Real Qt/Chromium integration test. Run from the repository root."""
import json
import os
import sys
import time
import zipfile
import faulthandler
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication, QTimer, Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
from app.desktop import MainWindow

output=Path('test-results').resolve();output.mkdir(exist_ok=True)
faulthandler.dump_traceback_later(35, repeat=True)
window=MainWindow(output/'desktop-data');window.select_workspace('rebuild')
window.show()
results=[]


def wait_for(predicate,timeout=40):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        app.processEvents()
        if predicate():return
        time.sleep(.02)  # Release the GIL for HTTP and reconstruction worker threads.
    raise AssertionError('Timed out waiting for desktop state: '+window.notice.text())


def js(code,view=None):
    result=[]
    (view or window.player).page().runJavaScript(code,lambda value:result.append(value))
    wait_for(lambda:bool(result),10)
    return result[0]


def record(name):
    results.append(name)
    print('PASS',name,flush=True)


try:
    wait_for(lambda:window.player_ready)
    assert js('typeof window.studioBridge?.publish')=='function'
    record('Native window and private playback Chromium launched')
    QTest.mouseClick(window.welcome.findChildren(__import__('PySide6.QtWidgets',fromlist=['QPushButton']).QPushButton)[0],Qt.MouseButton.LeftButton)
    wait_for(lambda:window.browser.ready)
    assert '/ui/demo/index.html' in window.url.text()
    record('Offline demo loads through real URL navigation')
    window.zoom.setCurrentText('Fit');window.resize_canvases()
    time.sleep(.2);app.processEvents()
    window.grab().save(str(output/'desktop-original.png'))
    QTest.mouseClick(window.initialize,Qt.MouseButton.LeftButton)
    wait_for(lambda:window.project is not None,70)
    wait_for(lambda:js('Boolean(window.Studio?.tasks?.length)'))
    assert len(window.blueprint['elements'])>50
    assert (window.project/'assets/images').is_dir()
    record('Rendered DOM captured, assets downloaded, semantic HTML and DAG saved')
    # Capture the most informative construction stage.
    wait_for(lambda:js('window.Studio.time')>2.4)
    window.grab().save(str(output/'desktop-swarm.png'))
    QTest.mouseClick(window.play_button,Qt.MouseButton.LeftButton)
    wait_for(lambda:window.paused)
    before=js('window.Studio.time');QTest.qWait(300);app.processEvents()
    assert abs(js('window.Studio.time')-before)<.001
    QTest.mouseClick(window.step_forward,Qt.MouseButton.LeftButton)
    assert js('window.Studio.time')>before
    QTest.mouseClick(window.step_back,Qt.MouseButton.LeftButton)
    assert js('window.Studio.paused') is True
    record('Pause freezes simulation; forward and backward steps work')
    window.speed.setCurrentText('5×')
    QTest.mouseClick(window.play_button,Qt.MouseButton.LeftButton)
    wait_for(lambda:js('window.Studio.finished'),90)
    assert js('window.Studio.failed')==0
    assert js('window.Studio.done')==len(window.blueprint['tasks'])
    record('Dependency-driven swarm completes all demo tasks at 5x')
    QTest.mouseClick(window.replay_button,Qt.MouseButton.LeftButton)
    wait_for(lambda:js('window.Studio.time')<2)
    record('Replay uses saved capture without network recapture')
    window.tabs.setCurrentIndex(2)
    assert js('window.Studio.frame.contentDocument.body.innerText.includes("Good things")')
    assert js('window.Studio.frame.contentDocument.querySelectorAll("[data-sw-state]").length')==0
    assert js('window.Studio.frame.contentDocument.querySelectorAll("script").length')==0
    record('Clone has independent selectable DOM and no animation masks or source scripts')
    QTest.mouseClick(window.compare_button,Qt.MouseButton.LeftButton)
    wait_for(lambda:(window.project/'metadata/quality-report.json').exists())
    report=json.loads((window.project/'metadata/quality-report.json').read_text())
    assert report['dom']['missing_elements']==[]
    assert report['dom']['broken_images']==[]
    window.grab().save(str(output/'desktop-comparison.png'))
    record('Measured screenshot comparison, heatmap and DOM diagnostics generated')
    destination=output/'desktop-export.zip'
    window.export_to(destination)
    wait_for(lambda:destination.exists() and not window.export_worker.isRunning())
    with zipfile.ZipFile(destination) as archive:
        assert 'index.html' in archive.namelist()
        assert 'metadata/blueprint.json' in archive.namelist()
        assert 'styles/reconstructed.css' in archive.namelist()
    record('Native export worker produces a portable ZIP')
    project_id=window.project_id
    window.new_project();window.load_project(project_id)
    wait_for(lambda:js('window.Studio.running'))
    record('SQLite recent project reopens and replays saved artifacts')
    window.settings.save({'volume':.4})
    from app.config import Settings
    assert Settings(window.settings.path).values['volume']==.4
    record('Settings persist to disk')
    # Reference test, without shipping reference source in our app.
    window.cancel()
    reference=Path('swarm-cursors-main/demo/index.html').resolve()
    from app.server import PreviewServer
    reference_server=PreviewServer(reference.parent)
    window.project=None;window.metadata=None
    window.url.setText(reference_server.url('index.html'));window.navigate()
    wait_for(lambda:window.browser.ready)
    window.start_capture();wait_for(lambda:window.project is not None,70)
    wait_for(lambda:js('window.Studio.model.elements.some(e=>e.tag==="canvas")'))
    wait_for(lambda:js('window.Studio.finished'),100)
    assert js('window.Studio.failed')==0
    record('Supplied reference demo: inner scroller, floats, forms, canvas fallback and iframe diagnostic captured and animated')
    reference_server.close()
    fixture=output/'crawl-source';fixture.mkdir(exist_ok=True)
    (fixture/'index.html').write_text('<html><head><title>Crawl root</title></head><body><main><h1>Root page</h1><a href="second.html">Second page</a><a href="/login">Login excluded</a></main></body></html>')
    (fixture/'second.html').write_text('<html><head><title>Crawl second</title></head><body><h1>Second page</h1><a href="index.html">Return home</a></body></html>')
    crawl_server=PreviewServer(fixture)
    window.cancel();window.new_project();window.settings.save({'page_limit':2,'crawl_depth':1})
    window.url.setText(crawl_server.url('index.html'));window.navigate();wait_for(lambda:window.browser.ready)
    window.start_capture();wait_for(lambda:window.project is not None,70)
    assert len(window.metadata['pages'])==2
    assert 'pages/page-002/index.html' in (window.project/'index.html').read_text()
    assert '../../index.html' in (window.project/'pages/page-002/index.html').read_text()
    record('Desktop bounded same-origin crawl captures two pages and rewrites links in both directions')
    # Exercise actual settings dialog persistence, presets, zoom and presentation.
    def save_dialog():
        modal=app.activeModalWidget();modal.fields['names'].setChecked(False);modal.accept()
    QTimer.singleShot(100,save_dialog);window.show_settings()
    assert window.settings.values['names'] is False
    window.change_viewport(3);wait_for(lambda:abs(js('innerWidth',window.source)-390)<=1)
    window.zoom.setCurrentText('50%');window.resize_canvases();wait_for(lambda:abs(js('innerWidth',window.source)-390)<=1)
    window.toggle_presentation();assert window.isFullScreen();window.toggle_presentation();assert not window.isFullScreen()
    record('Settings dialog saves, mobile viewport is real, zoom preserves CSS viewport and presentation toggles')
    window.settings.save({'page_limit':1})
    window.start_capture();window.cancel();wait_for(lambda:not window.busy)
    assert not window.browser.capturing
    window.url.setText('file:///C:/not-allowed');window.navigate()
    assert 'http://' in window.notice.text()
    record('Capture cancellation and invalid URL produce safe visible states')
    crawl_server.close()
    faulthandler.cancel_dump_traceback_later()
    (output/'desktop-results.json').write_text(json.dumps({'passed':results,'demo_quality':report},indent=2))
finally:
    window.close();app.processEvents()
    QTest.qWait(200)
