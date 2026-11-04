# README demonstration

`swarm-studio-demo.gif` is a ten-second excerpt, from 00:38 to 00:48, of the
user-supplied desktop recording `swarm-recording.mp4`. It preserves the camera
zoom and collaboration visible in that recording; no new agent motion was
generated for the GIF. The original video remains outside this repository.

The excerpt uses a shared palette, loops continuously and has no audio. It is
resized for README playback; the app can export full 1920 × 1080 MP4 movies at
60 fps. The README GIF itself is not a 1080p movie.

Rebuild it from a recording you have permission to use:

```powershell
.\.venv\Scripts\python.exe scripts/make_readme_gif.py --input "C:\path\to\swarm-recording.mp4" --start 38 --duration 10 --fps 20 --width 800 --colors 128
```

The command verifies the GIF's total playback time after encoding. Use
`--contact-sheet test-results/readme/contact-sheet.jpg` to inspect the source
before choosing a segment.

The depicted third-party website, branding and content remain their owners'
property. This software demonstration grants no rights to those materials and
implies no affiliation or endorsement. See
[third-party notices](../../THIRD_PARTY_NOTICES.md).
