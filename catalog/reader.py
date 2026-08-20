"""Read helpers for the results catalog (used by the dashboard and deck builder).

M6. Keeps read access in one place so the Streamlit summary and the deck
assembler agree on what a "row" looks like.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from catalog.writer import COLUMNS


def read_runs(db_path: Path) -> list[dict]:
    """Return all catalog rows as dicts (newest first). Empty list if no db."""
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM scenario_runs ORDER BY created_at DESC"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def latest_per_scenario(db_path: Path) -> list[dict]:
    """One row per scenario_id — the most recent run of each (by created_at)."""
    seen: dict[str, dict] = {}
    for row in read_runs(db_path):        # already newest-first
        seen.setdefault(row["scenario_id"], row)
    return list(seen.values())
