"""Fetch specific MuJoCo Menagerie models into assets/menagerie/ (gitignored).

M2 implementation. Pulls ONLY the models we use (currently the Franka Panda)
via a sparse git checkout, records the exact resolved commit SHA and license in
a committed lockfile (assets/menagerie.lock.json), and never commits the model
files themselves.

Reproducibility: on the first run the ref (default "main", override with
MENAGERIE_REF) is resolved to a concrete SHA and written to the lockfile. Commit
that lockfile; subsequent runs pin to the locked SHA so everyone fetches the
same bytes.

Usage:
    python -m assets.fetch_menagerie            # fetch per lockfile (or resolve main)
    MENAGERIE_REF=<sha> python -m assets.fetch_menagerie   # force a ref

Verified facts (do not re-guess): the model lives at franka_emika_panda/ with
panda.xml (model "panda", <compiler meshdir="assets">), and its LICENSE is
Apache-2.0. See docs/02-development.md.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MENAGERIE_URL = "https://github.com/google-deepmind/mujoco_menagerie.git"

# Models this project uses: Menagerie subdir -> notes for the asset table.
MODELS: dict[str, dict[str, str]] = {
    "franka_emika_panda": {
        "robot": "franka_panda",
        "primary_mjcf": "panda.xml",
    },
}

ASSETS_DIR = Path(__file__).resolve().parent           # .../assets
DEST_DIR = ASSETS_DIR / "menagerie"                    # gitignored
LOCKFILE = ASSETS_DIR / "menagerie.lock.json"          # committed


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    """Run a subprocess, returning stripped stdout; raise on failure."""
    res = subprocess.run(
        cmd, cwd=cwd, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return res.stdout.strip()


def _read_license_name(license_path: Path) -> str:
    """Best-effort license identifier from a LICENSE file's first lines."""
    if not license_path.exists():
        return "UNKNOWN (LICENSE file missing)"
    head = license_path.read_text(errors="replace").splitlines()[:3]
    text = " ".join(line.strip() for line in head).lower()
    if "apache license" in text:
        return "Apache-2.0"
    if "mit license" in text:
        return "MIT"
    if "bsd" in text:
        return "BSD"
    return head[0].strip() if head else "UNKNOWN"


def _load_lock() -> dict:
    if LOCKFILE.exists():
        return json.loads(LOCKFILE.read_text())
    return {}


def fetch() -> dict:
    """Fetch the configured models; return the lock dict that was written."""
    lock = _load_lock()
    # Prefer an explicit env ref, then the locked SHA, then main.
    ref = os.environ.get("MENAGERIE_REF") or lock.get("ref") or "main"

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "menagerie"
        print(f"[fetch] cloning {MENAGERIE_URL} (sparse) ...", flush=True)
        _run([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            MENAGERIE_URL, str(tmp_path),
        ])
        _run(["git", "sparse-checkout", "init", "--cone"], cwd=tmp_path)
        _run(["git", "sparse-checkout", "set", *MODELS.keys()], cwd=tmp_path)
        _run(["git", "checkout", ref], cwd=tmp_path)
        sha = _run(["git", "rev-parse", "HEAD"], cwd=tmp_path)
        print(f"[fetch] resolved {ref} -> {sha}", flush=True)

        models_out: dict[str, dict[str, str]] = {}
        for subdir, meta in MODELS.items():
            src = tmp_path / subdir
            if not src.is_dir():
                raise FileNotFoundError(f"Menagerie subdir not found: {subdir}")
            dst = DEST_DIR / subdir
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            license_name = _read_license_name(src / "LICENSE")
            models_out[subdir] = {**meta, "license": license_name}
            print(f"[fetch] {subdir}: license={license_name} -> {dst}", flush=True)

    lock_out = {
        "source": MENAGERIE_URL,
        "ref": sha,               # pin the concrete SHA going forward
        "resolved_from": ref,
        "models": models_out,
    }
    LOCKFILE.write_text(json.dumps(lock_out, indent=2) + "\n")
    print(f"[fetch] wrote lockfile {LOCKFILE.name} (commit this).", flush=True)
    return lock_out


def main() -> None:
    """CLI entry point for `make fetch-assets`."""
    try:
        fetch()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[fetch] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
