import functools
import threading
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


class PreviewHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self):
        # Never expose directory listings, dotfiles, or paths outside the root.
        requested = unquote(urlsplit(self.path).path)
        root = Path(self.directory).resolve()
        target = Path(self.translate_path(self.path)).resolve()
        outside = not target.is_relative_to(root)
        hidden_target = not outside and any(p.startswith('.') for p in target.relative_to(root).parts)
        if ".." in requested.split("/") or any(p.startswith(".") for p in requested.split("/") if p) or outside or hidden_target:
            self.send_error(403)
            return
        if target.is_dir() and not (target / "index.html").is_file():
            self.send_error(403)
            return
        if target.is_file():
            try:
                with target.open('rb') as source:
                    size=target.stat().st_size;start,end=0,size-1
                    header=self.headers.get('Range')
                    if header and not self.headers.get('If-Range'):
                        match=re.fullmatch(r'bytes=(\d*)-(\d*)',header.strip())
                        if not match or not any(match.groups()):
                            self.send_error(400,'Only one byte range is supported');return
                        left,right=match.groups()
                        if left:start=int(left);end=min(int(right),end) if right else end
                        else:start=max(0,size-int(right))
                        if start>=size or end<start:
                            self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
                        self.send_response(206);self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                    else:self.send_response(200)
                    self.send_header('Content-Type',{'mp4':'video/mp4','webm':'video/webm'}.get(target.suffix.lstrip('.'),self.guess_type(str(target))))
                    self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(max(0,end-start+1)));self.end_headers()
                    if self.command=='HEAD':return
                    source.seek(start);remaining=end-start+1
                    while remaining>0:
                        chunk=source.read(min(65536,remaining))
                        if not chunk:break
                        self.wfile.write(chunk);remaining-=len(chunk)
            except (BrokenPipeError,ConnectionResetError):pass
            return
        super().do_GET()

    def do_HEAD(self):
        self.do_GET()


class PreviewServer:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(PreviewHandler, directory=str(self.root)))
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def url(self, relative):
        from urllib.parse import quote
        return self.origin + "/" + quote(str(relative).replace("\\", "/"), safe="/")

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
