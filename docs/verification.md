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

## M3 — verifier (reach / cycle-time / clearance → catalog)  _[pending]_

_Commands + expected verdicts/metrics to be added when M3 lands._

## M4 — overlay MP4  _[pending]_

## M5 — DROID replay bridge  _[pending]_

## M6 — Blender hero render (host GPU) + Streamlit + deck  _[pending]_

## M7 — finalization  _[pending]_
