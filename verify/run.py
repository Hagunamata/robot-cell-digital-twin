"""CLI entry point: verify a scenario run and write the catalog row.

    python -m verify.run --scenario config/scenarios/cycle_time_pickplace.yaml

By default it verifies the most recent run of that scenario under outputs/.
Wired to `make verify SCEN=<id>`.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from sim.config import REPO_ROOT, SAFETY_PATH, load_scenario
from catalog.writer import write_run
from verify.verifier import latest_run_dir, verify_run


def _asset_licenses() -> str:
    """JSON {model -> license} from the fetch lockfile (empty if not fetched)."""
    lock = REPO_ROOT / "assets" / "menagerie.lock.json"
    if lock.exists():
        data = json.loads(lock.read_text())
        return json.dumps({m: meta.get("license") for m, meta in data.get("models", {}).items()})
    return json.dumps({})


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a scenario run (M3).")
    parser.add_argument("--scenario", required=True, help="path to a scenario YAML")
    parser.add_argument("--safety", default=str(SAFETY_PATH))
    parser.add_argument("--outputs", default=str(REPO_ROOT / "outputs"))
    parser.add_argument("--run-dir", default=None, help="specific run dir (default: latest)")
    parser.add_argument("--db", default=None, help="sqlite catalog path (default: outputs/catalog.sqlite)")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario, safety_path=Path(args.safety))
    outputs_root = Path(args.outputs)
    run_dir = Path(args.run_dir) if args.run_dir else latest_run_dir(outputs_root, scenario.id)
    db_path = Path(args.db) if args.db else outputs_root / "catalog.sqlite"

    verdict = verify_run(scenario, run_dir)
    meta = json.loads((run_dir / "meta.json").read_text())

    print(f"[verify] scenario={verdict.scenario_id} run={verdict.run_id} dir={run_dir}")
    for c in verdict.checks:
        print(f"[verify]   {'PASS' if c.ok else 'FAIL'}  {c.name:<11} {c.detail}")
    print(f"[verify] VERDICT: {verdict.verdict}")

    row = {
        "scenario_id": verdict.scenario_id,
        "run_id": verdict.run_id,
        "robot": meta.get("robot"),
        "trajectory_type": meta.get("trajectory_type"),
        "verdict": verdict.verdict,
        "reach_ok": verdict.reach_ok,
        "cycle_time_s": verdict.cycle_time_s,
        "min_clearance_m": verdict.min_clearance_m,
        "clip_path": None,          # filled by the M4 renderer
        "hero_clip_path": None,     # filled by the M6 Blender step
        "asset_licenses": _asset_licenses(),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_commit": meta.get("git_commit"),
        "notes": None,
    }
    write_run(db_path, row)
    print(f"[verify] wrote catalog row -> {db_path}")


if __name__ == "__main__":
    main()
