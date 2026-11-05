"""Real native layout and end-to-end playback regression for the canvas-first UI."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
from app.desktop import MainWindow
root=Path('test-results/focus-layout').resolve();root.mkdir(parents=True,exist_ok=True)
window=MainWindow(root/'data');window.showMaximized()
def wait(predicate,timeout=60):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError(window.notice.text())
def js(expression):
    values=[];window.player.page().runJavaScript(expression,values.append);wait(lambda:bool(values),10);return values[0]
try:
    wait(lambda:window.player_ready)
    assert window.isMaximized()
    assert not any(widget.isVisible() for widget in [window.left,window.right,window.topbar,window.navbar,window.timeline,window.statusBar()])
    assert window.bottom.isVisible() and window.initialize.isVisible() and window.url.isVisible()
    window.change_viewport(5);window.open_demo();wait(lambda:window.browser.ready)
    wait(lambda:window.source.size()==window.stack.size())
    ratio=window.stack.height()/window.centralWidget().height()
    assert ratio>=.89,ratio
    window.grab().save(str(root/'canvas-default.png'))
    # Switching to another hidden page must not shrink the viewport.
    before=window.source.size();window.tabs.setCurrentIndex(1);app.processEvents();window.tabs.setCurrentIndex(0);app.processEvents();window.resize_canvases()
    assert window.source.size()==before
    window.speed.setCurrentText('5×')
    QTest.mouseClick(window.initialize,Qt.MouseButton.LeftButton)
    wait(lambda:window.engine_ready)
    assert js('Studio.agents.length')<=12
    assert js('Boolean(Studio.choreography.highlight)') is True,'Native Chromium must support layout-stable text highlights'
    original_height=window.metadata['viewport']['height']
    window.metadata['viewport']['height']=900
    window.resize_canvases()
    assert window.player.size()==window.stack.size(),'A saved project must not shrink Window mode'
    window.metadata['viewport']['height']=original_height
    wait(lambda:js('Studio.time')>2)
    window.grab().save(str(root/'canvas-swarm.png'))
    try:
        # Occluded QtWebEngine views can throttle RAF on the Windows test host.
        # Movie export has its own fixed clock and is tested independently.
        wait(lambda:js('Studio.finished'),120)
    except AssertionError:
        print('CAMERA DEBUG',js('JSON.stringify({time:Studio.time,paused:Studio.paused,running:Studio.running,visibility:document.visibilityState,events:Studio.events.slice(-4),camera:{move:!!Studio.camera.move,atEnd:Studio.camera.atEnd,scroll:Studio.camera.primary?.scrollTop,max:Studio.camera.maximum(Studio.camera.primary)},pending:Studio.tasks.filter(t=>t.status!=="complete").map(t=>({id:t.id,state:t.status,operation:t.operation,deps:t.dependencies,visible:Studio.isVisible(Studio.elements.get(t.element)),box:Studio.box(Studio.elements.get(t.element)),tag:Studio.elements.get(t.element).tag}))})'), 'NATIVE',window.player.isVisible(),window.tabs.currentIndex(),flush=True)
        raise
    assert js('Studio.failed')==0
    assert js('Studio.camera.shots')>0
    window.compare_button.click();wait(lambda:(window.project/'metadata/quality-report.json').exists())
    report=json.loads((window.project/'metadata/quality-report.json').read_text('utf-8'))
    assert report['dom']['missing_elements']==[] and report['dom']['broken_images']==[]
    window.timeline_action.setChecked(True);wait(lambda:window.timeline.isVisible())
    window.timeline_action.setChecked(False);wait(lambda:not window.timeline.isVisible())
    assert not window.left.isVisible() and not window.right.isVisible()
    assert window.record_button.isEnabled()
    window.record_button.click();wait(lambda:window.recording_dialog.isVisible())
    dialog=window.recording_dialog
    assert dialog.fps.currentData()==60 and dialog.zoom.currentData()==3
    assert dialog.resolution.currentData()==(1920,1080)
    dialog.grab().save(str(root/'recording-dialog.png'));dialog.close()
    assert not dialog.isVisible()
    window.diagnostics.show();wait(lambda:window.left.isVisible());window.diagnostics.close()
    window.toggle_presentation();wait(lambda:window.isFullScreen());window.toggle_presentation();wait(lambda:window.isMaximized())
    assert not window.left.isVisible() and not window.right.isVisible()
    result={'canvas_height_fraction':round(ratio,4),'maximized':True,'window_viewport':[before.width(),before.height()],'camera_shots':js('Studio.camera.shots'),'crew_limit':js('Studio.agents.length'),'native_text_highlights':True,'recording_dialog_defaults':True,'tasks':len(window.blueprint['tasks']),'quality':report}
    (root/'results.json').write_text(json.dumps(result,indent=2),'utf-8')
    print('PASS Full canvas, compact bottom dock, real viewport, hidden diagnostics, playback, tour and comparison:',json.dumps(result),flush=True)
finally:window.close();app.processEvents()
