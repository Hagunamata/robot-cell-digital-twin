"""CLI entry point: run a single scenario headless and write its sim log.

    python -m sim.run --scenario config/scenarios/cycle_time_pickplace.yaml

Wired to `make scenarios SCEN=<id>`. M2 stops at the sim log; verification
(M3) and overlay rendering (M4) are separate steps.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sim.config import REPO_ROOT, SAFETY_PATH, load_scenario
from sim.runner import run_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one scenario headless (M2).")
    parser.add_argument("--scenario", required=True, help="path to a scenario YAML")
    parser.add_argument("--safety", default=str(SAFETY_PATH), help="path to safety.yaml")
    parser.add_argument(
        "--outputs", default=str(REPO_ROOT / "outputs"),
        help="root dir for run artifacts (gitignored)",
    )
    args = parser.parse_args()

    scenario = load_scenario(args.scenario, safety_path=Path(args.safety))
    print(f"[run] scenario={scenario.id} robot={scenario.robot} "
          f"trajectory={scenario.trajectory.get('type')}")

    artifacts = run_scenario(scenario, outputs_root=Path(args.outputs))

    print(f"[run] done in {artifacts.sim_duration_s:.2f} s sim time")
    print(f"[run]   run_dir     : {artifacts.run_dir}")
    print(f"[run]   states      : {artifacts.states_path.name}")
    for cam, fp in artifacts.frame_paths.items():
        print(f"[run]   frames[{cam}] : {fp.name}")
    if artifacts.min_tcp_to_human_m != float("inf"):
        print(f"[run]   min TCP→human (raw signal): {artifacts.min_tcp_to_human_m:.3f} m")
    print(f"[run]   max contacts (raw signal): {artifacts.max_contacts}")


if __name__ == "__main__":
    main()
