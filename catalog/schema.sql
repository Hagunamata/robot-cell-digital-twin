-- Results catalog schema (one row per scenario run).
-- Placeholder scaffolded at M0; wired up by the catalog writer in M3.
-- Mirrors §6.3 of CLAUDE_CODE_BRIEF_TWIN.md.

CREATE TABLE IF NOT EXISTS scenario_runs (
    scenario_id      TEXT,
    run_id           TEXT,
    robot            TEXT,
    trajectory_type  TEXT,
    verdict          TEXT,       -- PASS | FAIL
    reach_ok         BOOLEAN,
    cycle_time_s     NUMERIC,
    min_clearance_m  NUMERIC,
    clip_path        TEXT,
    hero_clip_path   TEXT,       -- nullable
    asset_licenses   TEXT,       -- json: model -> license
    created_at       TIMESTAMP,
    git_commit       TEXT,
    notes            TEXT
);
