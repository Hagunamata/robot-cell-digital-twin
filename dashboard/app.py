"""Streamlit summary app.

M6 implementation. Reads the sqlite results catalog and shows per-scenario
verdicts + metrics, embedding the overlay clip (and hero clip if present).

Run:  streamlit run dashboard/app.py
"""

from __future__ import annotations

from pathlib import Path

from catalog.reader import latest_per_scenario, read_runs
from sim.config import REPO_ROOT

DB_PATH = REPO_ROOT / "outputs" / "catalog.sqlite"


def _fmt(value: object, digits: int = 3) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "—"


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Robot-Cell Twin — Scenario Verifier", layout="wide")
    st.title("Robot-Cell Digital Twin — Scenario Verifier")
    st.caption(
        "Offline simulation + scenario verifier (digital-twin *style*), **not** a "
        "live-synced twin. Safety thresholds are ILLUSTRATIVE — not certified "
        "ISO 10218 / ISO/TS 15066 compliance."
    )

    runs = read_runs(DB_PATH)
    if not runs:
        st.warning(f"No runs in the catalog yet ({DB_PATH}). "
                   "Run `make scenarios`, `make verify`, `make render` first.")
        return

    latest = latest_per_scenario(DB_PATH)
    passed = sum(1 for r in latest if r["verdict"] == "PASS")
    c1, c2, c3 = st.columns(3)
    c1.metric("Scenarios", len(latest))
    c2.metric("PASS", passed)
    c3.metric("FAIL", len(latest) - passed)

    st.divider()
    for r in latest:
        verdict = r["verdict"]
        icon = "✅" if verdict == "PASS" else "❌"
        st.subheader(f"{icon} {r['scenario_id']} — {verdict}")
        m1, m2, m3 = st.columns(3)
        m1.metric("reach ok", str(r["reach_ok"]))
        m2.metric("cycle time (s)", _fmt(r["cycle_time_s"], 2))
        m3.metric("min clearance (m)", _fmt(r["min_clearance_m"], 3))

        for label, key in (("Overlay clip", "clip_path"), ("Hero clip", "hero_clip_path")):
            path = r.get(key)
            if path and Path(path).exists():
                st.caption(label)
                st.video(path)
        st.divider()

    with st.expander("All runs (raw catalog)"):
        st.dataframe(runs, use_container_width=True)


if __name__ == "__main__":
    main()
