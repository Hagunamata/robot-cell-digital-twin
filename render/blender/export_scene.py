"""Export a run's per-frame geometry + camera for the Blender hero render.

M6 — runs HEADLESS in WSL2/Docker (needs mujoco + fetched assets). It replays a
run's logged joint trajectory (states.npz `qpos`) through `mj_forward`, and for
each visual mesh geom records its world pose per frame, plus the camera pose.
The output (`manifest.json` + `transforms.npz`) is consumed by the host-side
`hero_render.py` — decoupling Blender from MuJoCo kinematics: Blender just plays
back recorded rigid-body transforms on the fetched meshes.

    python -m render.blender.export_scene --scenario config/scenarios/<id>.yaml \
        [--camera front] [--fps 24] [--max-frames 300] [--out <dir>]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np

from sim.config import REPO_ROOT, SAFETY_PATH, load_scenario
from verify.verifier import latest_run_dir

FRANKA_ASSETS = REPO_ROOT / "assets" / "menagerie" / "franka_emika_panda" / "assets"


def _visual_mesh_geoms(model: mujoco.MjModel) -> list[int]:
    """Mesh geoms, preferring the visual group (2); fall back to all mesh geoms."""
    mesh = [g for g in range(model.ngeom)
            if model.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH]
    visual = [g for g in mesh if int(model.geom_group[g]) == 2]
    return visual or mesh


def _mesh_file(mesh_name: str) -> Path | None:
    for ext in (".obj", ".OBJ", ".stl", ".STL"):
        p = FRANKA_ASSETS / f"{mesh_name}{ext}"
        if p.exists():
            return p
    return None


def _resample_indices(t: np.ndarray, fps: float, max_frames: int) -> np.ndarray:
    """Indices of `t` nearest to a uniform `fps` grid, capped at max_frames."""
    if t.size == 0:
        return np.array([], dtype=int)
    grid = np.arange(0.0, float(t[-1]) + 1e-9, 1.0 / fps)
    idx = np.clip(np.searchsorted(t, grid), 0, len(t) - 1)
    idx = np.unique(idx)
    if len(idx) > max_frames:
        idx = idx[np.linspace(0, len(idx) - 1, max_frames).round().astype(int)]
    return idx


def export(scenario, run_dir: Path, out_dir: Path, camera: str, fps: float,
           max_frames: int) -> Path:
    model = mujoco.MjModel.from_xml_path(str(scenario.scene_path))
    data = mujoco.MjData(model)

    states = np.load(run_dir / "states.npz")
    qpos_all, t = states["qpos"], states["t"]
    idx = _resample_indices(t, fps, max_frames)
    qpos = qpos_all[idx]
    n = len(qpos)

    geoms = _visual_mesh_geoms(model)
    geom_meta = []
    for gid in geoms:
        mesh_id = int(model.geom_dataid[gid])
        mesh_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH, mesh_id)
        f = _mesh_file(mesh_name)
        geom_meta.append({
            "geom_name": mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid),
            "mesh_name": mesh_name,
            "mesh_file": str(f.relative_to(REPO_ROOT)) if f else None,
            "rgba": [float(x) for x in model.geom_rgba[gid]],
        })

    pos = np.zeros((n, len(geoms), 3), dtype=np.float32)
    quat = np.zeros((n, len(geoms), 4), dtype=np.float32)   # (w, x, y, z)
    for i in range(n):
        data.qpos[:] = qpos[i]
        data.qvel[:] = 0.0
        mujoco.mj_forward(model, data)
        for j, gid in enumerate(geoms):
            pos[i, j] = data.geom_xpos[gid]
            q = np.zeros(4)
            mujoco.mju_mat2Quat(q, data.geom_xmat[gid])
            quat[i, j] = q

    cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, camera)
    if cam_id < 0:
        raise KeyError(f"camera {camera!r} not found in scene")
    camera_info = {
        "name": camera,
        "pos": [float(x) for x in data.cam_xpos[cam_id]],
        "mat": [float(x) for x in data.cam_xmat[cam_id]],   # 9, world axes of cam frame
        "fovy_deg": float(model.cam_fovy[cam_id]),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_dir / "transforms.npz", pos=pos, quat=quat)
    manifest = {
        "scenario_id": scenario.id,
        "run_id": run_dir.name,
        "n_frames": n,
        "fps": fps,
        "camera": camera_info,
        "geoms": geom_meta,
        "note": "quat is (w,x,y,z); poses are world-frame per mesh geom.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a run for Blender hero render (M6).")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--safety", default=str(SAFETY_PATH))
    parser.add_argument("--outputs", default=str(REPO_ROOT / "outputs"))
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--camera", default="front")
    parser.add_argument("--fps", type=float, default=24.0)
    parser.add_argument("--max-frames", type=int, default=300)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    scenario = load_scenario(args.scenario, safety_path=Path(args.safety))
    outputs_root = Path(args.outputs)
    run_dir = Path(args.run_dir) if args.run_dir else latest_run_dir(outputs_root, scenario.id)
    out_dir = Path(args.out) if args.out else run_dir / "blender_export"

    export(scenario, run_dir, out_dir, args.camera, args.fps, args.max_frames)
    print(f"[export] wrote {out_dir}/manifest.json + transforms.npz")
    print(f"[export] next (on the Windows host with the RTX card):")
    print(f'[export]   blender --background --python render/blender/hero_render.py -- '
          f'--export "{out_dir}" --out "{run_dir}/hero_{args.camera}.mp4"')


if __name__ == "__main__":
    main()
