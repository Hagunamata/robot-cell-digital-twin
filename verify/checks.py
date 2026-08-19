"""Verification checks: reach envelope, cycle time, human clearance.

Placeholder module (M0 scaffold — no logic yet). To be implemented in M3.

Planned checks (each returns a pass/fail + measured metric):
    - reach     : TCP stays inside the reachable envelope by workspace_margin_m.
    - cycle_time: run duration <= max_s.
    - clearance : min arm-to-obstacle distance >= min_distance_m.

A scenario passes only if all criteria pass (verdict.on_any_fail = FAIL).
Threshold values are ILLUSTRATIVE — see config/safety.yaml.
"""

from __future__ import annotations


def verify(*args, **kwargs):
    """Evaluate all criteria for a scenario run. Not yet implemented."""
    raise NotImplementedError("verify.checks.verify is implemented in M3")
