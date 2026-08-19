"""DROID episode -> MuJoCo Franka joint-trajectory adapter.

M5 implementation. Loads one DROID episode's recorded **joint positions**
(observation.state, 7-DoF) from a LeRobot dataset and returns them as a plain
array the sim can replay. The MuJoCo Franka is driven in JOINT POSITION space
(actuator1..7); the gripper is held constant.

Verified facts (dataset card + DROID docs; do not re-guess):
    - DROID robot = Franka Emika Panda 7-DoF (+ Robotiq gripper) — same arm as
      our MuJoCo Menagerie model, which is the whole point of this bridge.
    - lerobot/droid_100 (LeRobot v3.0): observation.state = float32[7] joint
      positions (rad); action = float32[7]; fps = 15; NO gripper channel.
    - We replay observation.state (the unambiguous joint configuration). We do
      NOT integrate `action` because droid_100 does not document its control
      mode (velocity vs delta vs next-position).

Loading: uses the optional `lerobot` package when available, and caches the
extracted joint array to a gitignored npz so later runs need neither lerobot nor
network. See docs/02-development.md.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "assets" / "droid_cache"     # gitignored

N_JOINTS = 7


def _cache_path(source: str, episode_index: int) -> Path:
    safe = source.replace("/", "__")
    return CACHE_DIR / f"{safe}_ep{episode_index}.npz"


def _extract_via_lerobot(source: str, episode_index: int) -> tuple[np.ndarray, float]:
    """Extract one episode's joint positions using the optional lerobot package."""
    try:  # module path moved across lerobot versions — try both.
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
    except ImportError:
        from lerobot.common.datasets.lerobot_dataset import LeRobotDataset

    ds = LeRobotDataset(source)
    efrom = int(ds.episode_data_index["from"][episode_index])
    eto = int(ds.episode_data_index["to"][episode_index])
    rows = ds.hf_dataset.with_format("numpy")[efrom:eto]      # no video decode
    positions = np.asarray(rows["observation.state"], dtype=np.float32)
    if positions.ndim != 2 or positions.shape[1] != N_JOINTS:
        raise ValueError(
            f"Expected observation.state of shape [T,{N_JOINTS}], got {positions.shape}"
        )
    return positions, float(ds.fps)


def load_episode_joint_positions(
    source: str, episode_index: int, use_cache: bool = True
) -> tuple[np.ndarray, float]:
    """Return (positions[T,7] float32 joint angles in rad, fps) for one episode.

    Reads a cached npz if present; otherwise extracts via lerobot and caches it.
    Raises ImportError (with guidance) if lerobot is needed but not installed.
    """
    cache = _cache_path(source, episode_index)
    if use_cache and cache.exists():
        data = np.load(cache)
        return data["positions"].astype(np.float32), float(data["fps"])

    try:
        positions, fps = _extract_via_lerobot(source, episode_index)
    except ImportError as exc:
        raise ImportError(
            "DROID replay needs the optional 'lerobot' package (pip install lerobot), "
            f"or a pre-extracted cache at {cache}. See docs/verification.md (M5)."
        ) from exc

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, positions=positions, fps=fps)
    return positions, fps
