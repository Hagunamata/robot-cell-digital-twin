# Robot-Cell Digital Twin — Scenario Verifier

> **Scope (read this):** This is a **simulation-based scenario verifier in a
> digital-twin *style*** — **not** a live, bidirectionally-synced industrial
> digital twin. It runs **offline**: scenarios in, simulated runs out, automatic
> pass/fail verdicts and **annotated MP4 clips** as the headline deliverable. The
> "twin" label describes the style (a virtual work-cell used to check scenarios),
> not live hardware synchronization. See
> [docs/01-conception.md](docs/01-conception.md) for the full framing.

Define operational scenarios for a robot work-cell, simulate them in MuJoCo,
verify pass/fail criteria (**reach envelope · cycle time · human-robot
clearance**), and render overlaid video clips of each result for a slide deck.

**Portfolio context.** Third project in a lifecycle arc: **(1)** dark-factory
data platform → **(2)** robot-learning data engine (DROID/LeRobot) → **(3)** this
scenario verifier. The bridge to Project 2: one scenario **replays a curated DROID
episode on the same Franka Panda** inside the twin.

> ⚠️ **Safety thresholds are ILLUSTRATIVE** portfolio-demo values. ISO 10218 and
> ISO/TS 15066 are the real collaborative-robot standards; nothing here is a claim
> of certified compliance.

---

## Status

**M3 — verifier + sqlite catalog.** Each run's sim log is scored on reach
envelope, cycle time, and human clearance → a PASS/FAIL verdict + metrics,
appended to the sqlite catalog. `make verify` works. Overlay MP4 (M4) and the
DROID bridge (M5) are not implemented yet.

**Run it** (on the WSL2/Docker target):

```bash
make up                                   # build the headless image
make fetch-assets                         # pull the Franka model (+ lockfile)
make scenarios SCEN=cycle_time_pickplace  # run one scenario headless
make verify    SCEN=cycle_time_pickplace  # score it -> verdict + catalog row
make test                                 # smoke + verify tests
```

**v1 scenarios** (defined at M1; illustrative thresholds):

| Scenario | Trajectory | Focus criterion |
|---|---|---|
| `droid_replay_reach_check` | `droid_replay` (lerobot/droid_100 → Franka) | reach envelope |
| `cycle_time_pickplace` | `scripted` (pick_place) | cycle time |
| `human_clearance_pickplace` | `scripted` (pick_place_near_human) | human clearance |

Global thresholds (`config/safety.yaml`, **illustrative** — not certified
compliance): cycle-time ≤ 15.0 s · min human clearance 0.30 m · reach margin
0.02 m · a scenario passes only if all criteria pass. Dashboard: **Streamlit**.

Prior: **M2** — headless MuJoCo runner (states/contacts/frames). **M1** — config
contracts. **M0** — scaffold + conception (repo structure, docs, architecture).

---

## Architecture

See **[docs/architecture.md](docs/architecture.md)** for the diagram and
**[docs/01-conception.md](docs/01-conception.md)** for the rationale.

- **Primary engine — MuJoCo (headless, CPU):** simulation logic + baseline
  annotated clips, run headless in **WSL2/Docker** (EGL/OSMesa, no GPU).
- **Hero clips — Blender (Cycles + OptiX):** 2–3 photoreal deck shots rendered
  **natively on the Windows host** to use the RTX card (a separate, optional step
  — not in the container).
- **Isaac Sim — excluded** (below the 8 GB laptop-GPU line; future work only).
- **Orchestration — simple CLI + Makefile**, deliberately **not** Airflow (see
  conception doc for why right-sizing is the correct call).

<a name="repository-layout"></a>

## Repository layout

