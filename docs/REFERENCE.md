# Reference investigation and provenance

The supplied `swarm-cursors-main/` directory is an isolated, unmodified reference.
Source: https://github.com/DhvanilPatel/swarm-cursors . Its README credits
Joel Califa's https://github.com/califa/swarm-site and explicitly states that
neither source grants a published license. No reference JavaScript, demo HTML,
icons or recordings are bundled in the desktop distribution. Obtain permission
from the relevant authors before distributing their material.

`swarm.js` is a single injected closure. `captureModel` walks styled DOM and open
shadow roots, detects repeated siblings and emits visual layers and dependencies.
`detectEnv` selects document scrolling or a large inner scroller. `View` isolates
the build scene in a shadow tree. `Engine` assigns generator-based drawing scripts
to lightweight cursor objects, unlocks tasks at the viewport frontier and applies
flocking. `Sound` synthesizes per-event clicks, keyboard noise, spatial notes and
transition chords. `App` coordinates preparation, capture, playback and teardown.
`window.__swarmRebuild` exposes start/stop/restart and debugging.

`background.js` uses chrome.scripting to inject, chrome.tabs.captureVisibleTab for
otherwise inaccessible media pixels, and chrome.runtime to restore hidden media.
Those APIs cannot run in Qt. The new app uses QWebEnginePage.runJavaScript in
ApplicationWorld for read-only inspection, a private local playback document with
QWebChannel, and widget screenshots for comparison. Remote documents never get
the native bridge. The engine here was written separately; no extension adapter
silently loads the reference engine.

