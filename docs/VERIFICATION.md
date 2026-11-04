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

