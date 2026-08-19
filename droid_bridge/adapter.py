"""DROID episode -> MuJoCo Franka actuator mapping adapter.

Placeholder module (M0 scaffold — no logic yet). To be implemented in M5.

Planned responsibility:
    - Load a DROID episode (e.g. from lerobot/droid_100).
    - Map its action space onto the MuJoCo Franka Panda actuators.
    - Yield per-step targets consumable by sim.trajectories (droid_replay).

Do NOT assume the DROID action space; verify it against the real dataset.
"""

from __future__ import annotations


def load_episode(*args, **kwargs):
    """Load a DROID episode trajectory. Not yet implemented."""
    raise NotImplementedError("droid_bridge.adapter.load_episode is implemented in M5")
