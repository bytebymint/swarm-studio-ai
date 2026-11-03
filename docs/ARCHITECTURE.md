# Architecture

Native PySide6 widgets form the shell, panels, toolbar and timeline. Two Chromium
views render the source and local output. Only the trusted playback page receives
a WebChannel, whose single slot accepts bounded event JSON and exposes no file,
shell or navigation operation. Capture runs in an isolated JavaScript world.
An off-the-record browser profile never persists cookies or storage.

