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

**M0 — scaffold + conception.** Repository structure, docs phase 1, and the
architecture diagram are in place. Simulation, verification, and rendering logic
are **not** implemented yet (they begin at M2). Module files are placeholders.

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
├── docker-compose.yml            # MuJoCo (headless) side — placeholder until M2
├── Makefile                      # up / fetch-assets / scenarios / verify / render / report / demo
├── .env.example                  # copy to .env
├── .gitignore                    # excludes outputs/ and fetched assets
├── requirements.txt              # placeholder; pinned as milestones land
├── config/
│   ├── scenarios/                # one YAML per scenario (defined at M1)
│   └── safety.yaml               # global thresholds (illustrative; set at M1)
├── assets/
│   ├── fetch_menagerie.py        # pulls specific Menagerie models; does NOT commit them
│   └── cells/                    # MJCF work-cell scenes (arm + human/obstacle proxy)
├── sim/                          # MuJoCo scenario runner + trajectory sources
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
    └── architecture.md            # architecture diagram (Mermaid)
```

## Make targets

Recipes are **stubs at M0** and get wired up in the milestone shown.

| Target | Purpose | Milestone |
|---|---|---|
| `make up` | Build/start the MuJoCo container | M2 |
| `make fetch-assets` | Pull needed Menagerie models (uncommitted) | M2 |
| `make scenarios` | Run the v1 scenarios headless | M2 |
| `make verify` | Reach / cycle-time / clearance → sqlite catalog | M3 |
| `make render` | MuJoCo overlay MP4s (`HERO=1` → host Blender) | M4 / M6 |
| `make report` | Streamlit summary + assemble `deck/` | M6 |
| `make demo` | End-to-end: fetch → scenarios → verify → render | M6 |

---

## Assets & licenses

Every fetched asset's license is recorded here (populated as assets are pulled in
M2). Menagerie models are **per-model licensed**; nothing is committed to git —
`assets/fetch_menagerie.py` pulls them into a gitignored path.

| Asset | Source | Version / rev | License | Used in |
|---|---|---|---|---|
| Franka Panda (MJCF) | MuJoCo Menagerie | _TBD (verify at M2)_ | _TBD (per-model)_ | primary robot |
| DROID episode(s) | DROID / LeRobot | _TBD (M5)_ | CC-BY 4.0 | `droid_replay` scenario |
| _(more as added)_ | | | | |

> The table is intentionally stubbed at M0. It must be filled with **verified**
> model names, paths, revisions, and licenses before those assets are used — not
> guessed.

---

## Hardware target

Windows 11 + WSL2 (Ubuntu); NVIDIA RTX 2000 Ada Laptop, 8 GB VRAM; ~500 GB local
disk. The headless MuJoCo path needs no GPU; only the optional host-side Blender
hero render uses the RTX card.
