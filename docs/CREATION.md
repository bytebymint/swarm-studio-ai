# Live website creation

The initial native chooser opens Rebuild or Create. Rebuild retains its existing
capture, comparison, export and cinematic recording workflow. Create adds a native
instruction chat, selectable target context, live canvas, interactive preview,
responsive viewports, uploads, local projects, revisions and static ZIP export.

## Model and authoring loop

`app/creation.py` calls the OpenAI-compatible Chat Completions endpoint using
native `httpx`. The default is Alibaba Model Studio's international endpoint and
`qwen3.8-flash`, with streaming and `enable_thinking: false` for prompt response.
The native connection dialog supports other compatible deployment endpoints.

The model receives the instruction, relevant recent instructions, selected
element, current source, available image metadata and uploaded images. Cancelled
or still-queued instructions are excluded. Image data is not duplicated in the
text context: source references use `asset:ID`, resolved natively to embedded
images after validation.

Incremental JSON operations set the title/theme/scripts, insert or replace a
named section, remove a section, describe a plan or finish. Each operation is
schema-checked and applied atomically. Model output is never a shell command or
native file path. An interrupted JSON object is not applied. Valid operations
survive a later malformed response or network failure.

The bounded authoring loop continues when a provider ends after one operation,
asks for corrections on malformed output, and stops on the finish operation.
It has a twenty-four-round and four-minute work budget. Smart review uses off-screen
desktop/mobile measurements and a non-executing JavaScript syntax check, then
asks for targeted repairs. Remaining measured issues are surfaced. A completed
network response alone does not prove the requested website is correct.

## The same swarm visualization

`web/create.html` loads the exact same `crew.js`, `choreography.js`, `camera.js`,
`media.js`, `director.js` and `swarm-engine.js` as Rebuild. `create-engine.js`
adapts incoming operations into the existing element/task graph. It uses the same
`WorkingCrew`, `TaskChoreography` and `CinematicTour`, including specialist
assignment, minimum-jerk travel, range-based typing, image placement, duplicate
components, frame milestones, handoffs, work cards and scroll timing.

Section updates are diffed against their prior source. A changed headline receives
a text task while unchanged DOM nodes, media and controls remain in place.
Structural changes animate the changed subtree. In-flight changes to the same section
wait for its current work to release; other sections can be built concurrently.
Removal is a shared choreography operation. Existing sections are preserved
during targeted edits. Off-canvas skip links remain in the output but are not
vertical construction jobs. The shared preparation path restores the visibility
masks and disables CSS smooth scrolling while the task camera owns movement.

The canvas is script-free and same-origin so that the trusted renderer can
inspect and animate it. Interactive preview runs the generated JavaScript in a
separate `allow-scripts` iframe without `allow-same-origin`. It cannot read the
parent document or the Qt bridge. Preview selection is a bounded message carrying
element context, not a native action. The native bridge is injected into the
trusted top-level UI only.

## Credentials and local data

The API key never enters preview JavaScript or the model's prompt. Windows DPAPI
encrypts it for the current Windows user in `.private/qwen.key`, which the local
HTTP server refuses to serve. Public source and releases contain no credentials,
including encrypted bootstrap credentials. Add your own key through **Model**.
`QWEN_API_KEY` remains an optional
native process override for development and local simulator tests.

Created projects live under `creation/projects/ID`. Atomic JSON writes preserve
the last complete operation, a recoverable working draft and up to thirty
revisions. Undo/Redo select earlier revisions without an API request. A fresh edit
after Undo begins a new active revision branch; previous snapshot files are not
deleted. Source autosaves are coalesced to keep streaming work responsive.

The generated ZIP includes only `index.html` and its usage note. HTML embeds its
CSS, browser JavaScript, SVG artwork and uploaded image data, so it works without
the model endpoint. App settings, credentials, chat and revision metadata are
excluded. API redirects are not followed, environment proxies are not inherited,
and provider error bodies are not copied into the chat or logs.

## Current boundaries

- This builds static frontend websites with browser interactions. It does not
  provision servers, databases, payment processors, authentication or email
  services. The model is instructed to avoid fake backend-success messages.
- Generated scripts cannot make network calls in preview or export. Remote
  frameworks, CDNs, external fonts, iframes and imported stylesheets are excluded.
  Original inline artwork and user-uploaded images keep output self-contained.
- Up to six PNG/JPEG/WebP uploads are resized and embedded. Inputs are bounded at
  20 MB / 24 megapixels; optimized embedded images are at most 120 KB each.
- Source is bounded to 3 MB and 64 named sections. Streaming operations and
  responses have additional size/operation budgets. A section contributes at
  most 500 visual tasks, with 2,500 tasks per authoring turn; the website itself
  retains its full HTML.
- A provider key, supported model access, network and provider usage charges are
  required for generation and editing. Saved websites and ZIPs run offline.
- Shared visual workers are task-driven personas; Qwen writes the actual source.
  Their on-screen tools represent real received operations, not independent
  operating-system mouse control or hidden native execution.
- Current cinematic MP4 recording remains in Rebuild. Create's live model session
  is not a deterministic recording/replay of remote API timing.
- Provider behavior and design quality vary. Syntax/layout checks do not prove
  every interaction works. Use the interactive preview and review exported code.

## Verification

`tests/test_creation.py` covers protocol parsing, transport, limits, sanitization,
encrypted keys, targeted changes, revisions, draft recovery, assets and ZIPs.
`scripts/test_creation_browser.py` checks the shared renderer, visibility masks,
handoffs, duplication, removal, responsive audits, real browser interactions,
offline output and the opaque-origin/network boundary. `test_creation_qt.py`
drives the real Windows UI through a local streaming provider and verifies that
sections appear before the model response finishes. `test_creation_portable.py`
tests a copied standalone EXE without Python on its PATH, using an explicitly
configured local model simulator; it never spends the real provider key.

Provider protocol references:
[Chat Completions](https://help.aliyun.com/en/model-studio/qwen-api-via-openai-chat-completions),
[streaming](https://www.alibabacloud.com/help/en/model-studio/stream),
[Qwen3.8 Flash](https://help.aliyun.com/en/model-studio/qwen3-8-flash).
