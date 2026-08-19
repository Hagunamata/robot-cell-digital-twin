"""Trajectory sources for the scenario runner.

M2 implements the `scripted` type as piecewise-linear joint-space motions.
`ik_waypoints` and `droid_replay` are placeholders (droid_replay -> M5 bridge).

Actuator layout (verified against Menagerie panda.xml):
    ctrl[0:7] = arm joint position targets (actuator1..7, ctrlrange ±2.8973 rad)
    ctrl[7]   = gripper command (actuator8, ctrlrange 0..255; 255≈open, 0≈closed)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Panda "home" keyframe arm angles (first 7 of the length-9 home qpos).
HOME_ARM: tuple[float, ...] = (0.0, 0.0, 0.0, -1.57079, 0.0, 1.57079, -0.7853)
GRIPPER_OPEN = 255.0
GRIPPER_CLOSED = 0.0

NU = 8  # number of actuators


@dataclass(frozen=True)
class Waypoint:
    """A target arm pose + gripper, and the time to move to it from the previous."""

    arm: tuple[float, ...]      # length 7, joint position targets (rad)
    gripper: float              # 0..255
    duration_s: float           # segment duration from the previous waypoint


@dataclass
class ScriptedTrajectory:
    """Piecewise-linear interpolation over a list of waypoints."""

    waypoints: list[Waypoint]

    def __post_init__(self) -> None:
        self._t = np.concatenate([[0.0], np.cumsum([w.duration_s for w in self.waypoints])])
        self._ctrl = np.array(
            [[*self.waypoints[0].arm, self.waypoints[0].gripper]]
            + [[*w.arm, w.gripper] for w in self.waypoints]
        )  # shape (n+1, 8): index 0 duplicates the first waypoint as the start pose

    @property
    def duration(self) -> float:
        return float(self._t[-1])

    def control_at(self, t: float) -> np.ndarray:
        """Return the length-8 ctrl vector at time t (clamped to [0, duration])."""
        t = float(np.clip(t, 0.0, self.duration))
        # np.interp per actuator channel over the cumulative-time knots.
        return np.array([np.interp(t, self._t, self._ctrl[:, i]) for i in range(NU)])


# --- Named scripted motions referenced by config/scenarios/*.yaml -----------
# Illustrative joint-space motions; not tuned to real cell geometry.

def _pick_place() -> ScriptedTrajectory:
    """A generic reach-down / grasp / lift / place / return cycle."""
    reach = (0.0, 0.5, 0.0, -2.0, 0.0, 2.5, -0.7853)      # lean toward workpiece
    place = (0.9, 0.4, 0.0, -1.9, 0.0, 2.3, -0.7853)      # rotate to place pose
    return ScriptedTrajectory([
        Waypoint(HOME_ARM, GRIPPER_OPEN, 1.5),
        Waypoint(reach, GRIPPER_OPEN, 2.0),               # move over target
        Waypoint(reach, GRIPPER_CLOSED, 1.0),             # grasp
        Waypoint(HOME_ARM, GRIPPER_CLOSED, 2.0),          # lift
        Waypoint(place, GRIPPER_CLOSED, 2.0),             # carry to place
        Waypoint(place, GRIPPER_OPEN, 1.0),               # release
        Waypoint(HOME_ARM, GRIPPER_OPEN, 2.0),            # return home
    ])


def _pick_place_near_human() -> ScriptedTrajectory:
    """Like pick_place, but the carry swings toward the +Y human_zone_1 side."""
    reach = (0.0, 0.5, 0.0, -2.0, 0.0, 2.5, -0.7853)
    near_human = (1.4, 0.3, 0.0, -1.6, 0.0, 2.0, -0.7853)  # base rotated toward human zone
    return ScriptedTrajectory([
        Waypoint(HOME_ARM, GRIPPER_OPEN, 1.5),
        Waypoint(reach, GRIPPER_OPEN, 2.0),
        Waypoint(reach, GRIPPER_CLOSED, 1.0),
        Waypoint(near_human, GRIPPER_CLOSED, 2.5),         # swing near the human proxy
        Waypoint(near_human, GRIPPER_OPEN, 1.0),
        Waypoint(HOME_ARM, GRIPPER_OPEN, 2.0),
    ])


_MOTIONS = {
    "pick_place": _pick_place,
    "pick_place_near_human": _pick_place_near_human,
}


def build_trajectory(trajectory_cfg: dict) -> ScriptedTrajectory:
    """Build a trajectory from a scenario's `trajectory` block.

    Raises NotImplementedError for types wired up in later milestones.
    """
    ttype = trajectory_cfg.get("type")
    if ttype == "scripted":
        motion = trajectory_cfg.get("motion")
        if motion not in _MOTIONS:
            raise KeyError(f"Unknown scripted motion: {motion!r} (have {list(_MOTIONS)})")
        return _MOTIONS[motion]()
    if ttype == "ik_waypoints":
        raise NotImplementedError("ik_waypoints trajectory source is a future milestone")
    if ttype == "droid_replay":
        raise NotImplementedError("droid_replay is implemented by the M5 droid_bridge")
    raise ValueError(f"Unknown trajectory type: {ttype!r}")
