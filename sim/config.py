"""Load and merge scenario + safety config into a typed Scenario object.

M2 implementation. A scenario's per-criterion thresholds override the global
defaults in config/safety.yaml; anything a scenario omits inherits the default.
See brief §6.1 (scenario contract) and §6.2 (safety defaults).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Repo root = two levels up from this file (sim/config.py -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"
ASSETS_DIR = REPO_ROOT / "assets"
SAFETY_PATH = CONFIG_DIR / "safety.yaml"


@dataclass(frozen=True)
class ReachCriterion:
    workspace_margin_m: float


@dataclass(frozen=True)
class CycleTimeCriterion:
    max_s: float


@dataclass(frozen=True)
class ClearanceCriterion:
    obstacle_zones: list[str]
    min_distance_m: float


@dataclass(frozen=True)
class Scenario:
    """A fully-resolved scenario (defaults merged in)."""

    id: str
    robot: str
    scene_path: Path
    trajectory: dict
    reach: ReachCriterion | None
    cycle_time: CycleTimeCriterion | None
    clearance: ClearanceCriterion | None
    render: dict
    on_any_fail: str
    cameras: list[str] = field(default_factory=list)


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping at the top of {path}, got {type(data)}")
    return data


def load_safety_defaults(path: Path = SAFETY_PATH) -> dict:
    """Return the merged {defaults, verdict} from config/safety.yaml."""
    data = _load_yaml(path)
    return {
        "defaults": data.get("defaults", {}),
        "verdict": data.get("verdict", {"on_any_fail": "FAIL"}),
    }


def load_scenario(scenario_path: str | Path, safety_path: Path = SAFETY_PATH) -> Scenario:
    """Load a scenario YAML and resolve its criteria against safety defaults."""
    scenario_path = Path(scenario_path)
    raw = _load_yaml(scenario_path)
    safety = load_safety_defaults(safety_path)
    defaults = safety["defaults"]
    criteria = raw.get("criteria", {}) or {}

    reach = None
    if "reach" in criteria:
        rc = criteria["reach"] or {}
        reach = ReachCriterion(
            workspace_margin_m=float(
                rc.get("workspace_margin_m", defaults.get("reach_workspace_margin_m"))
            )
        )

    cycle_time = None
    if "cycle_time" in criteria:
        cc = criteria["cycle_time"] or {}
        cycle_time = CycleTimeCriterion(
            max_s=float(cc.get("max_s", defaults.get("cycle_time_max_s")))
        )

    clearance = None
    if "clearance" in criteria:
        cl = criteria["clearance"] or {}
        clearance = ClearanceCriterion(
            obstacle_zones=list(cl.get("obstacle_zones", [])),
            min_distance_m=float(
                cl.get("min_distance_m", defaults.get("min_human_clearance_m"))
            ),
        )

    render = raw.get("render", {}) or {}
    # Scene path in the YAML is relative to assets/ (e.g. "cells/single_arm_cell.xml").
    scene_path = ASSETS_DIR / raw["scene"]

    return Scenario(
        id=raw["id"],
        robot=raw["robot"],
        scene_path=scene_path,
        trajectory=raw.get("trajectory", {}) or {},
        reach=reach,
        cycle_time=cycle_time,
        clearance=clearance,
        render=render,
        on_any_fail=str(safety["verdict"].get("on_any_fail", "FAIL")),
        cameras=list(render.get("cameras", [])),
    )
