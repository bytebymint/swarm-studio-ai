import functools
import threading
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
        if ".." in requested.split("/") or any(p.startswith(".") for p in requested.split("/") if p) or not target.is_relative_to(root):
            self.send_error(403)
            return
        if target.is_dir() and not (target / "index.html").is_file():
            self.send_error(403)
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
