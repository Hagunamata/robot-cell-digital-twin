# 02 — Development

Phase 2 of the `docs/` set. Implementation notes per milestone, plus the
verified external facts and the WSL2-vs-host GPU reality. Extended as each
milestone lands.

---

## M2 — Menagerie fetch + headless MuJoCo runner

**What M2 delivers:** load the Franka Panda into a work-cell scene, run a
scripted trajectory **headless**, and log states + contacts + camera frames.
`make scenarios SCEN=<id>` runs one. No verdicts yet — that is M3.

### Verified external facts (not invented)

Checked against the real `google-deepmind/mujoco_menagerie` repo before coding:

| Fact | Value |
|---|---|
| Model dir | `franka_emika_panda/` |
| Primary MJCF | `panda.xml` (`<mujoco model="panda">`) |
| Compiler | `<compiler angle="radian" meshdir="assets" autolimits="true"/>` |
| Hand | defined **inline** in `panda.xml` (no `hand.xml` include) |
| Actuators | 8 `<general>`: `actuator1..7` arm (ctrlrange ±2.8973 rad), `actuator8` gripper (ctrlrange **0..255**) |
| Joints | `joint1..7` + `finger_joint1/2` |
| Keyframe | `home`, qpos length 9: `0 0 0 -1.57079 0 1.57079 -0.7853 0.04 0.04` |
| End-effector | body `hand` — **no `<site>` elements exist**, so the runner uses the `hand` body frame as the TCP proxy |
| License | **Apache-2.0** |

Because the model defines **no TCP site**, `sim/runner.py` logs the `hand`
**body** world position as the TCP. If a precise tool-center offset is needed
later, add a fixed offset — do not assume a site that isn't there.

### The cross-directory asset-path gotcha (important)

MuJoCo resolves relative asset paths (`meshdir`/`texturedir`) **relative to the
top-level MJCF file's directory**, and multi-level/cross-directory includes are
fragile. Our work-cell scene lives in `assets/cells/` but includes the fetched
model in `assets/menagerie/`. The fix (per the MuJoCo docs guidance to specify
resource paths in the top file) is that `assets/cells/single_arm_cell.xml` sets:

```xml
<compiler ... meshdir="../menagerie/franka_emika_panda/assets"
              texturedir="../menagerie/franka_emika_panda/assets"/>
<include file="../menagerie/franka_emika_panda/panda.xml"/>
```

So the meshes resolve to the fetched model regardless of `panda.xml`'s own
`meshdir="assets"`. The smoke test loads this scene to confirm.

### Asset fetch + reproducibility

`assets/fetch_menagerie.py` does a **sparse** git checkout of only
`franka_emika_panda/`, copies it into `assets/menagerie/` (gitignored), and
writes **`assets/menagerie.lock.json`** (committed) recording the resolved
commit SHA + license. First run resolves `main` → a concrete SHA; commit the
lockfile and everyone thereafter fetches identical bytes. Override with
`MENAGERIE_REF=<sha>`.

### WSL2-vs-host GPU reality (the render split)

- **Default path — headless, CPU:** MuJoCo offscreen rendering uses
  **OSMesa software GL** (`MUJOCO_GL=osmesa`) so it runs in WSL2/Docker with **no
  GPU** and no display. This is what the Dockerfile and `docker-compose.yml` set.
- **EGL** (`MUJOCO_GL=egl`) is faster but needs a GPU + driver *inside* the
  container; we do **not** assume GPU passthrough into WSL2/Docker works, so it is
  opt-in, not the default.
- **Blender OptiX hero renders** (M6) run **natively on the Windows host** to use
  the RTX 2000 Ada card — never inside this container.

### Frame logging (M2) vs overlay MP4 (M4)

M2 renders `front`/`side` frames offscreen at a modest size/fps and stores them
compressed under `outputs/<scenario>/<run_id>/frames_<cam>.npz` alongside
`states.npz` and `meta.json` (all gitignored). The verdict/metric **overlay and
MP4 encoding** come in M4 — M2 deliberately stops at the raw frames.

### Run it (on the WSL2/Docker target)

```bash
make up                       # build the headless image
make fetch-assets             # pull the Franka model + write the lockfile
make scenarios SCEN=cycle_time_pickplace
make test                     # smoke test (skips the run part if assets absent)
```

Or from the host: `docker compose run --rm twin make scenarios SCEN=...`.

> Note: the sim runs on the Linux/WSL2/Docker target (final verification on
> Ubuntu). It is not exercised on the Windows host directly.

---

## M3+ — planned

- **M3** verifier: reach envelope, cycle-time, human clearance → verdict +
  metrics → sqlite catalog. (`min_tcp_to_human_m` in the M2 log is a raw signal,
  not yet the clearance verdict.)
- **M4** overlay MP4 with the verdict/metrics and highlighted breach.
- **M5** DROID replay bridge — verify the action-space mapping against the
  dataset card.
- **M6** Blender hero renders (host) + Streamlit summary + `deck/`.
