"""Exercise a copied, single-file Windows build without development dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
import zipfile

import av


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('This native executable check requires Windows.')
    source = args.exe.resolve(strict=True)
    root = Path(__file__).resolve().parent.parent
    run = root / 'test-results' / ('portable-' + uuid.uuid4().hex[:12])
    isolated = run / 'distribution'
    isolated.mkdir(parents=True)
    temporary = run / 'temp'
    temporary.mkdir()
    executable = isolated / source.name
    shutil.copyfile(source, executable)
    report = run / 'smoke.json'
    env = os.environ.copy()
    for name in list(env):
        if name.upper().startswith(('PYTHON', 'QT', 'QML', 'PLAYWRIGHT', 'SWARM_STUDIO')):
            env.pop(name)
    windows = Path(env.get('SystemRoot', 'C:/Windows'))
    env.update(PATH=os.pathsep.join(map(str, (windows / 'System32', windows))),
               TEMP=str(temporary), TMP=str(temporary),
               SWARM_STUDIO_RECORDING_BROWSER='bundled',
               QTWEBENGINE_CHROMIUM_FLAGS='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows')
    started = time.monotonic()
    with (run / 'process.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(
            [str(executable), '--data-dir', str(run / 'data'), '--smoke-report', str(report), '--smoke-recording'],
            cwd=isolated, env=env, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code = process.wait(timeout=420)
        except subprocess.TimeoutExpired:
            # Terminate only this test's process tree, including Qt/browser children.
            subprocess.run([str(windows / 'System32/taskkill.exe'), '/PID', str(process.pid), '/T', '/F'],
                           stdout=log, stderr=subprocess.STDOUT, check=False,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            raise AssertionError(f'Portable smoke timed out; evidence: {run}')
    assert code == 0, f'Portable process exited {code}; evidence: {run}'
    assert report.is_file(), f'No smoke report; evidence: {run}'
    result = json.loads(report.read_text('utf-8'))
    for key in ('native_window', 'demo_loaded', 'player_loaded', 'frozen', 'bundled_browser', 'workflow_complete', 'export_exists'):
        assert result.get(key) is True, f'{key} failed: {result}'
    assert not result.get('recording_error'), result
    assert result['tasks'] > 0, result
    bundle = Path(result['bundle_root']).resolve()
    assert bundle.is_relative_to(temporary.resolve()), f'Unexpected extraction location: {bundle}'
    movie = result['recording']
    assert movie['completed'] == movie['total'] > 0, movie
    assert (movie['width'], movie['height'], movie['fps']) == (1280, 720, 30), movie
    assert movie['frames'] > 30 and movie['shots'] and movie['audio_events'] > 0, movie
    with av.open(str(report.with_suffix('.mp4'))) as container:
        assert len(container.streams.video) == 1 and len(container.streams.audio) == 1
        stream = container.streams.video[0]
        assert (stream.width, stream.height) == (1280, 720)
        assert sum(1 for _ in container.decode(video=0)) == movie['frames']
    with zipfile.ZipFile(report.with_suffix('.zip')) as archive:
        assert archive.testzip() is None
        assert any(name.endswith('index.html') for name in archive.namelist())
    assert [path.name for path in isolated.iterdir()] == [source.name], 'Unexpected distribution sidecar files'
    assert not bundle.exists(), f'Temporary runtime was not cleaned up: {bundle}'
    with executable.open('rb') as copied:
        checksum = hashlib.file_digest(copied, 'sha256').hexdigest()
    summary = dict(executable=str(source), sha256=checksum,
                   seconds=round(time.monotonic() - started, 1), evidence=str(run),
                   tasks=result['tasks'], movie_frames=movie['frames'], bundled_browser=True,
                   isolated_distribution=True, temporary_runtime_cleaned=True)
    (run / 'verification.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
