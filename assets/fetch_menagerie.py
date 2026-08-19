"""Fetch specific MuJoCo Menagerie models (does NOT commit them to git).

Placeholder module (M0 scaffold — no logic yet). To be implemented in M2.

Planned responsibility:
    - Pull only the specific Menagerie models needed (primary: Franka Panda)
      into assets/ (gitignored), pinned to a known revision.
    - Record each fetched model's license so the README asset table stays true.

Do NOT invent Menagerie model names or MJCF paths — verify exact paths
against the real MuJoCo Menagerie repository before wiring them up.
"""

from __future__ import annotations


def main() -> None:
    """CLI entry point for `make fetch-assets`. Not yet implemented."""
    raise NotImplementedError("assets.fetch_menagerie is implemented in M2")


if __name__ == "__main__":
    main()
