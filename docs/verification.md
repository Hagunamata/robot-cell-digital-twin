# Verification runbook

A **living checklist** for verifying each milestone end-to-end on the Ubuntu
target. It is written to be run *at the end* (or whenever you like): follow the
commands, compare against **Expected**, and we then tailor the expected values
to what the machine actually produces.

- **Where:** an Ubuntu (or any Linux) box with internet. No GPU needed for M2–M5.
- **Docker optional:** the `make` verbs call `python` directly, so a plain venv
  works. Docker is offered as an alternative, not a requirement.
- **Legend:** ✅ = must pass · 📌 = value to be tailored after the first real run.

> Expected numbers marked 📌 are provisional (derived from the code, not yet
> observed). Replace them with the real first-run values during verification.

---

## 0. Environment setup

**Native venv (recommended):**

```bash
sudo apt-get install -y libosmesa6 libgl1 libglx-mesa0 git
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MUJOCO_GL=osmesa          # CPU software GL; use egl only with a GPU+driver
```

**Docker alternative:**

```bash
make up                                        # docker compose build
docker compose run --rm twin make test         # run any verb inside the container
```

**Expected:** `pip install` completes; `python -c "import mujoco, numpy, yaml"`
prints nothing (no error). ✅

---

## M0 — scaffold + conception

```bash
ls README.md Makefile docker-compose.yml Dockerfile .gitignore .gitattributes
ls docs/                       # 01-conception, 02-development, 03-finalization, architecture, verification
ls config/scenarios/           # three scenario YAMLs
```

**Expected:** all files listed, no "No such file". The architecture diagram in
`docs/architecture.md` renders as a Mermaid graph on GitHub. ✅

---

## M1 — config contracts

```bash
python -m pytest tests/test_smoke.py -k config -q
```

**Expected:** 3 passed (`test_scenario_config_loads` for each scenario). Confirms
each scenario resolves reach=0.02 m, cycle_time=15.0 s, clearance=0.30 m with
`human_zone_1`, verdict FAIL-on-any. ✅

---

## M2 — Menagerie fetch + headless MuJoCo runner

### 2a. Fetch the Franka model

```bash
make fetch-assets
cat assets/menagerie.lock.json
ls assets/menagerie/franka_emika_panda/panda.xml
```

**Expected:**
- Console shows `resolved main -> <40-char sha>` and `license=Apache-2.0`. ✅
- `assets/menagerie.lock.json` exists (committed) with `"ref": "<sha>"` and
  `"license": "Apache-2.0"`. ✅
- `assets/menagerie/franka_emika_panda/panda.xml` exists (gitignored). ✅

### 2b. Smoke test (scene loads + short headless run)

```bash
make test
```

**Expected:** all tests pass — the 3 config tests **plus**
`test_scripted_run_produces_log` (which now runs, since assets are present) →
**4 passed**. Confirms `assets/cells/single_arm_cell.xml` loads with the fetched
meshes (the cross-directory `meshdir` fix works) and the step/log loop runs. ✅

### 2c. Run each scenario headless

```bash
make scenarios SCEN=cycle_time_pickplace
make scenarios SCEN=human_clearance_pickplace
# droid_replay_reach_check is expected to ERROR until M5 (see below)
```

**Expected console (per run):**
```
[run] scenario=cycle_time_pickplace robot=franka_panda trajectory=scripted
[run] done in 11.50 s sim time          # 📌 pick_place duration
[run]   run_dir     : outputs/cycle_time_pickplace/<timestamp>
[run]   states      : states.npz
[run]   frames[front]: frames_front.npz
[run]   frames[side] : frames_side.npz
...
```
- `cycle_time_pickplace` → `sim_duration ≈ 11.5 s`. 📌 ✅
- `human_clearance_pickplace` → `sim_duration ≈ 10.0 s`; prints a finite
  `min TCP→human` value (this scenario swings toward the proxy, so it should be
  the **smallest** of the runs). 📌 ✅
