"""Hidden, local-simulator-only packaged Create verification."""
import copy
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

from PySide6.QtCore import QTimer


def run_creation_smoke(window, report):
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    state={'stage':'chooser','chooser':window.workspaces.currentWidget() is window.launcher}
    timer=QTimer(window);timer.setInterval(250);started=time.monotonic()
    endpoint=os.environ.get('SWARM_STUDIO_TEST_MODEL_ENDPOINT','')
    if urlsplit(endpoint).hostname not in {'127.0.0.1','localhost','::1'} or os.environ.get('QWEN_API_KEY')!='SWARM-STUDIO-LOCAL-TEST':
        report.write_text(json.dumps({'error':'Creation smoke requires the explicitly configured local model simulator.'}),encoding='utf-8')
        QTimer.singleShot(0,window.close);return

    def finish(error=None):
        timer.stop();c=window.creator
        result={'frozen':bool(getattr(sys,'frozen',False)),'native_window':window.isVisible(),
                'startup_choices':state['chooser'],'stage':state['stage'],'error':error,
                'fixed_step_smoke':True,'seconds':round(time.monotonic()-started,1),
                'shared_renderer':state.get('shared_renderer',False),'created':state.get('created',False),
                'edited':state.get('edited',False),'undo_redo':state.get('undo_redo',False),
                'export_exists':report.with_suffix('.zip').is_file(),
                'model':'local simulator; no real provider request','bundle_root':str(getattr(sys,'_MEIPASS',''))}
        report.write_text(json.dumps(result,indent=2),encoding='utf-8');window.grab().save(str(report.with_suffix('.png')))
        if c and c.worker and c.worker.isRunning():c.worker.cancel()
        window.close()

    def step():
        try:
            if time.monotonic()-started>150:raise RuntimeError('The packaged Create test exceeded its time budget.')
            if state['stage']=='chooser':
                window.grab().save(str(report.with_name(report.stem+'-startup.png')))
                window.select_workspace('create');state['stage']='ready';return
            c=window.creator
            if c.browser_ready:
                c.view.page().runJavaScript('Studio.externalClock=true;for(let i=0;i<180&&!Studio.finished;i++)Studio.tick(1/60);Studio.draw();Studio.report();')
            if state['stage']=='ready' and c.browser_ready:
                c.config.update(endpoint=endpoint,model='local-fixture',review=True)
                c.prompt.setPlainText('Create an original responsive studio website with a hero, features and footer.');c.submit();state['stage']='create'
            elif state['stage']=='create' and c.worker and not c.worker.isRunning() and not c.visual_busy:
                if not c.project['document']['blocks'] or c.project['history'][-1]['label'].startswith('Partial'):raise RuntimeError('Creation did not complete: '+c.project['chat'][-1]['text'])
                state['created']=True;state['first_document']=copy.deepcopy(c.project['document'])
                c.view.page().runJavaScript('Studio.crew instanceof WorkingCrew&&Studio.choreography instanceof TaskChoreography',lambda value:state.update(shared_renderer=bool(value)))
                c.prompt.setPlainText('Change the hero headline, add pricing before features and remove the footer.');c.submit();state['stage']='edit'
            elif state['stage']=='edit' and c.worker and not c.worker.isRunning() and not c.visual_busy:
                ids=[b['id'] for b in c.project['document']['blocks']]
                if 'pricing' not in ids or 'footer' in ids:raise RuntimeError('The follow-up edit was not applied.')
                state['edited']=True;state['final_document']=copy.deepcopy(c.project['document']);c.restore(-1);state['stage']='undo'
            elif state['stage']=='undo' and c.browser_ready:
                if c.project['document']!=state['first_document']:raise RuntimeError('Undo did not restore the original website.')
                c.restore(1);state['stage']='redo'
            elif state['stage']=='redo' and c.browser_ready:
                if c.project['document']!=state['final_document']:raise RuntimeError('Redo did not restore the edit.')
                state['undo_redo']=True;c.store.export(c.project,report.with_suffix('.zip'));state['stage']='complete';finish()
        except Exception as exc:finish(str(exc)[:500])
    timer.timeout.connect(step);timer.start()
