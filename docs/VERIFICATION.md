# Verification

## Adaptive crew and precise work animation, 5 November 2026

The default roster is now eight instead of 24. Existing settings above 12 migrate
to eight. The visible working limit also adapts to viewport area: the tested
1280-pixel canvas allowed five simultaneous jobs. Idle cursors no longer circle
the page; they fade at their release point, with at most two brief handoffs.

`scripts/test_crew.py` exercised drawing, actual-range typing, image placement,
component duplication, pen strokes and verification on a captured page. It checked:

- Approximately 90% of visible cursor time had an assigned task.
- Five concurrent jobs, no more than two retiring cursors, and no idle cloud.
- Zero lag between active cursor pose and the construction trajectory.
- Zero text mutation and zero text-width drift during typing.
- Real frame-readiness and completion events before dependent assignments.
- Progressive gradient-text paint and removal of all temporary masks/highlights.

The recorded fixture completed 67 tasks with no failures, published 23 frame
milestones, and performed dozens of dependency-driven handoffs. The largest sampled
cursor step at 1× was approximately 34.4 pixels per 1/60 simulation second.
These are fixture measurements, not a general frame-rate or quality guarantee.
Evidence and screenshots are in `test-results/crew/`.
The same test also replayed an older blueprint without explicit frame milestones.

The native Qt test also confirmed Custom Highlight support, the smaller crew,
the 90% canvas, tour, replay controls and zero demo screenshot difference.
Core tests now include crew-settings migration and parent-frame handoff ordering.
The rebuilt Windows executable passed capture, all 66 demo tasks, comparison and
ZIP export with exit code 0; the demo difference remained 0 / 255. Evidence is
in `test-results/crew-package.json` and its associated screenshot and ZIP.

## Canvas-first layout and cinematic Auto Tour update

`scripts/test_focus_layout.py` verified a maximized window with **90.14%** of its
client height occupied by the website canvas and only a compact bottom dock.
The actual browser viewport was 1280 × 585 CSS pixels, with no default zoom-down.
Side panels, permanent top bars and timeline were absent from the main view.
Diagnostics and timeline toggles, fullscreen return, playback and comparison were
checked. The demo screenshot comparison remained 0 mean RGB difference.
Window mode also fills the canvas when replaying an older capture with a different
height; comparison temporarily restores the saved capture viewport for measurement.

`scripts/test_camera.py` verified real animation-frame movement, pause and manual
control on long-document and inner-scrolling fixtures. Both completed six smooth
shots, reached their scrolling limits and assigned no offscreen construction.
The largest per-simulation-frame movement was 10 pixels at 1× speed.

`scripts/test_site_tour.py` captured the public Huzera page used in the reported
issue: **224 / 224 tasks**, **0 failures**, **12 camera shots**, ending at its
5514-pixel scroll limit. Evidence is in `test-results/site-tour/results.json`.

The old algorithm allowed offscreen assignment and counted the always-visible
final body-validation task as pending visible work. As a result, all work could
finish without the camera moving. Visible-only assignment and a separate camera
controller now sequence eased shots through unfinished sections, including nested
scroll panes, and finish the tour before final validation.

Native layout screenshots and results are in `test-results/focus-layout/`, and
camera traces are in `test-results/camera/results.json`. Unattended native playback
tests disable Chromium's occluded-window throttling for their test process.
The rebuilt executable passed the complete capture / 66-task playback / comparison /
ZIP export smoke test and exited with code 0. Its report and screenshot are in
`test-results/canvas-update-package.json` and `test-results/canvas-update-package.png`.

Verified on this Windows 11 machine on 4 November 2026, with CPython 3.12.14,
PySide6 6.12.0, Qt WebEngine 6.12.0.140 and PyInstaller 6.22.3.
`requirements-lock.txt` records the complete tested environment.

## Core tests

`python -m pytest -q --basetemp=test-results/unit-release`: **5 passed**.
Tests cover URL normalization and secret/scheme rejection, dependency ordering,
allocation, cycles, missing dependencies, failure propagation, cancellation,
empty graphs, project save/reopen/corruption handling, settings persistence,
known pixel differences, asset/CSS/font rewriting, input redaction, source-script
removal, loopback serving and reconstruction cancellation.
The final resource-path regression run (`unit-css-final`) also passed all five tests.

## Native desktop integration

`python scripts/test_desktop.py`: **15 workflow checks passed**. A real Qt window
and Chromium views exercised demo navigation, DOM capture, local image saving,
task metadata, pause, resume, forward/backward stepping, 5× completion, replay,
independent clone DOM, comparison, export, SQLite reopening, settings persistence,
the supplied reference demo, two-page bounded crawl, local link rewriting,
settings dialog, mobile viewport, zoom, presentation and cancellation/errors.

The supplied reference demo was served from its original directory. It was not
bundled into the new application. Its inner scroll container, floats, canvas image
fallback, input redaction and iframe diagnostic passed capture and playback.

## Independent browser verification

`python scripts/test_browser.py`: **6 workflow checks passed** in installed Chrome.
An inaccessible cross-origin stylesheet exercised computed fallback and local CSS
recovery. Two pages were captured, then both original HTTP servers were stopped.
The exported HTML still rendered its image, selectable text, native accordion and
local navigation. Event assertions verified that every task dependency completed
before child assignment. Replay, cleanup, zero tasks and failed-node diagnostics
were checked. Both supplied MP4 recordings were inspected locally.
Every generated stylesheet URL is resolved relative to that stylesheet's actual
directory and checked for an existing local file, including imported CSS and fonts.

## Public URL

`python scripts/test_public.py`: **passed** against https://example.com/ . The
saved page contained actual source text, nine visual nodes plus final validation,
no missing captured elements, no broken images and selectable text. At the tested
1280 × 800 CSS viewport and fit screenshot scale, mean absolute RGB difference
was approximately **0.003 / 255**. The bundled demo measured **0 / 255** on the
same machine. These are narrow fixture measurements, not a universal fidelity claim.

