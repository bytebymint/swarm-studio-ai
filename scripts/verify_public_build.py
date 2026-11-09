"""Verify release payloads exclude credentials; write a checksum for distribution."""
import argparse
import hashlib
import re
import subprocess
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader


def verify(executable):
    archive = CArchiveReader(str(executable))
    assert not any('local_credentials' in name or '.private' in name or name.endswith('.env') for name in archive.toc), 'Private file in release'
    pyz = archive.open_embedded_archive(next(n for n in archive.toc if n.endswith('.pyz')))
    assert 'app.local_credentials' not in pyz.toc, 'Private bootstrap module in release'
    # Detect actual provider/GitHub token shapes, not prose mentioning API keys.
    secret = re.compile(rb'(?:sk-ws-[A-Za-z0-9_.-]{35,}|sk-[A-Za-z0-9_-]{35,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{35,})')
    for name in pyz.toc:
        if name.startswith('app.'):
            assert not secret.search(pyz.extract(name, raw=True) or b''), 'Credential in app module: '+name
    for name in archive.toc:
        if name.lower().endswith(('.py','.js','.json','.md','.txt','.html','.css')):
            assert not secret.search(archive.extract(name)), 'Credential in payload: '+name
    tracked = subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard']).split(b'\0')
    for raw in tracked:
        if not raw:continue
        path=Path(raw.decode('utf-8'))
        if path.suffix.lower() in {'.py','.js','.json','.md','.txt','.html','.css','.yml','.yaml','.spec'}:
            assert not secret.search(path.read_bytes()), 'Credential in publishable source: '+str(path)
    with executable.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    checksum=executable.parent/'SHA256SUMS.txt'
    checksum.write_text(digest+'  '+executable.name+'\n',encoding='ascii')
    print('PASS: no credential modules or token-shaped secrets in public source/payload; SHA256 '+digest)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,required=True)
    verify(parser.parse_args().exe.resolve(strict=True))
