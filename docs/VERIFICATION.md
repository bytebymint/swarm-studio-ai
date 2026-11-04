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

