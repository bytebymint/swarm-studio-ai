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

A comparison readiness bug was found by inspecting public-page results. Native
comparison now waits for the local document to finish loading and preparing;
the public test asserts text presence and low pixel difference, not just node IDs.

## Windows distribution

The initial executable exposed a real DLL conflict, documented in PACKAGING.md.
An unrelated Poppler ICU library was removed from the build search path. A
packaged launch then passed native-window, demo, playback-resource and frozen
runtime checks. The final release smoke report and screenshot are stored under
`test-results/packaged-final.*`; the full smoke workflow captures, animates,
compares and exports the bundled demo from the executable.

The current-user installer is provided but has not been run against the user's
Programs/Start menu folders. The executable is unsigned. Code signing, installer
deployment and validation on a clean second Windows machine remain release steps.

Raw evidence is in `test-results/desktop-results.json`,
`test-results/browser/results.json`, `test-results/public/result.json`,
`test-results/packaged-final.json` and their associated screenshots/exports.

## Cinematic recording

`scripts/test_recording.py` captures the offline demo, exercises the director at
60 fixed steps per second, repeats the plan deterministically, then encodes and
decodes a real 720p/30 MP4 with stereo audio. All 66 tasks finish. The camera
reaches 2.989× with a 3× cap, moves fewer than 5 logical pixels per 60 Hz step,
returns below 1.02× at the end, and scroll travel starts below 1.04×. The movie
contains 1,573 video frames (52.43 seconds) and 423 sound events. Audio/video
duration differs by less than 80 ms. Cancellation preserves an existing output
and leaves no partial movie. Representative decoded frames were visually checked.

`scripts/test_recording_hd.py` also encodes the full demo at 1920 × 1080 and 60 fps
at 2× build speed: 1,619 frames / 26.98 seconds, all 66 tasks complete. Decoding
verifies monotonic timestamps and the exact frame count. Evidence and both MP4s
are in `test-results/recording/`.

The rebuilt executable passed `--smoke-report test-results/recording-package.json
--smoke-recording`: native capture, animation, comparison, ZIP export and actual
H.264/AAC encoding through bundled Playwright/PyAV. The packaged movie contains
546 frames at 30 fps, 18.2 seconds, all 66 tasks and 175 sound events. No QtCore
DLL failure or stderr output occurred. The native layout test verifies the new
dialog defaults (1080p, 60 fps, 3× cap) and retains a 90.14% canvas height.
Occluded QtWebEngine views on this host throttle RAF and can retain stale widget
screenshots; native comparison RGB results vary under occlusion. The DOM geometry
checks pass, and movie export uses a separate browser compositor and fixed clock.

## Video assets upgrade

The video-specific implementation and security review are documented in
[VIDEO.md](VIDEO.md). The original silent fixtures are generated locally by
`scripts/media_fixture.py`; no downloaded third-party video fixture is required.

Executed checks:

| Check | Result |
| --- | --- |
| Existing core tests plus media/HTTP/security tests | 17 passed, including the six existing core cases and eleven media/security cases. |
| `scripts/test_browser.py` | Passed: capture, assets, source shutdown, native interactions, multi-page links and scheduler regressions. |
| `scripts/test_camera.py` | Passed: document and nested tours. |
| `scripts/test_crew.py` | Passed: worker population, choreography, text stability and legacy blueprints. |
| `scripts/test_video.py` | Passed in installed Edge: MP4/WebM, nested sources, lazy/runtime sources, open shadow roots, multiple videos, posters, unsupported fallbacks, hidden-video discovery and secret/blob exclusion. |
| Video ZIP/offline playback | Passed after the source server was stopped and the ZIP was extracted. |
| Video clock and movie pixels | Passed: repeated seeks/loops produced identical expected pixels; different times changed pixels. The encoded 720p/30 film had 119 frames and 12–13 distinct quantized color samples in the final second across fresh capture runs. |
| Video 1080p/60 export | Passed: 237 decoded frames, no media fallback warnings. |
| `scripts/test_video_qt.py` | Passed in real Windows/PySide6 Qt WebEngine: WebM decoded/played, six media jobs completed, maximized native UI retained. |
| `scripts/test_desktop.py` | Passed. |
| `scripts/test_focus_layout.py` | Passed. |
| `scripts/test_public.py` | Passed against example.com. |
| `scripts/test_site_tour.py` | Passed against the existing public-site fixture. |
| `scripts/test_recording.py` | Passed: non-video 720p/30 movie, sound, deterministic camera, cancellation and destination preservation. |
| `scripts/test_recording_hd.py` | Passed: non-video 1080p/60 output. |

Two initial checks failed and were corrected before the successful reruns: reused
fixture folders retained prior downloaded files, so media tests now create an
isolated run directory; an encoded-pixel check exposed a poster-only fallback
losing tag-based video dimensions, which shifted layout. Fallback geometry now
retains the measured box. These were real failures, not counted as passes.

Local evidence is under `test-results/video-suite/` and the run directory named
in `test-results/video/latest.json`. Unit results, media reports, native and
browser screenshots, ZIPs and both movie sizes are local generated artifacts
and are excluded from Git. Browser codecs differ by platform: the Qt media
check validates WebM, while the installed Edge check validates MP4 and WebM.
No claim of universal video, codec, stream or DRM support is made.

The Windows distribution was rebuilt successfully. Its frozen executable passed
the full `--smoke-report ... --smoke-recording` workflow: native startup, capture,
66-task non-video playback, comparison, ZIP export and H.264/AAC movie encoding.
The packaged smoke has no video source fixture; video decoding is covered by the
separate native Qt and installed Edge checks above. The proprietary `LICENSE`
was compared byte-for-byte with the pre-change revision and remains unchanged.

## YouTube hero detection follow-up

A real browser inspection of an embedded hero found no HTML5 video element and
identified a YouTube iframe. The previous capture reported
only the generic isolated-frame placeholder. The follow-up identifies the
provider and third-party hosting, extracts clean embed/watch links, downloads
the public thumbnail and retains the hero's measured placement. It explicitly
reports `poster-only`; no YouTube media stream was downloaded or reconstructed.

`scripts/test_embedded_video.py` passed known-embed detection, canonical-link
privacy, thumbnail download, media task assignment, sandbox-preserving export
and hero sizing. The committed regression uses a synthetic video identifier and
an original local thumbnail fixture, with no customer-specific URL or media.
`scripts/test_embedded_video_qt.py` passed the
real native source-inspection dialog, including provider, hosting category,
poster-only status and copyable embed URL. Existing core/media tests (17) and
the independent browser regression passed. Test fixtures use a borderless hero
iframe matching the live site's presentation; an initial fixture with the
browser's default iframe border produced a sizing assertion and was corrected.
