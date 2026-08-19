"""M4 tests: overlay drawing + MP4 encode on a synthetic run (no mujoco/assets).

Needs Pillow + imageio + imageio-ffmpeg; self-skips if the ffmpeg backend is
unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from sim.config import REPO_ROOT, load_scenario

SCEN_DIR = REPO_ROOT / "config" / "scenarios"


def _synthetic_run(run_dir: Path, n: int = 20, fps: int = 10) -> None:
    """Write states.npz + meta.json + frames_front.npz mimicking an M2 run."""
    run_dir.mkdir(parents=True, exist_ok=True)
    t = np.arange(n) / fps
    tcp = np.tile([0.4, 0.0, 0.3], (n, 1))            # radial ~0.5 m -> reach OK
    tcp_to_human = np.full(n, 0.5)
    tcp_to_human[8:13] = 0.2                            # dip below 0.30 -> breach + FAIL
    np.savez_compressed(run_dir / "states.npz", t=t, tcp=tcp, tcp_to_human=tcp_to_human)
    (run_dir / "meta.json").write_text(json.dumps({
        "run_id": run_dir.name, "robot": "franka_panda",
        "trajectory_type": "scripted", "git_commit": "test",
    }))
    frames = np.random.default_rng(0).integers(0, 255, (n, 48, 64, 3), dtype=np.uint8)
    np.savez_compressed(run_dir / "frames_front.npz", frames=frames, fps=fps)


def test_draw_overlay_frame_shape() -> None:
    pytest.importorskip("PIL")
    from render.mujoco.overlay import draw_overlay_frame
    img = np.zeros((48, 64, 3), dtype=np.uint8)
    out = draw_overlay_frame(img, "hdr", (0, 190, 0), [("reach: OK", (120, 235, 120))], breach=True)
    assert out.shape == img.shape and out.dtype == np.uint8


def test_render_clips_writes_mp4(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    pytest.importorskip("imageio")
    pytest.importorskip("imageio_ffmpeg")

    from render.mujoco.overlay import render_clips
    from verify.verifier import verify_run

    scenario = load_scenario(SCEN_DIR / "human_clearance_pickplace.yaml")
    run_dir = tmp_path / scenario.id / "test-run"
    _synthetic_run(run_dir)

    verdict = verify_run(scenario, run_dir)
    assert verdict.verdict == "FAIL"          # clearance dip forces FAIL

    clips = render_clips(run_dir, scenario, verdict)
    assert "front" in clips
    mp4 = clips["front"]
    assert mp4.exists() and mp4.stat().st_size > 1000
