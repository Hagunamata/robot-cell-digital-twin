"""Export scene + keyframes and OptiX-render a hero clip (host-run).

Placeholder module (M0 scaffold — no logic yet). To be implemented in M6.

Planned responsibility:
    - Export the chosen scenario's scene + keyframes from the sim.
    - Render photoreal frames with Blender Cycles + OptiX on the Windows host.
    - Collect the result into deck/ for the slide deck.

Run this on the Windows host (RTX card), e.g. `make render HERO=1` or a
host-side invocation — never inside the WSL2/Docker container.
"""

from __future__ import annotations
