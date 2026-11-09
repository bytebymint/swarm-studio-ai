# Windows packaging

## Single-file portable build

Run `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1 -Portable`
after setting up the pinned development environment. The script runs pytest,
downloads the matching Playwright Chromium headless shell into
`build/portable-browsers`, collects dependency licenses and builds
`dist/SwarmStudioAI-Portable.exe`. Only this EXE needs to be distributed. The
existing folder distribution remains available without `-Portable`.

The EXE embeds Python, Qt WebEngine, the web player and demo, the recording
browser, PyAV/FFmpeg, documentation and license notices. It automatically extracts
these to a temporary `_MEI...` directory at startup. Extraction needs disk space
and makes startup slower than the folder distribution. Projects, settings and
logs use `%LOCALAPPDATA%\SwarmStudio`, or the explicit `--data-dir` directory;
they are not removed with the temporary runtime. No administrator installation
or machine-wide PATH changes are needed. This is a Windows 11 x64 build, not a
cross-platform or universal-machine executable. It is unsigned.

Open **Studio → About and licenses** to read the unchanged proprietary project
license and open the embedded third-party notices. The Chromium distribution's
own notices are also retained in its bundled directory. Generated binaries and
browser staging directories stay out of Git.

Recording tries installed Edge/Chrome first for codec compatibility, then uses
the bundled Chromium shell if neither launches. The fallback requires no browser
download on the receiving computer. Source and folder builds still require
installed Edge/Chrome. Codec support can differ between these browsers; bundling
Chromium does not add support for DRM or authenticated media.

Verify the actual single-file distribution with:

```powershell
.\.venv\Scripts\python.exe scripts/test_portable.py --exe dist/SwarmStudioAI-Portable.exe
.\.venv\Scripts\python.exe scripts/test_creation_portable.py --exe dist/SwarmStudioAI-Portable.exe
```

The check copies only the EXE into a fresh directory, strips development paths
from the child's environment, forces the bundled recording browser, launches the
real native Qt window, captures the offline demo, completes agent playback,
compares, exports a ZIP and encodes a 720p MP4. It checks the movie streams, ZIP,
temporary extraction and successful shutdown. This host-isolation check does not
replace testing on a clean second Windows 11 machine.

The Create check uses an explicit local streaming model simulator and a synthetic
process-only credential. It verifies the startup chooser, shared swarm renderer,
creation, follow-up editing, Undo/Redo and website export without spending a real
provider key. Its hidden smoke mode advances the same simulation with fixed
steps, avoiding the host's background-window RAF throttling. Normal playback uses
the regular live animation clock.

Public builds explicitly exclude `app.local_credentials` and never embed a provider
key, even an encrypted one. Users add their own key through **Model**; runtime keys
are encrypted with Windows DPAPI in the user's application data. Build verification
must inspect the embedded Python archive for excluded credential modules, scan
tracked source for secrets, and test with an isolated data directory.

## Windows DLL isolation

The first packaged launch failed at `PySide6.QtCore` despite working from Python.
Inspection of PE imports and `Analysis-00.toc` identified an incompatible
`icuuc.dll` copied from the Codex host's Poppler tool directory. That library
exports version-suffixed ICU 78 symbols; QtCore requests the Windows unversioned
ICU facade. A development Python process correctly loaded System32's facade.

The specification now replaces the packaging process's PATH with Python, its Qt
packages and Windows system directories, rejects binaries resolved from the Codex
host runtime, and excludes app-local ICU facades. Windows 11 supplies the required
system interface. This changes no machine-wide PATH or installed Windows DLL.

The PyInstaller project documents how unrelated DLLs on PATH can produce this
class of Qt import failure: https://github.com/pyinstaller/pyinstaller/issues/6297 .
Our specific diagnosis comes from the local import/export tables and build TOC.

The final executable must pass `--smoke-report PATH` after each build, and a clean
second-machine Windows 11 check remains a release step. Never mark a successful
PyInstaller command alone as a verified desktop distribution.

Cinematic recording bundles Playwright's driver, PyAV/FFmpeg and NumPy through
their PyInstaller hooks. The folder build uses installed Edge or Chrome with a
fresh context; the portable variant also embeds Chromium. Package notices include these dependencies.
Use `--smoke-report PATH --smoke-recording` to run the native capture/comparison/
ZIP workflow and encode an actual MP4 from the frozen executable. The report
includes movie dimensions, frame count, camera shots and audio events.

## Public release checklist

Run `scripts/verify_public_build.py --exe dist/SwarmStudioAI-Portable.exe` after
packaging. It checks the embedded Python archive and text payloads for credential
modules and token-shaped secrets, scans publishable source, and writes
`dist/SHA256SUMS.txt`. Run both copied-EXE smoke scripts above. Attach the EXE and
checksum to a GitHub Release; do not commit binaries, local data or test results.
The Windows Actions workflow can also build a key-free artifact on a version tag
or through **Run workflow**. A local validation is not a claim that a remote
Actions run has passed.

Generate the documented Create animation with `scripts/make_creation_gif.py`.
It records the actual native app using an original four-section SaaS response
fixture. It never calls a cloud model; the resulting GIF labels this fact.
