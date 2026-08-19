"""Frame overlay + MP4 encoding for the baseline MuJoCo video path.

Placeholder module (M0 scaffold — no logic yet). To be implemented in M4.

Planned responsibility:
    - Draw the per-scenario verdict and metrics onto rendered frames
      (e.g. "Reach: OK", "Cycle time: 11.4 s / 12.0 s").
    - Highlight a clearance breach when it occurs.
    - Encode the annotated frames to MP4 (imageio-ffmpeg), headless.
"""

from __future__ import annotations


def render_clip(*args, **kwargs):
    """Render an annotated MP4 for one scenario run. Not yet implemented."""
    raise NotImplementedError("render.mujoco.overlay.render_clip is implemented in M4")
