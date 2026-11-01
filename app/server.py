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
