"""M5 tests: DROID replay trajectory + cache loader + full droid_replay run.

All tests avoid the network and the optional `lerobot` dependency by using a
synthetic joint-position cache. The full-run test also needs mujoco + fetched
assets and self-skips otherwise.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest

import droid_bridge.adapter as adapter
from sim.config import REPO_ROOT, load_scenario
from sim.trajectories import GRIPPER_OPEN, DroidReplayTrajectory

SCEN_DIR = REPO_ROOT / "config" / "scenarios"
FETCHED_PANDA = REPO_ROOT / "assets" / "menagerie" / "franka_emika_panda" / "panda.xml"
HOME = np.array([0.0, 0.0, 0.0, -1.57079, 0.0, 1.57079, -0.7853])


def test_droid_replay_trajectory() -> None:
    positions = np.stack([HOME, HOME + 0.2, HOME + 0.4]).astype(np.float32)
    traj = DroidReplayTrajectory(positions=positions, fps=10.0)
    assert traj.duration == pytest.approx(0.2)                 # (3-1)/10
    assert np.allclose(traj.initial_arm, HOME)
    c0 = traj.control_at(0.0)
    assert c0.shape == (8,)
    assert np.allclose(c0[:7], HOME) and c0[7] == GRIPPER_OPEN
    # midpoint interpolation between frame 0 and 1
    assert np.allclose(traj.control_at(0.05)[:7], HOME + 0.1, atol=1e-5)


def test_droid_replay_trajectory_rejects_bad_shape() -> None:
    with pytest.raises(ValueError):
        DroidReplayTrajectory(positions=np.zeros((5, 6), np.float32), fps=15.0)


def test_loader_reads_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "CACHE_DIR", tmp_path)
    src, ep = "lerobot/droid_100", 3
    positions = np.zeros((5, 7), dtype=np.float32)
    np.savez_compressed(adapter._cache_path(src, ep), positions=positions, fps=15.0)

    got, fps = adapter.load_episode_joint_positions(src, ep)
    assert got.shape == (5, 7) and fps == 15.0


def test_droid_replay_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("mujoco")
    if not FETCHED_PANDA.exists():
        pytest.skip("Menagerie model not fetched — run `make fetch-assets` first")

    cache_dir = tmp_path / "droid_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(adapter, "CACHE_DIR", cache_dir)

    scenario = load_scenario(SCEN_DIR / "droid_replay_reach_check.yaml")
    src = scenario.trajectory["source"]
    ep = int(scenario.trajectory["episode_index"])
    # small motion around home so the TCP stays inside the reach envelope
    t = np.linspace(0.0, 3.0, 30)
    positions = (HOME[None, :] + 0.1 * np.sin(t)[:, None]).astype(np.float32)
    np.savez_compressed(adapter._cache_path(src, ep), positions=positions, fps=15.0)

    scenario = dataclasses.replace(scenario, render={}, cameras=[])
    from sim.runner import run_scenario

    artifacts = run_scenario(scenario, outputs_root=tmp_path / "out")
    assert artifacts.states_path.exists()
    assert artifacts.sim_duration_s == pytest.approx((30 - 1) / 15.0, rel=1e-3)
