# Architecture diagram

Data flow of the scenario verifier, from human-owned config to the deck clips.
The two shaded lanes make the **execution-environment split** explicit: the
default path runs **headless inside WSL2/Docker** (CPU, no GPU), while the
photoreal hero render runs **natively on the Windows host** to use the RTX card.

> Offline scenario verifier — **not** a live, bidirectionally-synced digital
> twin. See [01-conception.md](01-conception.md) for the honest scope note.

```mermaid
flowchart TD
    %% ---------------- Inputs (human-owned) ----------------
    subgraph CFG["Config — human owns these"]
        SCEN["config/scenarios/*.yaml"]
        SAFE["config/safety.yaml<br/>(illustrative thresholds)"]
    end

    %% ---------------- Default path: WSL2 / Docker ----------------
    subgraph WSL["Default path — headless in WSL2 / Docker (CPU, no GPU)"]
        direction TB
        RUN["Scenario runner<br/>(MuJoCo + Menagerie assets)"]

        subgraph TRAJ["Trajectory source"]
            TSCRIPT["scripted"]
            TIK["ik_waypoints"]
            TDROID["droid_replay"]
        end
        BRIDGE["droid_bridge<br/>maps a DROID episode<br/>onto the MuJoCo Franka"]

        STEP["Physics step loop<br/>(states, contacts, camera frames)"]
        LOG["Sim log<br/>(TCP path, clearances, timings, frames)"]

        VERIFY["Verifier → verdict + metrics<br/>reach envelope · cycle time · human clearance"]

        CAT[("Results catalog<br/>(sqlite)")]
        RMUJOCO["MuJoCo native render + overlay → MP4<br/>(default clip per scenario)"]
        DASH["Streamlit summary<br/>(reads the catalog)"]
    end

    %% ---------------- Host path: Windows + RTX ----------------
    subgraph HOST["Host-side step — Windows + RTX (separate, optional)"]
        RBLENDER["Blender OptiX 'hero' render<br/>(2–3 chosen deck clips)"]
    end

    DECK["deck/<br/>hero clips + slide outline"]

    %% ---------------- Edges ----------------
    SCEN --> RUN
    SAFE --> VERIFY
    RUN --> TRAJ
    RUN --> STEP
    TDROID --- BRIDGE
    BRIDGE --> STEP
    STEP --> LOG
    LOG --> VERIFY
    VERIFY --> CAT
    VERIFY --> RMUJOCO
    CAT --> DASH
    RMUJOCO --> DECK
    LOG -. "export scene + keyframes" .-> RBLENDER
    RBLENDER --> DECK

    %% ---------------- Styling ----------------
    classDef wsl fill:#e8f0fe,stroke:#4285f4,color:#000;
    classDef host fill:#fce8e6,stroke:#ea4335,color:#000;
    classDef cfg fill:#e6f4ea,stroke:#34a853,color:#000;
    class RUN,TSCRIPT,TIK,TDROID,BRIDGE,STEP,LOG,VERIFY,CAT,RMUJOCO,DASH wsl;
    class RBLENDER host;
    class SCEN,SAFE cfg;
```

**Legend**

- 🟩 Green — human-owned config (scenarios + illustrative safety thresholds).
- 🟦 Blue — the default, CPU-only path that runs headless in WSL2/Docker.
- 🟥 Red — the optional host-side Blender step that uses the RTX card.

**Excluded by design:** Isaac Sim (below the 8 GB laptop-GPU line — documented
future work only). Orchestration is a simple CLI + Makefile, **not** Airflow —
see [01-conception.md](01-conception.md) for the rationale.
