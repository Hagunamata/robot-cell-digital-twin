"""M6 tests: catalog reader, deck outline builder, and Blender export smoke.

The export smoke needs mujoco + fetched assets and self-skips otherwise; the
rest run anywhere (no mujoco, no streamlit, no blender).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from catalog.reader import latest_per_scenario, read_runs
from catalog.writer import write_run
from deck.build_deck import HERO_DEFAULT, build_outline
from sim.config import REPO_ROOT, load_scenario

FETCHED_PANDA = REPO_ROOT / "assets" / "menagerie" / "franka_emika_panda" / "panda.xml"


def test_reader_missing_db(tmp_path: Path) -> None:
    assert read_runs(tmp_path / "nope.sqlite") == []


def test_reader_and_latest_per_scenario(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite"
    write_run(db, {"scenario_id": "a", "run_id": "1", "verdict": "PASS",
                   "created_at": "2026-01-01T00:00:00"})
    write_run(db, {"scenario_id": "a", "run_id": "2", "verdict": "FAIL",
                   "created_at": "2026-01-02T00:00:00"})
    write_run(db, {"scenario_id": "b", "run_id": "3", "verdict": "PASS",
                   "created_at": "2026-01-01T00:00:00"})

    assert len(read_runs(db)) == 3
    latest = {r["scenario_id"]: r for r in latest_per_scenario(db)}
    assert set(latest) == {"a", "b"}
    assert latest["a"]["run_id"] == "2"          # newest run of scenario a


def test_build_outline_flags_hero_and_metrics() -> None:
    rows = [
        {"scenario_id": "droid_replay_reach_check", "verdict": "PASS", "reach_ok": True,
         "cycle_time_s": 13.58, "min_clearance_m": 0.505,
         "clip_path": "outputs/x/clip_front.mp4", "hero_clip_path": None},
        {"scenario_id": "cycle_time_pickplace", "verdict": "PASS", "reach_ok": True,
         "cycle_time_s": 11.5, "min_clearance_m": 0.40,
         "clip_path": None, "hero_clip_path": None},
    ]
    md = build_outline(rows, HERO_DEFAULT)
    assert "droid_replay_reach_check" in md
    assert "cycle_time_pickplace" in md
    assert "13.58" in md
    assert "hero clip" in md.lower()             # droid scenario is a hero


def test_build_outline_empty() -> None:
    assert "No catalog rows" in build_outline([], HERO_DEFAULT)


def test_export_scene_smoke(tmp_path: Path) -> None:
    pytest.importorskip("mujoco")
    if not FETCHED_PANDA.exists():
        pytest.skip("Menagerie model not fetched — run `make fetch-assets` first")

    from render.blender.export_scene import export

    scenario = load_scenario(REPO_ROOT / "config" / "scenarios" / "cycle_time_pickplace.yaml")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    n = 10
    home = np.array([0, 0, 0, -1.57079, 0, 1.57079, -0.7853, 0.04, 0.04])
    np.savez_compressed(
        run_dir / "states.npz",
        qpos=np.tile(home, (n, 1)), t=np.arange(n) / 50.0,
        tcp=np.zeros((n, 3)), tcp_to_human=np.full(n, 0.5),
    )

    out = export(scenario, run_dir, tmp_path / "bexport", camera="front",
                 fps=24.0, max_frames=50)
    assert (out / "manifest.json").exists() and (out / "transforms.npz").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["n_frames"] >= 1
    assert len(manifest["geoms"]) > 0
