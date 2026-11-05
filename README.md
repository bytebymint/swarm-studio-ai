<div align="center">

<img src="web/studio.svg" alt="SWARM STUDIO" width="72" />

# SWARM STUDIO

### Analyze a website. Unleash a local swarm. Watch the rebuild.

**A cinematic website reconstruction studio by Byte by Mint.**

[How it works](#how-it-works) · [Install](#installation) · [Use](#your-first-reconstruction) · [Architecture](#architecture) · [License](#license-and-permissions)

</div>

SWARM STUDIO analyzes a rendered website, maps its structure, styles and assets,
and turns that analysis into a portable local reconstruction. A coordinated crew
of AI-inspired agents brings the page together in front of you: drawing layouts,
typing text, placing images, duplicating components and handing work to one
another as the build progresses.

**No expensive AI API subscriptions. No cloud inference. No API keys.** Capture,
task planning, reconstruction, agent choreography and video rendering run on your
machine. Export the captured frontend as a website project, or turn the entire
build into an automatically directed cinematic 1080p video.

The current agent system is deterministic and rule based: these are coordinated
software personas driven by a real task graph, not LLMs independently writing
code. Internet access is needed to load online source websites and download
available assets; the bundled demo and saved local projects work offline.

<div align="center">

![Ten seconds of SWARM STUDIO agents collaborating, with smooth cinematic zoom](docs/media/swarm-studio-demo.gif)

*10 seconds from a real recording: agents at work, automatic close-ups, smooth transitions.*

</div>

The animation above is an excerpt of the recording supplied for this project.
Third-party site content and branding remain their owners' property; no
affiliation or endorsement is implied. See [third-party notices](THIRD_PARTY_NOTICES.md).

## What you can do

| Capability | What you get |
| --- | --- |
| Analyze a rendered website | DOM structure, readable CSS, computed-style fallback, visual geometry, text, fonts and available media. |
| Rebuild with a coordinated crew | Visible workers assigned real construction tasks, with dependencies and genuine task handoffs. |
| Follow the whole page | Automatic tours through document scrolling and nested scrolling containers. |
| Focus on the work | A maximized canvas taking about 90% of the window, with one compact bottom dock. |
| Control the build | Pause, replay, 0.5×–5× speed, stepping, optional sounds and a collapsible timeline. |
| Export the reconstructed website | A ZIP containing captured HTML, CSS, saved images, fonts, assets and project metadata. |
| Compare the result | Original/reconstruction screenshots, an RGB difference heatmap and DOM diagnostics. |
| Record the process | Canvas-only MP4 export at 1080p or 720p, with 60 or 30 frames per second. |
| Receive an automatically directed film | Smooth zoom up to 3× on active edits, pullbacks before section travel, and a wide finish. |
| Reopen work later | A local project library that loads saved reconstructions without recapturing the original site. |

The website export includes the elements and assets successfully captured within
the configured limits. Source JavaScript, authentication, server logic and
unsupported or inaccessible resources are outside that export. See
[limitations](#limitations) for the boundaries of a reconstruction.

## How it works

1. **Inspect the page you can see.** Chromium renders the source website. The
   capture engine walks the DOM, records visual geometry, reads accessible style
   rules, discovers bounded lazy content and identifies text, images and repeated
   components.
2. **Build a local blueprint.** Stable element IDs connect the saved document to
   a dependency graph. A container's frame can unlock its children before every
   detail finishes; a duplicated component waits for its original to complete.
3. **Save a portable reconstruction.** HTML is sanitized, CSS and resource URLs
   are rewritten, and available assets are stored in the project. Source scripts,
   inline handlers, form values and session storage are excluded.
4. **Let the crew coordinate.** Workers pick eligible, visible tasks according
   to their specialties and distance. Cursors follow the same measured paths as
   the drawing, typing and image work. Unneeded workers fade away.
5. **Explore, compare, export or record.** The result remains a local HTML/CSS
   document. Save the website as a ZIP, inspect comparison reports, or render a
   movie with automatic cinematic camera direction.

All of this runs locally. The local preview server binds to `127.0.0.1`; it is an
internal file preview, not a cloud service or a separate development server you
need to start.

## Installation

### Requirements

- **Windows 11, 64-bit.** This is the platform currently packaged and verified.
- **Python 3.12 or newer** to run from source or build an executable.
- **Microsoft Edge or Google Chrome** installed if you want cinematic recording.
  Regular capture and playback use the bundled Qt Chromium engine.
- Enough disk space for the Python/Qt environment, local website assets and
  recordings. A complete packaged distribution is several hundred megabytes.
- Internet access for initial dependency installation and online website capture.
  No AI provider account or API key is required.

### Option A — run an existing Windows build

If you have been provided a complete, authorized distribution:

1. Extract the entire `SwarmStudio` distribution folder.
2. Keep `SwarmStudio.exe`, `_internal`, `Notices` and the remaining files together.
3. Double-click **SwarmStudio.exe**. The app opens maximized.
4. Optionally run the included `install_windows.ps1` to copy it into your user
   Programs folder and create a Start menu shortcut. Administrator rights are
   not required.

This repository keeps generated builds out of Git. If you only have source
files, follow Option B. There is no public binary download implied by this guide.

### Option B — run from source with Python

1. Obtain an authorized copy of the source and extract it.
2. Open **PowerShell** in the extracted project folder.
3. Confirm that Python 3.12+ is installed:

   ```powershell
   py -3.12 --version
   ```

4. Create an isolated environment:

   ```powershell
   py -3.12 -m venv .venv
   ```

5. Install the verified dependency versions:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
   ```

   To resolve versions within the supported ranges instead, use
   `-r requirements.txt`. No environment activation is required for these commands.

6. Launch the offline demo:

   ```powershell
   .\.venv\Scripts\python.exe main.py --demo
   ```

   Or open the application normally:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

### Alternative — use uv

If you already have `uv` installed, run these commands from the project folder:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-lock.txt
.\.venv\Scripts\python.exe main.py --demo
```

Recording uses your installed Edge or Chrome; a separate Playwright browser
download is not needed. The first launch may take a moment while Chromium starts.

### Build a Windows executable

After installing the dependencies:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

The build runs the core tests and creates
`dist/SwarmStudio/SwarmStudio.exe`, including WebEngine resources, the offline
demo and third-party notices. Keep that entire folder together. The executable
is unsigned; see [packaging notes](docs/PACKAGING.md) for the verified environment
and the Qt DLL isolation fix.

## Your first reconstruction

1. **Open a website.** Paste an `https://` URL, `http://localhost:PORT` or
   `http://127.0.0.1:PORT` address into the bottom dock, then click **Open**.
   Alternatively, choose **Studio → Try offline demo**.
2. **Prepare the page.** Wait for the layout and images to load. Choose the
   desired viewport under **Studio → Canvas options** before capturing.
3. **Initialize the swarm.** Click **Initialize Swarm**. The app analyzes the
   rendered page, saves its local reconstruction and builds the task graph.
4. **Watch the crew work.** In **Swarm** mode, agents draw, type, place and
   duplicate the captured elements. Keep **Tour** enabled to follow unfinished
   sections automatically.
5. **Adjust playback.** Use **Pause**, **Replay** and the speed selector. Enable
   **Sound** for synthesized agent sounds. The Studio menu provides stepping,
   diagnostics and the optional activity timeline.
6. **Explore the result.** Select **Reconstruction** to use the saved local DOM.
   Native accordions, CSS hover effects, anchors and other preserved browser
   behavior can work; source application scripts and backend services do not.
7. **Compare if needed.** Choose **Studio → Playback → Run comparison** to write
   screenshots, a difference heatmap and DOM checks.
8. **Export or record.** Use **Export** for a portable website ZIP or **Record**
   for an automatically directed movie.

Only capture content you own, have permission to reproduce, or otherwise have a
lawful basis to use. Avoid private accounts, personal information and secrets.

### Export the rebuilt website

1. Complete a capture or reopen a saved project.
2. Click **Export** and choose a ZIP destination.
3. Extract the ZIP into a new folder.
4. Open `index.html` to inspect the saved frontend. For a browser environment
   closer to the app's local preview, serve the extracted folder:

   ```powershell
   py -3.12 -m http.server 8000 --bind 127.0.0.1
   ```

5. Visit `http://127.0.0.1:8000/` in your browser. Press **Ctrl+C** in PowerShell
   when you finish the preview.

The project includes the captured document, reconstructed CSS, successfully saved
assets and metadata. Exporting does not restore a site's server, proprietary
scripts, protected content or missing resources. Export warnings identify capture
and asset limits. Rights in the website remain with their owners.

### Record an automatically edited cinematic video

1. Open a saved project or initialize a new swarm.
2. Click **Record** in the bottom dock or **Studio → Cinematic recording**.
3. Choose **1080p · 1920 × 1080** and **60 fps** for the default high-quality
   output; 720p and 30 fps are also available.
4. Select a camera cap of **3×**, **2×** or **Wide view**. Choose build speed and
   whether to include agent sounds.
5. Click **Save MP4…** and choose the destination.
6. Wait for the background render to finish, then click **Play video**.

The director chooses active edits, eases into close-ups, briefly gives the
selected work time to read, pulls back before section travel and finishes wide.
The saved MP4 contains the canvas, with optional synchronized synthesized audio.
It does not record the app toolbar, desktop, microphone or unrelated windows.

This is a deterministic movie render rather than a real-time desktop recorder:
every output frame is rendered individually. A busy desktop therefore does not
drop movie frames, although rendering can take longer than playback. The camera
editing is automatic; there is no manual video editor or timeline of editable
camera cuts in this release. Movies are bounded to ten minutes.

### Capture more than one page

Under **Studio → Settings → Capture**, increase the same-origin page limit from
the default **1** to **2–8** and choose link depth **0–2**. The crawler follows
eligible discovered links on the same origin, saves captured pages and rewrites
their local links. Common login, account, checkout and destructive paths are
excluded. Animation and cinematic recording cover the first captured page.

### Saved projects and shortcuts

Projects, settings and the SQLite library live under
`%LOCALAPPDATA%\SwarmStudio`. Use **Studio → Open saved project** to reopen work
without loading the original source. To keep a separate local library:

```powershell
.\.venv\Scripts\python.exe main.py --data-dir "D:\SwarmStudioData"
```

| Shortcut | Action |
| --- | --- |
| `Ctrl+L` | Focus the website address. |
| `Ctrl+N` | Start a new project. |
| `Ctrl+O` | Open a saved project. |
| `Ctrl+E` | Export the reconstructed website. |
| `F11` | Toggle fullscreen presentation. |

## Agent skills and coordination

The default roster contains eight named workers. The scheduler activates only
the workers needed for visible tasks; the roster is not a cloud of idle cursors.
Specialties guide assignment rather than permanently restricting each worker
to one operation.

| Agent | Specialty |
| --- | --- |
| Ada | Layout and frame construction. |
| Grace | Typography and text work. |
| Linus | Repeated components and duplication. |
| Hedy | Images and asset placement. |
| Alan | Inspection and verification. |
| Radia | Navigation and related text/layout work. |
| Margaret | Larger structural frames. |
| Ken | Fine details and paths. |

The core skills are drawing, typing, placing, duplicating, stroking and verifying.
Parent-frame milestones unlock dependent work; completed master components
unlock duplication. Published events drive the timeline and diagnostics. Cursor
position and visible work share one trajectory, so the mouse stays attached to
the job. Text uses browser ranges and Custom Highlights to preserve line layout.

These skills are implemented in the application itself. Running the app does not
require an agent marketplace, an external coding-agent skill or a paid AI service.

## Architecture

```mermaid
flowchart TD
    A[Public or local source website] --> B[Qt Chromium rendered capture]
    B --> C[Sanitized HTML, CSS and asset collection]
    B --> D[Stable element IDs and dependency blueprint]
    C --> E[Saved local project]
    D --> E
    E --> F[Trusted local player and coordinated agent crew]
    F --> G[Task-aware tour and construction choreography]
    E --> H[Portable website ZIP]
    E --> I[Headless browser and fixed-step recording clock]
    I --> J[Smooth recording director]
    J --> K[PyAV: H.264 video and optional AAC audio]
    E --> L[SQLite project library and metadata]
```

| System | Implementation |
| --- | --- |
| Desktop application | Python, PySide6 native widgets, Qt WebEngine and WebChannel. |
| Capture and planning | Isolated JavaScript DOM inspection, stable IDs and a dependency graph. |
| Local reconstruction | Beautiful Soup/lxml sanitization, HTTPX asset collection and CSS URL rewriting. |
| Agent motion | Independently implemented JavaScript, Canvas 2D, DOM Range and Custom Highlights. |
| Scrolling camera | Task-driven document/nested tours with eased motion and section holds. |
| Project storage | SQLite library, JSON metadata and portable directories. |
| Local preview | GET/HEAD-only loopback HTTP server. |
| Cinematic recording | Playwright, installed Edge/Chrome, CDP compositor frames and a deterministic clock. |
| Media encoding | PyAV/FFmpeg H.264, optional AAC, NumPy audio synthesis and Pillow frame handling. |
| Verification | pytest, independent browser checks, native UI checks and decoded-movie checks. |
| Windows packaging | PyInstaller, dependency notices and a current-user installation script. |

The source browser never receives the native WebChannel. Only the trusted local
player receives its bounded event bridge. The capture profile is memory-only;
cookies, browser storage and source scripts are not exported. Website loading
still makes ordinary network requests, and asset downloads occur locally within
configured budgets. See [the architecture document](docs/ARCHITECTURE.md).

### Repository layout

```text
app/                    Native UI, capture orchestration, reconstruction and storage
web/                    Capture, player, crew, choreography, cameras and offline demo
assets/                 Original application icons
scripts/                Build, launch, diagnostics, media and integration checks
tests/                  Core automated tests
docs/                   Architecture, provenance, packaging and verification
docs/media/             The README's ten-second cinematic demonstration
main.py                 Desktop entry point
SwarmStudio.spec        Windows packaging specification
LICENSE                 Personal noncommercial use terms
THIRD_PARTY_NOTICES.md   Dependency and third-party content boundaries
```

## Limitations

- **A frontend reconstruction, not a universal website compiler.** Source
  JavaScript, authentication, private APIs, databases and backend behavior are
  excluded. A visually faithful result is not proof of functional equivalence.
- **No autonomous LLM code generation.** Agent actions are a locally scheduled
  visualization of the captured task graph. They do not call an AI model or
  independently reason about a new product specification.
- **Capture is bounded.** Element counts, document height, lazy discovery,
  timeouts and asset budgets can limit the result. Infinite feeds and every
  possible hidden state are not exhaustively captured.
- **Some resources cannot be reproduced.** Protected, signed, unavailable,
  cross-origin or over-budget assets may be skipped. Cross-origin frames become
  placeholders; canvas may become an image. Closed shadow roots, WebGL, DRM and
  live video are unsupported; some video posters can survive.
- **Responsive behavior can differ.** The captured viewport is the primary
  fidelity target. Computed fallbacks, inaccessible CSS, platform fonts, complex
  shadow styling and dynamic CSS can change other layouts or states.
- **Forms and sessions are intentionally restricted.** Existing form values,
  hidden inputs, inline handlers and session storage are removed. Exported forms
  cannot submit to the source site's backend.
- **Comparisons are measurements, not guarantees.** RGB differences and geometry
  checks cover a viewport. They do not prove semantics, accessibility, behavior
  or backend equivalence. Occluded native views may retain stale screenshots.
- **Performance depends on the project.** Large DOMs and backward resimulation
  can take time. Interactive playback has no universal FPS guarantee. Movie
  exports have a fixed frame rate but can render slower than real time.
- **The recorded movie has scope limits.** It uses the first saved page, pauses
  decorative source animations, requires installed Edge/Chrome and has a
  ten-minute cap. Its camera is automatically directed rather than manually edited.
- **Windows is the verified platform.** Other operating systems, a signed
  installer and clean second-machine validation remain outside the current
  release verification.

## Verification and development

Run the core tests from PowerShell:

```powershell
New-Item -ItemType Directory -Path test-results -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=test-results/unit-run
```

Additional checks exercise actual Chromium pages, native windows and movie files:

```powershell
.\.venv\Scripts\python.exe scripts/test_browser.py
.\.venv\Scripts\python.exe scripts/test_camera.py
.\.venv\Scripts\python.exe scripts/test_crew.py
.\.venv\Scripts\python.exe scripts/test_focus_layout.py
.\.venv\Scripts\python.exe scripts/test_recording.py
.\.venv\Scripts\python.exe scripts/test_recording_hd.py
```

Run `test_recording.py` before `test_recording_hd.py`; the HD check uses its saved
fixture. Some checks use installed Chrome, and the recording check uses installed
Edge. Native checks open real windows. Public-site and isolated-reference checks
have additional network/reference prerequisites documented in their scripts.

For unattended native checks behind other windows, set the following only for
the test process to reduce Chromium background throttling:

```powershell
$env:QTWEBENGINE_CHROMIUM_FLAGS='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
```

The verified demo movie completed all **66 tasks**, produced **1,619 frames at
1920 × 1080 / 60 fps**, and decoded with the exact expected frame count and
monotonic timestamps. The Windows executable also completed a real MP4 export.
Those results describe the tested fixture, not every possible website. Detailed
evidence is documented in [verification](docs/VERIFICATION.md).

To recreate the README GIF from a recording you are authorized to use:

```powershell
.\.venv\Scripts\python.exe scripts/make_readme_gif.py --input "C:\path\to\recording.mp4" --start 38 --duration 10 --fps 20 --width 800 --colors 128
```

## License and permissions

Copyright © 2026 **Byte by Mint**. All rights reserved.

SWARM STUDIO uses a custom **Personal Noncommercial Use License**. You may
inspect, run and privately modify it for personal, noncommercial learning and
evaluation. Only working and backup copies necessary for that permitted use are
allowed. Redistribution, copying into another distributed project, selling,
paid client work and other commercial use require **prior written approval**.
This is restricted source-available software, not an open-source license.

Read [LICENSE](LICENSE) for the actual terms. Third-party libraries retain their
own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). This license
does not grant rights in websites or content you capture.

**Commercial licensing, redistribution and permission requests:**
[info@bytebymint.space](mailto:info@bytebymint.space).

