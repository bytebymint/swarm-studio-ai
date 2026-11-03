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

The independently written JavaScript engine builds local HTML with real captured
nodes. `crew.js` keeps a small roster and assigns only the workers required by
visible tasks. `choreography.js` drives both cursor positions and drawing progress
from the same minimum-jerk trajectories. Inactive cursors fade instead of circling
the page. The task DAG distinguishes parent frame readiness from final completion:
content can start after its parent frame is placed; duplicates still wait for a
completed master. These milestones emit real handoff events.

Typing leaves the full original text in the DOM. Custom Highlights conceal only
the untyped ranges, and DOM Range measures the insertion caret, preserving line
breaks and glyph spacing. Gradient text uses an SVG mask built from those same
range rectangles. Temporary masks and highlight registries are removed on stop,
completion and replay. Simulation time drives tasks, cursor paths, effects and
camera together, so pause, speed and stepping remain coherent.

Validation compares source and reconstructed widget screenshots at the same
viewport and zoom, normalizes device pixel dimensions, reports mean absolute
RGB difference and writes a heatmap. A separate DOM check measures bounding boxes,
missing images and text presence. Pixel metrics do not prove backend fidelity.

Design: graphite panels reduce distraction around arbitrary websites. Blue marks
the main reconstruction action. Agent colors are identities, not status claims.
Segoe UI follows Windows typography; compact measured panels give the actual
website most of the window. Motion is confined to construction and its controls.
The cursor shape and transient dimension labels repeat the design-tool motif.

