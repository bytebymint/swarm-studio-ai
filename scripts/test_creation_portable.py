"""Copy only the EXE and verify native Create against an explicit local simulator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts.creation_fixture import FixtureProvider

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--exe',type=Path,required=True);args=parser.parse_args()
root=(Path('test-results/creation-portable')/uuid.uuid4().hex[:10]).resolve();folder=root/'distribution';folder.mkdir(parents=True)
source=args.exe.resolve(strict=True);target=folder/source.name;shutil.copy2(source,target)
temp=root/'temp';temp.mkdir();report=root/'report.json'
provider=FixtureProvider();env=os.environ.copy()
for name in list(env):
    if name.upper().startswith(('PYTHON','QT','QML','PLAYWRIGHT','SWARM_STUDIO','QWEN')):env.pop(name)
windows=Path(env.get('SystemRoot','C:/Windows'))
env.update(PATH=os.pathsep.join(map(str,[windows/'System32',windows])),TEMP=str(temp),TMP=str(temp),
           QWEN_API_KEY='SWARM-STUDIO-LOCAL-TEST',SWARM_STUDIO_TEST_MODEL_ENDPOINT=provider.endpoint,
           QTWEBENGINE_CHROMIUM_FLAGS='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows')
try:
    with (root/'process.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([str(target),'--data-dir',str(root/'data'),'--smoke-create-report',str(report)],cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:code=process.wait(timeout=230)
        except subprocess.TimeoutExpired:
            subprocess.run([str(windows/'System32/taskkill.exe'),'/PID',str(process.pid),'/T','/F'],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            raise AssertionError('Creation EXE check timed out: '+str(root))
    assert code==0,(code,str(root))
    result=json.loads(report.read_text('utf-8'));assert not result['error'],result
    for key in ['frozen','native_window','startup_choices','shared_renderer','created','edited','undo_redo','export_exists']:assert result[key],result
    assert result['stage']=='complete'
    bundle=Path(result['bundle_root']);assert bundle.is_relative_to(temp) and not bundle.exists(),result
    assert len(list(folder.iterdir()))==1
    with zipfile.ZipFile(report.with_suffix('.zip')) as archive:
        assert archive.testzip() is None
        html=archive.read('index.html').decode('utf-8');assert 'Make room for something better.' in html and 'SWARM-STUDIO-LOCAL-TEST' not in html
    with target.open('rb') as executable:result['sha256']=hashlib.file_digest(executable,'sha256').hexdigest()
    result['evidence']=str(root);(root/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS portable Create',json.dumps(result),flush=True)
finally:provider.close()
