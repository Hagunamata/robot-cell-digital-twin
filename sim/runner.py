"""MuJoCo scenario runner (headless).

M2 implementation. Loads an MJCF work-cell scene, drives the Franka with a
trajectory source, steps the physics loop headless, and logs states, contacts,
and camera frames to outputs/ (gitignored). Verdicts/metrics are NOT computed
here — that is the M3 verifier's job; M2 only produces the sim log.

Headless rendering uses whatever GL backend MUJOCO_GL selects (osmesa for pure
CPU containers, egl where a GPU/driver is present). No on-screen display.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import mujoco
import numpy as np

from sim.config import REPO_ROOT, Scenario
from sim.trajectories import build_trajectory

# Logging / rendering cadence.
CONTROL_LOG_HZ = 50      # state-log sample rate
RENDER_FPS = 15          # frames captured per camera
RENDER_H, RENDER_W = 240, 320


@dataclass
class RunArtifacts:
    """Paths + light-touch signals produced by a run (consumed by M3/M4)."""

    run_id: str
    run_dir: Path
    states_path: Path
    meta_path: Path
    frame_paths: dict[str, Path] = field(default_factory=dict)
    sim_duration_s: float = 0.0
    min_tcp_to_human_m: float = float("inf")
    max_contacts: int = 0


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - best-effort provenance
        return "unknown"


def _name2id(model: mujoco.MjModel, objtype: int, name: str) -> int:
    idx = mujoco.mj_name2id(model, objtype, name)
    if idx < 0:
        raise KeyError(f"MJCF object not found: type={objtype} name={name!r}")
    return idx


def run_scenario(scenario: Scenario, outputs_root: Path) -> RunArtifacts:
    """Run one scenario headless and write its sim log. Returns RunArtifacts."""
    if not scenario.scene_path.exists():
        raise FileNotFoundError(
            f"Scene not found: {scenario.scene_path}. Run `make fetch-assets` first."
        )

    model = mujoco.MjModel.from_xml_path(str(scenario.scene_path))
    data = mujoco.MjData(model)

    # Start from the Panda "home" keyframe and hold there.
    home_key = _name2id(model, mujoco.mjtObj.mjOBJ_KEY, "home")
    mujoco.mj_resetDataKeyframe(model, data, home_key)

    traj = build_trajectory(scenario.trajectory)
    data.ctrl[:] = traj.control_at(0.0)

    hand_id = _name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hand")
    human_site_id = None
    if scenario.clearance and "human_zone_1" in scenario.clearance.obstacle_zones:
        human_site_id = _name2id(model, mujoco.mjtObj.mjOBJ_SITE, "human_zone_1")

    dt = model.opt.timestep
    total_steps = int(np.ceil(traj.duration / dt))
    log_every = max(1, int(round(1.0 / (CONTROL_LOG_HZ * dt))))
    render_every = max(1, int(round(1.0 / (RENDER_FPS * dt))))

    log_t, log_qpos, log_qvel, log_ctrl = [], [], [], []
    log_tcp, log_ncon, log_tcp_human = [], [], []
    frames: dict[str, list[np.ndarray]] = {cam: [] for cam in scenario.cameras}

    renderer = None
    if scenario.render.get("mujoco", False) and scenario.cameras:
        renderer = mujoco.Renderer(model, height=RENDER_H, width=RENDER_W)

    min_tcp_human = float("inf")
    max_contacts = 0
    try:
        for step in range(total_steps):
            t = step * dt
            data.ctrl[:] = traj.control_at(t)
            mujoco.mj_step(model, data)

            tcp = data.xpos[hand_id].copy()
            tcp_human = float("inf")
            if human_site_id is not None:
                tcp_human = float(np.linalg.norm(tcp - data.site_xpos[human_site_id]))
                min_tcp_human = min(min_tcp_human, tcp_human)
            max_contacts = max(max_contacts, int(data.ncon))

            if step % log_every == 0:
                log_t.append(t)
                log_qpos.append(data.qpos.copy())
                log_qvel.append(data.qvel.copy())
                log_ctrl.append(data.ctrl.copy())
                log_tcp.append(tcp)
                log_ncon.append(int(data.ncon))
                log_tcp_human.append(tcp_human)

            if renderer is not None and step % render_every == 0:
                for cam in scenario.cameras:
                    renderer.update_scene(data, camera=cam)
                    frames[cam].append(renderer.render().copy())
    finally:
        if renderer is not None:
            renderer.close()

    # --- write artifacts (outputs/ is gitignored) ---
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = outputs_root / scenario.id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    states_path = run_dir / "states.npz"
    np.savez_compressed(
        states_path,
        t=np.array(log_t),
        qpos=np.array(log_qpos),
        qvel=np.array(log_qvel),
        ctrl=np.array(log_ctrl),
        tcp=np.array(log_tcp),
        ncon=np.array(log_ncon),
        tcp_to_human=np.array(log_tcp_human),
    )

    frame_paths: dict[str, Path] = {}
    for cam, imgs in frames.items():
        if not imgs:
            continue
        fp = run_dir / f"frames_{cam}.npz"
        np.savez_compressed(fp, frames=np.array(imgs, dtype=np.uint8), fps=RENDER_FPS)
        frame_paths[cam] = fp

    meta = {
        "scenario_id": scenario.id,
        "run_id": run_id,
        "robot": scenario.robot,
        "trajectory_type": scenario.trajectory.get("type"),
        "scene": str(scenario.scene_path.relative_to(REPO_ROOT)),
        "sim_duration_s": traj.duration,
        "timestep_s": dt,
        "cameras": scenario.cameras,
        "render_fps": RENDER_FPS,
        "render_size": [RENDER_H, RENDER_W],
        "signals": {
            "min_tcp_to_human_m": None if min_tcp_human == float("inf") else min_tcp_human,
            "max_contacts": max_contacts,
        },
        "git_commit": _git_commit(),
        "note": "Signals here are raw sim logs, NOT verdicts. Verdicts land in M3.",
    }
    meta_path = run_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    return RunArtifacts(
        run_id=run_id,
        run_dir=run_dir,
        states_path=states_path,
        meta_path=meta_path,
        frame_paths=frame_paths,
        sim_duration_s=traj.duration,
        min_tcp_to_human_m=min_tcp_human,
        max_contacts=max_contacts,
    )
