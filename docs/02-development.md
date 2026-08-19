# 02 — Development

Phase 2 of the `docs/` set. **Skeleton scaffolded at M0** — filled in as the
development milestones (M2–M6) land.

Planned contents:

- **Implementation notes per milestone** (M2 runner, M3 verifier, M4 render,
  M5 DROID bridge, M6 hero render + dashboard + deck).
- **The WSL2-vs-host GPU gotcha** — why MuJoCo renders headless in the container
  (EGL/OSMesa, CPU) while Blender OptiX runs natively on the Windows host, and
  the concrete setup steps for each.
- **Verified external facts** — the exact MuJoCo Menagerie Franka MJCF path/model
  name, and the DROID action-space mapping (confirmed against the dataset card,
  not assumed).
- **Smoke test** — running one scenario headless end-to-end on a tiny scene.

> _To be written during M2–M6._
