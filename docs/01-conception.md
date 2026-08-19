# 01 — Conception

Phase 1 of the three-phase `docs/` set (conception → development → finalization),
mirroring the prior portfolio repos. This document fixes the architecture, the
engine choices, the honest scope of the "twin" label, and the deliberate
decisions *not* to reuse Airflow and *not* to depend on Isaac Sim.

---

## 1. What this project is (and is not)

This is a **simulation-based scenario verifier in a digital-twin *style***. You
define operational scenarios for a robot work-cell, simulate them, automatically
verify pass/fail criteria (reach envelope, cycle time, human-robot clearance),
and render **annotated video clips** of each result for a slide deck.

**Honest scope note — read this first.**
This is **NOT** a live, bidirectionally-synced industrial digital twin. There is
no real robot, no telemetry feed, and no closed control loop back to hardware. It
is an **offline simulation + scenario verifier**: config in, simulated runs out,
verdicts and MP4 clips as artifacts. The "digital-twin" framing describes the
*style* — a virtual model of a work-cell used to check scenarios before they are
trusted — not a claim of live synchronization. The project is deliberately
labelled this way so it reads as credible rather than overreaching. A true
live-sync twin is listed as future work in
[03-finalization.md](03-finalization.md).

**The headline deliverable is video.** Each scenario run produces an MP4 with an
overlay showing the verdict and metrics (e.g. `Reach: OK`,
`Cycle time: 11.4 s / 12.0 s`, a highlighted clearance breach). Those clips are
the assets for a PowerPoint; everything else exists to produce and justify them.

**Safety numbers are illustrative.** Thresholds (clearance, cycle time, reach
margin) are portfolio-demo values. ISO 10218 and ISO/TS 15066 are the real
collaborative-robot standards; nothing here is presented as certified compliance.

---

## 2. Where this sits in the portfolio

This is the **third** project in a lifecycle story:

1. **Project 1 — dark-factory data platform** (batch platform: Kafka, Spark,
   Airflow, Postgres, ELK, Docker Compose + Makefile). *Curate/stream factory data.*
2. **Project 2 — robot-learning data engine** (DROID/LeRobot: selective
   acquisition, storage-guard, batch validation, catalog, Streamlit). *Curate and
   validate robot-learning data.*
3. **This project — robot-cell digital twin (scenario verifier).** *Validate the
   deployment scenario in simulation before it is trusted.*

**The bridge to Project 2 is concrete:** DROID is Franka Panda data, and MuJoCo
Menagerie ships a Franka Panda. So one scenario **replays a curated DROID episode
trajectory in the twin on the same robot**, tying the three projects into one
arc: curate data → validate the deployment scenario → (future) monitor the fleet.

---

## 3. Architecture

Full diagram: **[architecture.md](architecture.md)** (Mermaid). Summary of the
flow:

```
config/scenarios/*.yaml  +  config/safety.yaml        (human owns these)
                    │
                    ▼
            Scenario runner  (MuJoCo + Menagerie assets)
                    │
     ┌──────────────┼───────────────────────────┐
     ▼              ▼                            ▼
 Trajectory     Physics step loop           Sim log
 source         (states, contacts,          (TCP path, clearances,
 scripted /     camera frames)              timings, frames)
 ik_waypoints /
 droid_replay ◄── droid_bridge  (maps a DROID episode onto the MuJoCo Franka)
                    │
                    ▼
             Verifier → verdict + metrics per scenario
       (reach envelope · cycle time · human clearance)
                    │
     ┌──────────────┴───────────────┐
     ▼                              ▼
 Results catalog (sqlite)       Rendering
     │                          ├── MuJoCo native + overlay → MP4  (WSL2/Docker, default)
     ▼                          └── Blender OptiX hero render      (Windows host, few clips)
 Streamlit summary                     │
     │                                 ▼
     └───────────────►  deck/  (hero clips + slide outline)
```

