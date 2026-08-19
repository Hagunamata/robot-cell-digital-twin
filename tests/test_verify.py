"""M3 tests: the checks (pure, no mujoco) and a run -> verify -> catalog pass.

The integration test needs mujoco + fetched assets; it self-skips otherwise.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from sim.config import REPO_ROOT, load_scenario
from verify.checks import check_clearance, check_cycle_time, check_reach

SCEN_DIR = REPO_ROOT / "config" / "scenarios"
FETCHED_PANDA = REPO_ROOT / "assets" / "menagerie" / "franka_emika_panda" / "panda.xml"


# --- pure check unit tests (always run) -------------------------------------

def test_check_reach() -> None:
    inside = np.array([[0.5, 0.0, 0.3], [0.4, 0.1, 0.4]])
    assert check_reach(inside, workspace_margin_m=0.02).ok
    overextended = np.array([[0.9, 0.0, 0.3]])           # radial ~0.949 > 0.835
    assert not check_reach(overextended, workspace_margin_m=0.02).ok


def test_check_cycle_time() -> None:
    t = np.linspace(0.0, 11.5, 100)
    assert check_cycle_time(t, max_s=15.0).ok
    assert not check_cycle_time(np.linspace(0.0, 20.0, 100), max_s=15.0).ok


def test_check_clearance() -> None:
    ok = check_clearance(np.array([0.6, 0.4, 0.35]), min_distance_m=0.30)
    assert ok.ok and ok.metric == pytest.approx(0.35)
    assert not check_clearance(np.array([0.6, 0.2]), min_distance_m=0.30).ok
    # infinities (no zone in view) are ignored when taking the min
    assert check_clearance(np.array([np.inf, 0.5]), min_distance_m=0.30).metric == pytest.approx(0.5)


# --- integration: run -> verify -> catalog ----------------------------------

def test_run_verify_catalog(tmp_path: Path) -> None:
    pytest.importorskip("mujoco")
    if not FETCHED_PANDA.exists():
        pytest.skip("Menagerie model not fetched — run `make fetch-assets` first")

    from sim.runner import run_scenario
    from verify.verifier import verify_run
    from catalog.writer import write_run

    scenario = load_scenario(SCEN_DIR / "human_clearance_pickplace.yaml")
    scenario = dataclasses.replace(scenario, render={}, cameras=[])

    artifacts = run_scenario(scenario, outputs_root=tmp_path)
    verdict = verify_run(scenario, artifacts.run_dir)

    assert verdict.verdict in {"PASS", "FAIL"}
    assert verdict.reach_ok is not None
    assert verdict.cycle_time_s is not None
    assert verdict.min_clearance_m is not None

    db_path = tmp_path / "catalog.sqlite"
    write_run(db_path, {
        "scenario_id": verdict.scenario_id,
        "run_id": verdict.run_id,
        "verdict": verdict.verdict,
        "reach_ok": verdict.reach_ok,
        "cycle_time_s": verdict.cycle_time_s,
        "min_clearance_m": verdict.min_clearance_m,
    })
    conn = sqlite3.connect(str(db_path))
    try:
        (count,) = conn.execute("SELECT COUNT(*) FROM scenario_runs").fetchone()
    finally:
        conn.close()
    assert count == 1
