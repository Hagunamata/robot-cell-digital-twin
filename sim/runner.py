"""MuJoCo scenario runner.

Placeholder module (M0 scaffold — no logic yet). To be implemented in M2.

Planned responsibility:
    - Load an MJCF work-cell scene (arm + human/obstacle proxy).
    - Drive it with a trajectory source (scripted | ik_waypoints | droid_replay).
    - Step the physics loop headless (EGL/OSMesa), collecting states,
      contacts, TCP path, clearances, timings, and camera frames.
    - Emit a structured sim log consumed by the verifier and renderer.
"""

from __future__ import annotations


def run_scenario(*args, **kwargs):
    """Run a single scenario headless and return its sim log. Not yet implemented."""
    raise NotImplementedError("sim.runner.run_scenario is implemented in M2")