**Module map** (see [the repo layout](../README.md#repository-layout)):

| Stage | Module | Milestone |
|---|---|---|
| Fetch assets | `assets/fetch_menagerie.py` | M2 |
| Simulate | `sim/` (runner + trajectories) | M2 |
| DROID replay | `droid_bridge/` | M5 |
| Verify | `verify/` | M3 |
| Persist | `catalog/` (sqlite) | M3 |
| Render (default) | `render/mujoco/` | M4 |
| Render (hero) | `render/blender/` (host) | M6 |
| Summarize | `dashboard/` (Streamlit) | M6 |
| Package | `deck/` | M6 |

---

## 4. Engine choice

### 4.1 MuJoCo — the primary, headless engine

**MuJoCo is the primary engine** for both the simulation logic and the baseline
video. Rationale:

- **CPU-first and fast.** The verification logic (reach, cycle time, clearance)
  does not need a GPU. MuJoCo steps quickly on CPU, which suits a small batch of
  scenarios run repeatedly.
- **Headless-renderable.** MuJoCo renders offscreen via EGL/OSMesa, so it runs
  **headless inside WSL2/Docker and in CI** with no display and no GPU. This is
  the default path and the one the `make` verbs target.
- **Right-sized assets.** MuJoCo Menagerie provides a maintained, per-model
  licensed **Franka Panda**, which is exactly the robot that bridges to the
  Project-2 DROID data.

The baseline clip is produced entirely on this path: render frames headless,
overlay verdict/metrics with OpenCV/matplotlib, encode MP4 via imageio-ffmpeg.

### 4.2 Blender (Cycles + OptiX) — host-side hero clips only

For **2–3 chosen deck shots**, a photoreal "hero" render is produced with
**Blender Cycles + OptiX**. This runs **natively on the Windows host** to use the
RTX 2000 Ada card.

**Why host-side, not in the container:** GPU passthrough into WSL2/Docker is not
assumed to work on this hardware, so the supported render path is host-native
Blender. This keeps the container path CPU-only and reliable, and confines the
GPU dependency to a clearly separate, optional step (`make render HERO=1` or a
host-side invocation). The WSL2-vs-host GPU reality is documented in
[02-development.md](02-development.md).

### 4.3 Isaac Sim — excluded, and why

**Isaac Sim is deliberately excluded** as a dependency. The target machine has an
**8 GB laptop GPU (RTX 2000 Ada)**, which is below current Isaac Sim comfort
minimums. Making Isaac a dependency would make the project unrunnable on its own
target hardware. Isaac-based photoreal simulation is therefore recorded as
**future/optional work** in [03-finalization.md](03-finalization.md), not part of
v1.

### 4.4 Summary of the split

| Concern | Choice | Where it runs |
|---|---|---|
| Physics + verification logic | **MuJoCo** | Headless, WSL2/Docker (CPU) |
| Baseline annotated clips | **MuJoCo render + overlay** | Headless, WSL2/Docker (CPU) |
| Photoreal hero clips | **Blender Cycles + OptiX** | **Windows host** (RTX GPU) |
| Photoreal simulation | **Isaac Sim** | **Excluded** — future work only |

---

## 5. Deliberate decision: NOT reusing Airflow

Project 1 used **Airflow** to orchestrate a batch data platform. This project
**deliberately does not reuse it.** The orchestration here is a **simple CLI +
Makefile runner**.

**Why right-sizing away from Airflow is the correct call:**

- **Tiny, bounded batch.** v1 is a handful of scenarios run start-to-finish. There
  is no large DAG of interdependent tasks, no backfills, no schedules, no
  sensors — the workload Airflow exists to manage is absent.
- **Linear pipeline per scenario.** Each scenario is a straight line:
  fetch → simulate → verify → render → catalog. A `Makefile` (`fetch-assets`,
  `scenarios`, `verify`, `render`, `report`, `demo`) expresses this directly and
  is trivially reviewable.
- **Lower operational weight.** Airflow brings a scheduler, metadata database, and
  web server to babysit. For this scale that is pure overhead against the goal
  (produce annotated clips), and it would obscure rather than clarify the design.
- **Reproducibility without a scheduler.** `make demo` runs the whole thing
  headless and deterministically; that is the reproducibility guarantee, and it
  needs no orchestrator.

This is a **conscious contrast with Project 1**, not an oversight: the portfolio
point is choosing the right tool per problem scale. If the scenario matrix later
grew large or needed scheduling/retries/backfills, revisiting a DAG orchestrator
(Airflow or a lighter alternative) would be justified — noted as future work.

---

## 6. Reused vs. new (at a glance)

| Concern | Decision | Origin |
|---|---|---|
| Physics + sim | MuJoCo | **new** |
| Robot/scene assets | MuJoCo Menagerie (Franka Panda primary) | **new** |
| Baseline video | MuJoCo render + overlay (OpenCV, imageio-ffmpeg) | **new** |
| Photoreal hero clips | Blender (Cycles + OptiX), host-side | **new** |
| Isaac Sim | Excluded (below the 8 GB GPU line) | — |
| Trajectory sources | scripted / ik_waypoints / **droid_replay** | **new** |
| Orchestration | Simple CLI + Makefile (**not** Airflow) | right-sized |
| Results store | sqlite catalog | reuse pattern (Project 2) |
| Summary dashboard | Streamlit (confirm at M1) | reuse decision (Project 2) |
| Runtime | Docker Compose + Makefile (MuJoCo side) | reuse (Project 1) |

---

## 7. Constraints that shaped this design

- **Hardware:** Windows 11 + WSL2; NVIDIA RTX 2000 Ada Laptop, 8 GB VRAM →
  headless CPU path by default, GPU confined to host-side Blender.
- **No large binaries in git.** Renders, fetched assets, and sim logs live under
  `outputs/` (gitignored). Only code, config, docs, one tiny sample scenario, and
  one small sample frame are committed.
- **Licenses recorded.** Every used Menagerie model's license goes in the README
  asset table; the DROID basis is CC-BY 4.0.
- **Verify, don't invent.** MJCF paths, Menagerie model names, and the DROID
  action space are checked against the real repos/dataset cards before coding.

---

## 8. Open DECISION points (owned by the human)

Carried into **M1** and later milestones — not decided here:

- Which **3 scenarios** ship in v1 (recommended: one reach check, one cycle-time
  check, one human-clearance check — at least one a DROID replay).
- The **threshold values** in `config/safety.yaml` (and confirm they are labeled
  illustrative).
- Whether the **DROID replay bridge** is in v1 (recommended) or deferred.
- Which **2–3 clips** get the Blender hero treatment.
- **Confirm Streamlit** for the summary dashboard.

---

## 9. Status

**M0 (this milestone):** repo scaffolded per the brief, this conception document
written, architecture diagram produced. No simulation, verification, or rendering
logic yet — those begin at M2 after the M1 config contracts are fixed.
