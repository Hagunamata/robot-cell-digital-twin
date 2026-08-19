"""M2 smoke test: config loads for all scenarios; one scenario runs headless.

The run portion needs mujoco installed AND the Menagerie model fetched
(`make fetch-assets`); it self-skips otherwise so the suite is green on a fresh
checkout. Rendering is disabled here so no GL backend is required — the test
exercises the physics/step/log path end-to-end on the real scene.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from sim.config import REPO_ROOT, load_scenario

SCENARIO_IDS = [
    "droid_replay_reach_check",
    "cycle_time_pickplace",
    "human_clearance_pickplace",
]
SCEN_DIR = REPO_ROOT / "config" / "scenarios"
FETCHED_PANDA = REPO_ROOT / "assets" / "menagerie" / "franka_emika_panda" / "panda.xml"


@pytest.mark.parametrize("sid", SCENARIO_IDS)
def test_scenario_config_loads(sid: str) -> None:
    scenario = load_scenario(SCEN_DIR / f"{sid}.yaml")
    assert scenario.id == sid
    assert scenario.robot == "franka_panda"
    # Every v1 scenario declares all three criteria, resolved against defaults.
    assert scenario.reach is not None and scenario.reach.workspace_margin_m == 0.02
    assert scenario.cycle_time is not None and scenario.cycle_time.max_s == 15.0
    assert scenario.clearance is not None
    assert scenario.clearance.min_distance_m == 0.30
    assert "human_zone_1" in scenario.clearance.obstacle_zones
    assert scenario.on_any_fail == "FAIL"


def test_scripted_run_produces_log(tmp_path: Path) -> None:
    pytest.importorskip("mujoco")
    if not FETCHED_PANDA.exists():
        pytest.skip("Menagerie model not fetched — run `make fetch-assets` first")

    from sim.runner import run_scenario

    scenario = load_scenario(SCEN_DIR / "cycle_time_pickplace.yaml")
    # Disable rendering so no GL backend is needed for the smoke test.
    scenario = dataclasses.replace(scenario, render={}, cameras=[])

    artifacts = run_scenario(scenario, outputs_root=tmp_path)

    assert artifacts.states_path.exists()
    assert artifacts.meta_path.exists()
    assert artifacts.sim_duration_s > 0.0
