"""Preserve installed dependency notices alongside the local Windows build."""
import importlib.metadata
import shutil
import sys
import argparse
from pathlib import Path

root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=root/'dist/SwarmStudio/Notices')
destination=parser.parse_args().output
destination.mkdir(parents=True,exist_ok=True)
names=['PySide6','PySide6_Essentials','PySide6_Addons','PySide6_WebEngine','shiboken6',
       'httpx','httpcore','anyio','h11','idna','certifi','beautifulsoup4','soupsieve',
       'lxml','Pillow','typing_extensions','pyinstaller','playwright','pyee','greenlet','av','numpy']
catalog=[]
for name in names:
    dist=importlib.metadata.distribution(name)
    license_name=dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'See bundled package notices'
    catalog.append(f'{dist.metadata["Name"]} {dist.version}\n{license_name}\n')
    for file in dist.files or []:
        parts=list(file.parts)
        filename=file.name.lower()
        if not ('licenses' in parts or filename.startswith(('license','copying','notice'))):continue
        if any(part=='..' for part in parts):continue
        source=Path(dist.locate_file(file))
        if source.is_file():
            target=destination/name/Path(*parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():shutil.copyfile(python_license,destination/'Python-LICENSE.txt')
(destination/'PACKAGES.txt').write_text('\n'.join(catalog),'utf-8')
print('Dependency notices saved:',destination)
