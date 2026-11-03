# Architecture

Native PySide6 widgets form the shell, panels, toolbar and timeline. Two Chromium
views render the source and local output. Only the trusted playback page receives
a WebChannel, whose single slot accepts bounded event JSON and exposes no file,
shell or navigation operation. Capture runs in an isolated JavaScript world.
An off-the-record browser profile never persists cookies or storage.

Capture creates two independent outputs: semantic sanitized HTML/CSS and a stable
ID blueprint. Original CSS rules preserve layout and hover behavior; computed
styles provide a per-node fallback when a stylesheet is inaccessible. Browser
scripts, inline handlers, form values, frames and session storage are excluded.
An asynchronous bounded asset collector rewrites CSS URLs recursively. Build and
export execute on QThreads. Project metadata lives in SQLite; project artifacts
are portable directories, served by a GET/HEAD-only loopback server.

