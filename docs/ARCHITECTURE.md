# Architecture

Native PySide6 widgets form the shell, startup chooser, workspaces and controls.
In Rebuild, two Chromium views render the source and local output. Only the trusted playback page receives
a WebChannel, whose single slot accepts bounded event JSON and exposes no file,
shell or navigation operation. Capture runs in an isolated JavaScript world.
An off-the-record browser profile never persists cookies or storage.

Create uses a separate memory-only browser profile and the same Studio engine,
crew, choreography and camera scripts. Streaming Qwen operations update a live
task graph; a separate opaque-origin iframe runs generated website interactions.
The native instruction chat owns model requests, user-bound encrypted credentials,
source validation, project history and exports. See [live creation](CREATION.md)
for the protocol, data boundaries, limits and verification workflow.

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

The viewport admits two to four concurrent jobs. If the roster contains a
specialist for an operation, that specialist handles it; small rosters retain a
fallback for missing skills. Each assignment records a target description from
the captured element, then runs inspection, construction and review phases.
`inspected` and `reviewed` events describe this deterministic work, not LLM
reasoning. Per-tick work rectangles share the engine's invalidated geometry cache
to avoid repeating ancestor-style/layout reads for each worker candidate.

Work-card positions, opacity and bounded travel trails update in simulation time.
Rendering a paused frame never advances them. Cards retain a fitting side until
it is obstructed and damp their position changes; they avoid each other and stay
inside the canvas. Their inverse presentation scale keeps them readable without
growing over the work at 3× zoom. Reduced motion disables trails and card easing.

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

Design: graphite panels reduce distraction around arbitrary websites. A pale mint
accent marks the main reconstruction action. Agent colors are identities, not status claims.
Segoe UI follows Windows typography; compact measured panels give the actual
website most of the window. Motion is confined to construction and its controls.
Local corner guides, task cards and brief dependency transfers make work visible
without a full-width ruler or separate inspector panels.

Recording uses a separate QThread and a fresh, headless Edge/Chrome session
through Playwright, with bundled Chromium as a fallback in the portable build.
The saved DOM keeps its captured CSS viewport.
`MoviePresentation` transforms that iframe and applies the identical matrix to
the vector overlay. `RecordingDirector` chooses active edits, retains camera
velocity through retargets, caps zoom at 3× and asks Auto Tour to wait until wide
before scrolling. A selected edit briefly slows while the camera arrives.
Decorative source animations are paused during recording.

An external fixed-step clock plans the movie and repeats the same simulation for
rendering. CDP captures each composited frame; PyAV encodes H.264 and optional
48 kHz stereo AAC, with agent sound events synthesized on the same movie clock.
No microphone, desktop pixels, user browser profile or app chrome is recorded.
The renderer permits only local saved assets and has a ten-minute movie cap.
One frame and short audio blocks are retained at a time. Output is atomically
replaced only after full task completion and an end hold; cancellation removes
the unique partial movie and preserves an existing destination.

Video assets follow the same saved-project pipeline. Capture records safe HTML5
video candidates/properties, the collector streams validated MP4/WebM files to
`assets/media/`, and reconstruction writes local video/source/poster references.
The blueprint's `place_media` operation uses the existing crew, frame dependencies
and clipping reveal. Unsupported media has explicit poster-only/unavailable states.
The local preview serves single byte ranges for seeking. During movie rendering,
`media.js` pauses source videos and awaits seeks/video-frame callbacks at each
output timestamp before compositor capture; source audio is muted. See
[video architecture and limits](VIDEO.md).