```
robot-cell-digital-twin/
├── README.md                     # this file (asset+license table, twin-scope note)
├── Dockerfile                    # headless MuJoCo image (OSMesa, CPU)
├── docker-compose.yml            # MuJoCo (headless) side
├── Makefile                      # up / fetch-assets / scenarios / test / verify / render / report / demo
├── pyproject.toml                # pytest config
├── .env.example                  # copy to .env
├── .gitignore                    # excludes outputs/ and fetched assets
├── requirements.txt              # mujoco, numpy, pyyaml, imageio, pytest
├── config/
│   ├── scenarios/                # one YAML per scenario (defined at M1)
│   └── safety.yaml               # global thresholds (illustrative; set at M1)
├── assets/
│   ├── fetch_menagerie.py        # sparse-fetches Menagerie models; does NOT commit them
│   ├── menagerie.lock.json       # committed pin: resolved SHA + license (written by fetch)
│   └── cells/single_arm_cell.xml # MJCF work-cell scene (Franka + human_zone_1 + cameras)
├── sim/                          # MuJoCo runner (runner.py, trajectories.py, config.py, run.py)
├── tests/                        # headless smoke test
├── droid_bridge/                 # map a DROID episode onto the MuJoCo Franka
├── verify/                       # reach / cycle-time / clearance checks -> verdicts
├── render/
│   ├── mujoco/                   # headless frames + overlay -> mp4 (default)
│   └── blender/                  # export scene+keyframes; OptiX render (host-run)
├── catalog/                      # sqlite schema + writer
├── dashboard/                    # Streamlit summary reading the catalog
├── deck/                         # exported hero clips + slide outline
├── outputs/                      # gitignored: clips, renders, sim logs
├── sample_scenario/              # one committed tiny scenario + one sample frame
└── docs/
    ├── 01-conception.md          # architecture, engine choice, twin-scope, why-not-Airflow/Isaac
    ├── 02-development.md          # implementation notes + WSL2-vs-host GPU gotcha
    ├── 03-finalization.md         # reflection + roadmap
    ├── architecture.md            # architecture diagram (Mermaid)
    └── verification.md            # per-milestone run + expected-result checklist
```

## Make targets

| Target | Purpose | Status |
|---|---|---|
| `make up` | Build the headless MuJoCo image | ✅ M2 |
| `make fetch-assets` | Pull needed Menagerie models (uncommitted) | ✅ M2 |
| `make scenarios` | Run one scenario headless (`SCEN=<id>`) | ✅ M2 |
| `make test` | Headless smoke test | ✅ M2 |
| `make verify` | Reach / cycle-time / clearance → sqlite catalog (`SCEN=<id>`) | ✅ M3 |
| `make render` | MuJoCo overlay MP4s (`HERO=1` → host Blender) | stub → M4 / M6 |
| `make report` | Streamlit summary + assemble `deck/` | stub → M6 |
| `make demo` | End-to-end: fetch → scenarios → verify → render | stub → M6 |

---

## Assets & licenses

Every fetched asset's license is recorded here (populated as assets are pulled in
M2). Menagerie models are **per-model licensed**; nothing is committed to git —
`assets/fetch_menagerie.py` pulls them into a gitignored path.

| Asset | Source | Version / rev | License | Used in |
|---|---|---|---|---|
| Franka Emika Panda (`franka_emika_panda/panda.xml`) | [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) | pinned SHA in `assets/menagerie.lock.json` | **Apache-2.0** | primary robot |
| DROID episode(s) | DROID / LeRobot (`lerobot/droid_100`) | _TBD (M5)_ | CC-BY 4.0 | `droid_replay` scenario |

> The Franka license (Apache-2.0) and exact model path were **verified** against
> the Menagerie repo at M2. The DROID row firms up at M5 once the episode is
> pinned. `fetch_menagerie.py` writes the resolved SHA + license into the
> committed lockfile.

---

## Hardware target

Windows 11 + WSL2 (Ubuntu); NVIDIA RTX 2000 Ada Laptop, 8 GB VRAM; ~500 GB local
disk. The headless MuJoCo path needs no GPU; only the optional host-side Blender
hero render uses the RTX card.
