"""Catalog writer: persist one row per scenario run into sqlite.

M3 implementation. Applies catalog/schema.sql (idempotent) and inserts a row
matching brief §6.3.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

COLUMNS = [
    "scenario_id", "run_id", "robot", "trajectory_type", "verdict",
    "reach_ok", "cycle_time_s", "min_clearance_m", "clip_path", "hero_clip_path",
    "asset_licenses", "created_at", "git_commit", "notes",
]


def ensure_db(db_path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the catalog db and apply the schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def write_run(db_path: Path, row: dict) -> None:
    """Insert one scenario-run row. Missing keys are stored as NULL."""
    values = [row.get(col) for col in COLUMNS]
    placeholders = ", ".join("?" for _ in COLUMNS)
    conn = ensure_db(db_path)
    try:
        with conn:
            conn.execute(
                f"INSERT INTO scenario_runs ({', '.join(COLUMNS)}) VALUES ({placeholders})",
                values,
            )
    finally:
        conn.close()


def update_clip_path(db_path: Path, scenario_id: str, run_id: str, clip_path: str) -> int:
    """Set clip_path on matching rows. Returns the number of rows updated (0 if none)."""
    if not db_path.exists():
        return 0
    conn = ensure_db(db_path)
    try:
        with conn:
            cur = conn.execute(
                "UPDATE scenario_runs SET clip_path = ? WHERE scenario_id = ? AND run_id = ?",
                (clip_path, scenario_id, run_id),
            )
            return cur.rowcount
    finally:
        conn.close()
