"""Real Windows Qt WebEngine media playback and existing native shell integration."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication,Qt
from PySide6.QtWidgets import QApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
from app.desktop import MainWindow
root=Path(json.loads(Path('test-results/video/latest.json').read_text('utf-8')))
window=MainWindow(root);window.showMaximized()
def wait(predicate,seconds=40):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError('Native media check timed out')
def js(code):
    values=[];window.player.page().runJavaScript(code,values.append);wait(lambda:bool(values),10);return values[0]
try:
    wait(lambda:window.player_ready)
    window.project=root/'project'
    window.metadata=json.loads((window.project/'metadata/project.json').read_text('utf-8'))
    window.blueprint=json.loads((window.project/'metadata/blueprint.json').read_text('utf-8'))
    window.load_player();wait(lambda:window.engine_ready)
    js('Studio.pause(true);for(let i=0;i<10000&&!Studio.finished;i++)Studio.tick(1/60);Studio.draw();')
    assert js('Studio.finished&&Studio.failed===0')
    js('Studio.showClone();window.nativeVideo=Studio.media.items.find(i=>i.v.currentSrc.includes("webm")).v;nativeVideo.muted=true;nativeVideo.play();')
    wait(lambda:js('nativeVideo.readyState>=2&&nativeVideo.currentTime>0'))
    result={'native_qt':True,'webm_decoded':True,'media_tasks':js('Studio.history.filter(h=>Studio.byId.get(h.task).operation==="place_media").length'),'maximized':window.isMaximized()}
    assert result['media_tasks']==6
    window.grab().save(str(root/'native-video.png'))
    (root/'qt-report.json').write_text(json.dumps(result,indent=2),'utf-8')
    print('PASS NATIVE VIDEO',json.dumps(result),flush=True)
finally:window.close();app.processEvents()
