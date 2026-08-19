"""CLI entry point: render annotated overlay MP4s for a scenario run.

    python -m render.run --scenario config/scenarios/human_clearance_pickplace.yaml

Renders the latest run's frames with the verdict/metrics overlay + clearance
breach highlight, and best-effort updates the catalog row's clip_path. Wired to
`make render SCEN=<id>` (the non-HERO path; HERO=1 is the host-side Blender step
in M6).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sim.config import REPO_ROOT, SAFETY_PATH, load_scenario
from catalog.writer import update_clip_path
from render.mujoco.overlay import render_clips
from verify.verifier import latest_run_dir, verify_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Render overlay MP4s for a run (M4).")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--safety", default=str(SAFETY_PATH))
    parser.add_argument("--outputs", default=str(REPO_ROOT / "outputs"))
    parser.add_argument("--run-dir", default=None, help="specific run dir (default: latest)")
    parser.add_argument("--db", default=None, help="catalog path (default: outputs/catalog.sqlite)")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario, safety_path=Path(args.safety))
    outputs_root = Path(args.outputs)
    run_dir = Path(args.run_dir) if args.run_dir else latest_run_dir(outputs_root, scenario.id)
    db_path = Path(args.db) if args.db else outputs_root / "catalog.sqlite"

    verdict = verify_run(scenario, run_dir)
    print(f"[render] scenario={scenario.id} run={verdict.run_id} verdict={verdict.verdict}")

    clips = render_clips(run_dir, scenario, verdict)
    if not clips:
        print(f"[render] no frames found in {run_dir} — was the run rendered "
              f"(render.mujoco true, cameras set)?")
        return

    for cam, path in clips.items():
        print(f"[render]   clip[{cam}] -> {path}")

    # Prefer 'front' as the catalog clip; else the first produced.
    primary = clips.get("front") or next(iter(clips.values()))
    updated = update_clip_path(db_path, scenario.id, verdict.run_id, str(primary))
    if updated:
        print(f"[render] catalog clip_path updated for run {verdict.run_id}")
    else:
        print("[render] no catalog row updated (run `make verify` first to create one)")


if __name__ == "__main__":
    main()
