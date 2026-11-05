"""Native source-inspection dialog for a captured YouTube hero."""
import json
import shutil
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication,QTimer,Qt
from PySide6.QtWidgets import QApplication,QTreeWidget,QLineEdit
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
from app.desktop import MainWindow
root=Path('test-results/embedded-video/native').resolve()
project=root/'projects/hero'
shutil.copytree('test-results/embedded-video/fixture',project,dirs_exist_ok=True)
window=MainWindow(root);window.showMaximized()
def wait(predicate):
    end=time.monotonic()+30
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError('Native player did not load')
try:
    wait(lambda:window.player_ready)
    window.project=project;window.metadata=json.loads((project/'metadata/project.json').read_text('utf-8'));window.blueprint=json.loads((project/'metadata/blueprint.json').read_text('utf-8'))
    window.load_player();wait(lambda:window.engine_ready)
    observed=[]
    def inspect():
        dialog=app.activeModalWidget();tree=dialog.findChild(QTreeWidget);item=tree.topLevelItem(0)
        observed.append([item.text(i) for i in range(5)])
        dialog.grab().save(str(root/'video-sources.png'));dialog.close()
    QTimer.singleShot(150,inspect);window.show_video_sources()
    assert observed and observed[0][1:4]==['third-party','youtube','poster-only'],observed
    assert observed[0][4]=='https://www.youtube.com/embed/fixture0001',observed
    print('PASS native YouTube source dialog',json.dumps(observed),flush=True)
finally:window.close();app.processEvents()
