"""Small real-public-URL Qt capture test. Network and GUI access required."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
from app.desktop import MainWindow

root=Path('test-results/public').resolve();root.mkdir(exist_ok=True)
window=MainWindow(root/'data');window.show()
def wait(predicate,timeout=45):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        app.processEvents()
        if predicate():return
        time.sleep(.02)
    raise AssertionError(window.notice.text())
try:
    window.url.setText('https://example.com');window.navigate()
    wait(lambda:window.browser.ready)
    window.speed.setCurrentText('5×')
    window.start_capture()
    wait(lambda:window.project is not None)
    html=(window.project/'index.html').read_text('utf-8')
    assert 'Example Domain' in html
    assert window.metadata['url'].startswith('https://example.com')
    assert len(window.blueprint['tasks'])>3
    window.run_comparison()
    wait(lambda:(window.project/'metadata/quality-report.json').exists())
    report=json.loads((window.project/'metadata/quality-report.json').read_text('utf-8'))
    assert report['dom']['missing_elements']==[]
    assert report['dom']['selectable_text_characters']>50
    assert report['mean_absolute_rgb_difference']<5
    (root/'result.json').write_text(json.dumps({'url':window.metadata['url'],'tasks':len(window.blueprint['tasks']),'quality':report},indent=2))
    print('PASS Real public https://example.com capture, saved HTML and measured DOM comparison',flush=True)
finally:
    window.close();app.processEvents()
