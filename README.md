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

