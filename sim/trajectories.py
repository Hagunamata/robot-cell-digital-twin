"""Trajectory sources for the scenario runner.

Placeholder module (M0 scaffold — no logic yet). To be implemented in M2/M5.

Planned trajectory types (per config/scenarios/*.yaml):
    - scripted        : hand-authored waypoints / joint targets.
    - ik_waypoints    : Cartesian waypoints solved to joint space via IK.
    - droid_replay    : a DROID episode mapped onto the MuJoCo Franka
                        (delegated to droid_bridge; the Project-2 bridge).
"""

from __future__ import annotations