- `droid_replay_reach_check` → **raises `NotImplementedError`** ("implemented by
  the M5 droid_bridge"). This is the correct M2 behavior, not a failure. ✅

### 2d. Inspect the artifacts

```bash
RUN=$(ls -td outputs/cycle_time_pickplace/*/ | head -1)
cat "$RUN/meta.json"
python -c "import numpy as np; d=np.load('$RUN/states.npz'); print({k:v.shape for k,v in d.items()})"
python -c "import numpy as np; d=np.load('$RUN/frames_front.npz'); print('frames', d['frames'].shape, d['frames'].dtype)"
```

**Expected:**
- `meta.json`: `scenario_id`, `trajectory_type: scripted`, `sim_duration_s ≈ 11.5`,
  `git_commit` set, `signals.max_contacts` an integer, note that signals are raw
  (not verdicts). ✅
- `states.npz` shapes (timestep-dependent, 📌): `t (~575,)`, `qpos (~575, 9)`,
  `qvel (~575, 9)`, `ctrl (~575, 8)`, `tcp (~575, 3)`, `ncon (~575,)`,
  `tcp_to_human (~575,)`. ✅
- `frames_front.npz`: `frames (~172, 240, 320, 3) uint8`. 📌 ✅

### 2e. (Optional) eyeball a rendered frame

```bash
python -c "import numpy as np, imageio.v2 as iio; d=np.load('$RUN/frames_front.npz'); iio.imwrite('/tmp/front.png', d['frames'][len(d['frames'])//2])"
```

**Expected:** `/tmp/front.png` shows the Panda in the work-cell with the floor,
the orange workpiece, and the translucent red `human_zone_1` box. ✅ (This is the
visual we'll add verdict/metric overlays onto in M4.)

### M2 pass criteria (summary)

- [ ] `make fetch-assets` writes the lockfile + Apache-2.0 license
- [ ] `make test` → 4 passed
- [ ] both scripted scenarios run and write `states.npz` + `frames_*.npz` + `meta.json`
- [ ] `droid_replay_reach_check` cleanly raises NotImplementedError (M5)
- [ ] a rendered frame looks correct
- [ ] `git status` shows nothing under `outputs/` or `assets/menagerie/` staged
      (both gitignored)

---

## M3 — verifier (reach / cycle-time / clearance → catalog)

The verifier reads an existing run's sim log (states.npz + meta.json) — it does
**not** re-simulate — computes the three checks, prints a verdict, and appends a
row to the sqlite catalog. Reach envelope + thresholds are **illustrative**.

### 3a. Unit checks (no mujoco needed)

```bash
python -m pytest tests/test_verify.py -k "reach or cycle or clearance" -q
```

**Expected:** 3 passed (`check_reach`, `check_cycle_time`, `check_clearance`). ✅

### 3b. Verify a run and write the catalog

```bash
make scenarios SCEN=cycle_time_pickplace     # produce a run first (if not already)
make verify    SCEN=cycle_time_pickplace
```

**Expected console:**
```
[verify] scenario=cycle_time_pickplace run=<ts> dir=outputs/cycle_time_pickplace/<ts>
[verify]   PASS  reach       max TCP reach 0.xxx m ≤ 0.835 m ...
[verify]   PASS  cycle_time  cycle time 11.50 s ≤ 15.00 s
[verify]   PASS  clearance   min clearance 0.xxx m ≥ 0.30 m
[verify] VERDICT: PASS                      # 📌 confirm against real metrics
[verify] wrote catalog row -> outputs/catalog.sqlite
```
- `cycle_time_pickplace` → expected **PASS** (all three). 📌
- `human_clearance_pickplace` → the arm swings toward `human_zone_1`, so the
  **clearance** check is the interesting one and may report **FAIL** by design
  (this is the breach we highlight in the M4 overlay). Verdict then = FAIL. 📌 ✅

### 3c. Inspect the catalog

```bash
sqlite3 outputs/catalog.sqlite \
  "SELECT scenario_id, verdict, reach_ok, round(cycle_time_s,2), round(min_clearance_m,3) FROM scenario_runs;"
```

**Expected:** one row per `make verify` call, with verdict + metrics + a JSON
`asset_licenses` (e.g. `{"franka_emika_panda": "Apache-2.0"}`). `clip_path` /
`hero_clip_path` are NULL until M4 / M6. ✅

### M3 pass criteria (summary)

- [ ] `tests/test_verify.py` unit checks pass
- [ ] `make verify SCEN=cycle_time_pickplace` prints a verdict and writes a row
- [ ] the catalog holds the expected metrics; `asset_licenses` carries Apache-2.0
- [ ] `human_clearance_pickplace` verdict matches its measured clearance
      (tailor the threshold if the by-design breach doesn't trigger)

## M4 — overlay MP4

Draws the verdict/metrics banner onto the M2 frames, highlights per-frame
clearance breaches (red border + "CLEARANCE BREACH"), and encodes an MP4 per
camera into the run dir. Overlay uses Pillow; encode uses imageio-ffmpeg.

### 4a. Overlay unit + encode test (no mujoco/assets)

```bash
python -m pytest tests/test_render.py -q
```

**Expected:** 2 passed — `draw_overlay_frame` returns a same-shape uint8 image,
and `render_clips` writes a non-empty `clip_front.mp4` (with a FAIL verdict from
the synthetic clearance dip). ✅

### 4b. Render a real run

```bash
make scenarios SCEN=human_clearance_pickplace
make verify    SCEN=human_clearance_pickplace     # creates the catalog row
make render    SCEN=human_clearance_pickplace
```

**Expected console:**
```
[render] scenario=human_clearance_pickplace run=<ts> verdict=<PASS|FAIL>
[render]   clip[front] -> outputs/human_clearance_pickplace/<ts>/clip_front.mp4
[render]   clip[side]  -> outputs/human_clearance_pickplace/<ts>/clip_side.mp4
[render] catalog clip_path updated for run <ts>
```

**Expected artifacts:**
- `clip_front.mp4` / `clip_side.mp4` play and show the banner
  (`human_clearance_pickplace [VERDICT]`) with the three metric lines. ✅
- If the clearance check fails, the frames where the TCP is inside 0.30 m show a
  **red border + "CLEARANCE BREACH"**. 📌 (confirm the breach frames line up with
  the arm nearest the red zone)
- The catalog row's `clip_path` now points at the front clip:
  ```bash
  sqlite3 outputs/catalog.sqlite "SELECT scenario_id, verdict, clip_path FROM scenario_runs;"
  ```

### M4 pass criteria (summary)

- [ ] `tests/test_render.py` → 2 passed
- [ ] `make render` writes playable `clip_<cam>.mp4` with a legible overlay
- [ ] breach highlight appears when/where clearance < threshold
- [ ] catalog `clip_path` is populated after render
- [ ] the overlay text is readable at 240×320 (bump render size in `sim/runner.py`
      if not — a value to tailor)

## M5 — DROID replay bridge  _[pending]_

## M6 — Blender hero render (host GPU) + Streamlit + deck  _[pending]_

## M7 — finalization  _[pending]_
