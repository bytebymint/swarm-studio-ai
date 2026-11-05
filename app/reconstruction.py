import asyncio
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.assets import AssetCollector, URL_PATTERN
from app.blueprint import build_blueprint
from app.projects import write_json
from app.urls import resource_url

SECURITY_POLICY = "default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; media-src 'self' data:; script-src 'self'; form-action 'none'; frame-src 'none'; connect-src 'none'; base-uri 'none'"


def reconstruct(capture, root, settings, cancel=None, progress=None):
    root = Path(root)
    cancel = cancel or threading.Event()
    root.mkdir(parents=True, exist_ok=True)
    collector = AssetCollector(root, settings, cancel, progress)
    async def bounded_collect():
        try:
            return await asyncio.wait_for(collector.collect(capture), timeout=max(10, settings.get('timeout', 25) + 20))
        except TimeoutError:
            collector.warnings.append('Asset collection reached its total time limit. Some local resources may be missing.')
            def local_css(text, base):
                return URL_PATTERN.sub(lambda m: 'url("' + (m.group(2) if m.group(2).startswith(('data:', '#')) else collector.mapping.get(urljoin(base, m.group(2)), '')) + '")', text)
            return '\n'.join(local_css(s['text'], s['base']) for s in capture.get('sheets', [])), local_css(capture.get('computedCSS', ''), capture['url'])
    css, computed = asyncio.run(bounded_collect())
    for url, relative in list(collector.mapping.items()):
        if not (root / relative).is_file():
            del collector.mapping[url]
            collector.warnings.append('An interrupted asset was omitted from the local resource map.')
    if cancel.is_set():
        raise InterruptedError("Capture cancelled")
    soup = BeautifulSoup(capture['html'], 'lxml')
    for tag in soup.select('script, iframe, object, embed, base, link, meta[http-equiv], input[type=hidden]'):
        tag.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith('on') or attr.lower() in {'value', 'checked', 'selected', 'srcdoc', 'nonce', 'integrity', 'srcset', 'action', 'formaction', 'ping', 'autofocus', 'contenteditable'} or attr.lower().startswith('data-') and attr != 'data-sw-id':
                del tag[attr]
        if tag.name in {'input', 'textarea', 'select'}:
            tag.attrs.pop('name', None)
            if tag.name == 'textarea':
                tag.clear()
        if tag.name == 'input':
            tag['autocomplete'] = 'off'
        for attr in ['src', 'poster', 'href', 'xlink:href']:
            if attr not in tag.attrs:
                continue
            raw = str(tag[attr])
            if raw.startswith('#') or raw.startswith('data:image/'):
                continue
            absolute = urljoin(capture['url'], raw)
            if tag.name == 'a':
                if resource_url(absolute):
                    # Single-page capture preserves external links with explicit navigation.
                    tag[attr] = absolute
                    tag['rel'] = 'noreferrer noopener'
                    tag['target'] = '_blank'
                else:
                    tag.attrs.pop(attr, None)
            elif absolute.split('#')[0] in collector.mapping:
                tag[attr] = collector.mapping[absolute.split('#')[0]]
            else:
                tag.attrs.pop(attr, None)
        if tag.get('style'):
            # Inline styles must undergo exactly the same local URL rewrite.
            def inline_reference(match):
                ref = match.group(2)
                local = ref if ref.startswith(('data:', '#')) else collector.mapping.get(urljoin(capture['url'], ref), '')
                return 'url("' + local + '")'
            tag['style'] = URL_PATTERN.sub(inline_reference, tag['style'])
    # Keep source rules ahead of computed fallback. The export never loads source scripts.
    (root / 'styles').mkdir(exist_ok=True)
    def stylesheet_reference(match):
        ref = match.group(2)
        # This CSS lives one directory below index.html. Inline style URLs above
        # remain relative to the HTML document instead.
        return 'url("' + ('../' + ref if ref.startswith('assets/') else ref) + '")'
    stylesheet = URL_PATTERN.sub(stylesheet_reference, css + '\n' + computed)
    (root / 'styles/reconstructed.css').write_text(stylesheet, 'utf-8')
    policy = soup.new_tag('meta', attrs={'http-equiv': 'Content-Security-Policy', 'content': SECURITY_POLICY})
    soup.head.insert(0, policy)
    soup.head.insert(0, soup.new_tag('meta', charset='utf-8'))
    link = soup.new_tag('link', rel='stylesheet', href='styles/reconstructed.css')
    for url in capture.get('stylesheets', []):
        if url in collector.mapping:
            soup.head.append(soup.new_tag('link', rel='stylesheet', href=collector.mapping[url]))
    soup.head.append(link)
    media_elements={e['id']:e for e in capture.get('media',[])}
    media_elements.update({e['id']:e for e in capture['elements'] if e.get('kind')=='media'})
    for element in media_elements.values():
        if element.get('kind')!='media':continue
        media=element['media'];node=soup.find(attrs={'data-sw-id':element['id']})
        if node is None:continue
        local=[collector.mapping[u.split('#')[0]] for u in media.get('sources',[]) if u.split('#')[0] in collector.mapping and collector.mapping[u.split('#')[0]].startswith('assets/media/')]
        node.clear();node.attrs.pop('src',None)
        media['sources']=local;media['currentSrc']=local[0] if local else None
        media['poster']=node.get('poster')
        media['status']='downloaded' if local else 'poster-only' if node.get('poster') else 'unsupported'
        if local:
            if len(local)==1:node['src']=local[0]
            for path in local:node.append(soup.new_tag('source',src=path,type=collector.media_info[path]['mime']))
        else:
            node.name='div';node['role']='img';node['aria-label']='Video unavailable — media not reconstructed'
            rect=element.get('rect',{})
            if rect:node['style']=node.get('style','')+f";width:{rect.get('w',0)}px;height:{rect.get('h',0)}px;max-width:100%;overflow:hidden;"
            if media['poster']:node.append(soup.new_tag('img',src=media['poster'],alt='Video poster only — video unavailable',style='width:100%;height:100%;object-fit:contain'))
            else:node.string='Video unavailable — unsupported or inaccessible media'
            collector.warnings.append(f"Video {element['id']}: {media['status']}; actual media was not reconstructed.")
    (root / 'index.html').write_text(str(soup), 'utf-8')
    for element in capture['elements']:
        node = soup.find(attrs={'data-sw-id': element['id']})
        if node is None or node.name == 'img' and not node.get('src'):
            element['validation'] = 'failed'
            collector.warnings.append(f"Element {element['id']} could not be reconstructed: missing node or image asset.")
        else:
            element['validation'] = 'captured'
    blueprint = build_blueprint(capture)
    warnings = list(dict.fromkeys(capture.get('warnings', []) + collector.warnings))
    metadata = {'schema': 1, 'name': capture.get('title') or 'Untitled capture', 'url': capture['url'],
                'created': datetime.now(timezone.utc).isoformat(), 'viewport': capture['viewport'],
                'elements': len(blueprint['elements']), 'assets': len(collector.mapping),
                'asset_bytes': collector.total, 'warnings': warnings,
                'mode': 'single-page rendered snapshot', 'scripts': 'excluded',
                'limitations': ['Source JavaScript and server behavior are excluded.', 'Form values and session state are not retained.', 'Responsive behavior depends on recovered source CSS.', 'Links to uncaptured pages open the original website.']}
    write_json(root / 'metadata/project.json', metadata)
    write_json(root / 'metadata/blueprint.json', blueprint)
    write_json(root / 'metadata/capture-report.json', {'warnings': warnings, 'assets': collector.mapping, 'media':collector.media_info, 'media_failures':collector.media_failures, 'capture_ms': capture.get('duration'), 'status': 'partial' if warnings else 'captured'})
    (root / 'README.md').write_text('# Local website reconstruction\n\nOpen index.html in a browser or serve this directory with `python -m http.server 8000`.\n\n'
        'Captured from ' + capture['url'] + '. Reproduce and share only material you have permission to use.\n\n'
        'This is a static rendered-DOM reconstruction. Source scripts, sessions, credentials, backends and form values are excluded. '
        'Native controls, anchor links and preserved CSS interactions work. Uncaptured links lead to the original site.\n\n'
        'See metadata/capture-report.json and metadata/quality-report.json for measured limitations.\n', 'utf-8')
    return metadata, blueprint


