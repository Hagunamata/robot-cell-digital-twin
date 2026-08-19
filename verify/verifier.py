"""Aggregate the per-criterion checks for one run into a verdict.

M3 implementation. Consumes a run directory produced by the M2 runner
(states.npz + meta.json) plus the resolved Scenario, runs the applicable
checks, and returns a Verdict. A scenario passes only if ALL its applicable
checks pass (verdict.on_any_fail = FAIL).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sim.config import Scenario
from verify.checks import CheckResult, check_clearance, check_cycle_time, check_reach


@dataclass(frozen=True)
class Verdict:
    scenario_id: str
    run_id: str
    verdict: str                     # PASS | FAIL
    checks: list[CheckResult]
    reach_ok: bool | None
    cycle_time_s: float | None
    min_clearance_m: float | None


def latest_run_dir(outputs_root: Path, scenario_id: str) -> Path:
    """Return the most recent run directory for a scenario."""
    base = outputs_root / scenario_id
    runs = sorted((p for p in base.glob("*/") if p.is_dir()))
    if not runs:
        raise FileNotFoundError(
            f"No runs found under {base}. Run `make scenarios SCEN={scenario_id}` first."
        )
    return runs[-1]


def verify_run(scenario: Scenario, run_dir: Path) -> Verdict:
    """Run all applicable checks for one scenario run and return a Verdict."""
    states = np.load(run_dir / "states.npz")
    meta = json.loads((run_dir / "meta.json").read_text())

    checks: list[CheckResult] = []
    reach_ok: bool | None = None
    cycle_time_s: float | None = None
    min_clearance_m: float | None = None

    if scenario.reach is not None:
        r = check_reach(states["tcp"], scenario.reach.workspace_margin_m)
        checks.append(r)
        reach_ok = r.ok

    if scenario.cycle_time is not None:
        c = check_cycle_time(states["t"], scenario.cycle_time.max_s)
        checks.append(c)
        cycle_time_s = c.metric

    if scenario.clearance is not None:
        cl = check_clearance(states["tcp_to_human"], scenario.clearance.min_distance_m)
        checks.append(cl)
        min_clearance_m = cl.metric

    passed = all(c.ok for c in checks) if checks else False
    verdict = "PASS" if passed else scenario.on_any_fail  # FAIL on any failing check

    return Verdict(
        scenario_id=scenario.id,
        run_id=meta.get("run_id", run_dir.name),
        verdict=verdict,
        checks=checks,
        reach_ok=reach_ok,
        cycle_time_s=cycle_time_s,
        min_clearance_m=min_clearance_m,
    )
