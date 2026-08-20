"""Verification checks: reach envelope, cycle time, human clearance.

M3 implementation. Each check is a pure function over the M2 sim log arrays and
returns a CheckResult (pass/fail + the measured metric + the threshold). The
verifier (verify/verifier.py) aggregates them into a verdict.

NOTE: thresholds and the reach-envelope radius are ILLUSTRATIVE for a portfolio
demo — not a claim of ISO 10218 / ISO/TS 15066 certified compliance.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Illustrative nominal maximum reach of the Franka Panda TCP from its base
# (~0.86 m). Used only to demonstrate an envelope check; not a certified value.
# Tailored from 0.855 -> 0.86 during M3 verification: the Panda HOME pose already
# places the TCP at ~0.8351 m, so the old limit (0.855 - 0.02 margin = 0.835 m)
# was breached by 0.148 mm at t=0 — a false FAIL before any motion. See
# docs/verification.md §3b.
FRANKA_MAX_REACH_M = 0.86

# Arm base mount point in world coordinates (panda link0 sits at the origin).
BASE_XYZ = np.array([0.0, 0.0, 0.0])


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    metric: float          # the measured value
    threshold: float       # the value it was compared against
    detail: str


def check_reach(tcp: np.ndarray, workspace_margin_m: float) -> CheckResult:
    """TCP must stay inside the reachable envelope by workspace_margin_m.

    Measures the max radial distance of the TCP from the base and requires it to
    stay below (max_reach - margin), i.e. the arm never over-extends to the edge
    of its envelope.
    """
    radial = np.linalg.norm(tcp - BASE_XYZ, axis=1)
    measured_max = float(radial.max())
    limit = FRANKA_MAX_REACH_M - workspace_margin_m
    ok = measured_max <= limit
    return CheckResult(
        name="reach",
        ok=ok,
        metric=measured_max,
        threshold=limit,
        detail=(f"max TCP reach {measured_max:.3f} m "
                f"{'≤' if ok else '>'} {limit:.3f} m "
                f"(max_reach {FRANKA_MAX_REACH_M} − margin {workspace_margin_m})"),
    )


def check_cycle_time(t: np.ndarray, max_s: float) -> CheckResult:
    """Run duration (last logged sim time) must be <= max_s."""
    measured = float(t[-1]) if t.size else 0.0
    ok = measured <= max_s
    return CheckResult(
        name="cycle_time",
        ok=ok,
        metric=measured,
        threshold=max_s,
        detail=f"cycle time {measured:.2f} s {'≤' if ok else '>'} {max_s:.2f} s",
    )


def check_clearance(tcp_to_human: np.ndarray, min_distance_m: float) -> CheckResult:
    """Minimum TCP-to-human-zone distance must be >= min_distance_m.

    Uses the TCP-to-zone distance logged in M2 (an illustrative proxy for full
    arm-to-human clearance).
    """
    finite = tcp_to_human[np.isfinite(tcp_to_human)]
    measured = float(finite.min()) if finite.size else float("inf")
    ok = measured >= min_distance_m
    return CheckResult(
        name="clearance",
        ok=ok,
        metric=measured,
        threshold=min_distance_m,
        detail=f"min clearance {measured:.3f} m {'≥' if ok else '<'} {min_distance_m:.2f} m",
    )
