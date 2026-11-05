# Video reconstruction

## Workflow and implementation plan

Inspection traced source loading in `browser.py`, isolated DOM analysis in
`capture.js`, asset collection, sanitization, the task blueprint, crew and
choreography, local serving, saved projects, ZIP export and deterministic movie
rendering. The former capture explicitly removed video sources and classified
videos as images; the collector rejected video MIME types and buffered downloads;
the server had no range support; the recording clock did not advance video.

The implementation follows the existing architecture:

1. Capture safe video candidates and media properties, including lazy attributes,
   runtime-populated sources and accessible shadow roots.
2. Stream unauthenticated media to temporary files, validate containers/codecs,
   publish successful local mappings and report failures.
3. Rewrite video/source/poster references and build explicit fallbacks.
4. Assign `place_media` jobs through the existing dependency graph and reveal
   them with the existing drag, selection-box and clipping choreography.
5. Seek paused local video decoders on the movie clock before compositor capture;
   preserve the camera, fixed output cadence and separate agent audio.
6. Verify real capture, source-independent playback, ZIP contents, ranges,
   deterministic frames, Windows/Qt playback and existing regressions.

## Supported sources

Direct HTTP(S) MP4 (H.264/AV1) and WebM (VP8/VP9/AV1) containers are accepted
when downloadable without authentication and validated by the installed decoder.
Actual browser support remains codec/platform dependent. Both `<video src>` and
nested `<source>` candidates are inspected. Current runtime sources, `data-src`
and `data-lazy-src` on video, and `data-src` on source elements are discovered.
Multiple videos share deduplicated asset downloads. Open shadow roots are
flattened as before. Hidden videos are collected without creating invisible
swarm jobs. The capture is a snapshot after bounded lazy discovery, not an
indefinite watcher for future JavaScript updates.

Metadata includes current source/candidates, poster, autoplay, mute, loop,
controls, preload, inline playback, intrinsic dimensions, aspect ratio, playback
rate, position and paused state. Geometry and styling remain in the captured DOM
and CSS. Media-specific candidate metadata is rewritten to local paths in the
blueprint. `metadata/capture-report.json` includes validated MIME, bytes, codec
and dimensions. `downloaded`, `poster-only` and `unsupported` are distinct states.

Downloads reside in `assets/media/`. A video advertised as octet-stream is only
accepted with an MP4/WebM extension and valid matching container signature.
Downloads stream in 64 KiB chunks, check cancellation and read deadlines, reject
unsafe redirects and HTTPS downgrades, and use temporary files removed on
failure/cancellation. Mappings are published only after validation. Video pixels
are capped at 16,777,216 before first-frame decoding. No full-video byte buffer
or movie-length frame cache is retained by the application.

## Settings and playback

**Studio → Settings → Media** exposes `max_video_mb` (default 64 MB per file)
and `max_total_media_mb` (default 256 MB per capture/page). These budgets are
separate from the existing image/font limits. Multi-page capture applies the
budgets to each captured page. Existing capture deadlines still bound collection.
Warnings identify skipped/failed media without reproducing credential URLs.

The loopback server supports bounded single HTTP byte ranges, suffix/open-ended
ranges, HEAD, 206 responses and 416 unsatisfiable ranges. Multipart ranges are
rejected. Traversal, dotfile, directory-listing and write-method restrictions
remain. ExportWorker already archives project assets recursively, so videos
travel with the ZIP; no source-server connection is needed after export.

Browser-native controls and muted autoplay/loop behavior are retained where the
browser supports them. Agent playback is muted; exploration restores the captured
mute preference. Browser playback policies may require a user gesture for sound.
Decode failures produce a poster or visible unavailable-video fallback, plus a
native diagnostic event, rather than a successful-playback claim.

## Cinematic movies

The planning pass advances only the task graph. The render pass pauses source
videos and seeks them to the output movie time plus their captured initial
position, honoring playback rate and looping. Paused non-autoplay videos retain
their captured position. Looping uses modulo duration; non-looping videos clamp
to the last available frame. Source-video time follows movie time, while the
build-speed selector affects construction speed.

Only revealed, visible videos are sought, in batches of at most four simultaneous
seeks. Re-entering the viewport uses absolute movie time rather than stale
offscreen playback time. Each seek awaits the decoder/compositor video-frame callback before the screenshot
(or seek completion on browsers without that callback). A four-second metadata/
frame deadline and a five-second overall synchronization budget per output frame
convert decode failures or excessive seek work into explicit fallbacks and report them
in movie metadata and the completion dialog. Same-position frames are reused;
browser decoders maintain their own buffers, with no application frame cache.
Rendering can therefore be slower than real time. Existing 720p/1080p and 30/60
fps encoding, camera transitions and optional synthesized agent audio remain.
Source-video audio is deliberately muted during recording and is not mixed.

The frame-callback mechanism is described in the
[video-frame callback specification](https://wicg.github.io/video-rvfc/).

## Unsupported cases and security

HLS/DASH manifests, MSE/blob streams, DRM, authenticated/signed sources,
cross-origin embedded players, unavailable files, invalid containers, excessive
dimensions and unsupported codecs use an available authorized poster or a marked
placeholder. They are not described as reconstructed playable videos. There is
no stream resolver, browser-session forwarding or access-control bypass.

Existing CSP (`media-src 'self' data:`), sandbox, bridge isolation and source
script removal remain unchanged. Only local saved assets are permitted in the
recording browser. Media requests use a fresh client with no forwarded cookies,
authorization or environment proxy credentials. Known secret-bearing URL
parameters and embedded credentials are rejected. Obtain permission to download,
reproduce, record and publish content; this feature grants no third-party rights.
The proprietary project license and ownership notices remain unchanged.

## Verification

`tests/test_media.py` generates original silent MP4/WebM fixtures and checks range
serving, streaming budgets, deduplication, failures, cancellation, invalid data,
unsafe redirects, MIME handling and cookie isolation.
`scripts/test_video.py` performs real Edge capture, lazy/shadow/multiple-video
inspection, poster/unsupported fallbacks, source-server shutdown, ZIP extraction,
offline playback, media task completion, loop/seek pixel determinism and a real
720p MP4 movie render. `scripts/test_video_qt.py` follows it to exercise native
Windows Qt WebEngine WebM playback, the existing shell and six media tasks.
See `VERIFICATION.md` for the executed suite and results.