def reconstruct_collection(captures, root, settings, cancel=None, progress=None):
    """Build bounded captured pages and rewrite links only between successful local pages."""
    from posixpath import relpath
    from urllib.parse import urldefrag
    metadata, blueprint = reconstruct(captures[0], root, settings, cancel, progress)
    pages = {urldefrag(captures[0]['url'])[0]: 'index.html'}
    for index, capture in enumerate(captures[1:], 2):
        if cancel and cancel.is_set():
            raise InterruptedError('Capture cancelled')
        relative = f'pages/page-{index:03d}/index.html'
        try:
            reconstruct(capture, Path(root) / Path(relative).parent, settings, cancel, progress)
            pages[urldefrag(capture['url'])[0]] = relative
        except InterruptedError:
            raise
        except (OSError, ValueError) as exc:
            metadata['warnings'].append(f"Linked page {index} could not be saved: {type(exc).__name__}")
    for url, relative in pages.items():
        path = Path(root) / relative
        soup = BeautifulSoup(path.read_text('utf-8'), 'lxml')
        for anchor in soup.select('a[href]'):
            raw = anchor['href']
            if raw.startswith('#'):
                continue
            base, fragment = urldefrag(urljoin(url, raw))
            if base in pages:
                anchor['href'] = relpath(pages[base], str(Path(relative).parent).replace('\\', '/')) + ('#' + fragment if fragment else '')
                anchor.attrs.pop('target', None)
        path.write_text(str(soup), 'utf-8')
    metadata['pages'] = pages
    write_json(Path(root) / 'metadata/project.json', metadata)
    return metadata, blueprint
