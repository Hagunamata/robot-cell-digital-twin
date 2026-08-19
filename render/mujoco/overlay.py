"""Frame overlay + MP4 encoding for the baseline MuJoCo video path.

M4 implementation. Reads the M2 frames (frames_<cam>.npz) and the M3 verdict,
draws a verdict/metrics banner, highlights per-frame clearance breaches, and
encodes an annotated MP4 per camera into the run directory.

Drawing uses Pillow (light-weight) instead of OpenCV; encoding uses
imageio + imageio-ffmpeg. Runs headless — no display, no GPU.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from sim.config import Scenario
from verify.verifier import Verdict

_LINE_H = 13
_PAD = 5


def _font() -> ImageFont.ImageFont:
    """A small bitmap font that is always available headless."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", 12)
    except OSError:
        return ImageFont.load_default()


def draw_overlay_frame(
    img: np.ndarray,
    header: str,
    header_rgb: tuple[int, int, int],
    metric_lines: list[tuple[str, tuple[int, int, int]]],
    breach: bool,
) -> np.ndarray:
    """Return `img` (H,W,3 uint8) with the banner + optional breach highlight."""
    base = Image.fromarray(img).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = base.size
    font = _font()

    band_h = _PAD + (1 + len(metric_lines)) * _LINE_H + _PAD
    draw.rectangle([0, 0, w, band_h], fill=(0, 0, 0, 160))

    draw.text((_PAD, _PAD), header, fill=(*header_rgb, 255), font=font)
    y = _PAD + _LINE_H
    for text, rgb in metric_lines:
        draw.text((_PAD, y), text, fill=(*rgb, 255), font=font)
        y += _LINE_H

    if breach:
        for i in range(5):  # thick red border
            draw.rectangle([i, i, w - 1 - i, h - 1 - i], outline=(255, 45, 45, 255))
        draw.text((_PAD, h - 16), "CLEARANCE BREACH", fill=(255, 70, 70, 255), font=font)

    return np.asarray(Image.alpha_composite(base, overlay).convert("RGB"))


def _cameras_in_run(run_dir: Path) -> list[str]:
    return sorted(p.stem.replace("frames_", "") for p in run_dir.glob("frames_*.npz"))


def render_clips(run_dir: Path, scenario: Scenario, verdict: Verdict) -> dict[str, Path]:
    """Annotate every camera's frames and encode one MP4 each. Returns {cam: path}."""
    import imageio.v2 as imageio

    states = np.load(run_dir / "states.npz")
    header_rgb = (0, 190, 0) if verdict.verdict == "PASS" else (225, 45, 45)
    header = f"{scenario.id}  [{verdict.verdict}]"

    metric_lines: list[tuple[str, tuple[int, int, int]]] = []
    for c in verdict.checks:
        rgb = (120, 235, 120) if c.ok else (255, 120, 120)
        metric_lines.append((f"{c.name}: {'OK' if c.ok else 'FAIL'}  {c.detail}", rgb))

    threshold = scenario.clearance.min_distance_m if scenario.clearance else None

    clips: dict[str, Path] = {}
    cameras = scenario.cameras or _cameras_in_run(run_dir)
    for cam in cameras:
        fp = run_dir / f"frames_{cam}.npz"
        if not fp.exists():
            continue
        npz = np.load(fp)
        frames = npz["frames"]
        fps = float(npz["fps"])

        if threshold is not None and "tcp_to_human" in states:
            frame_t = np.arange(len(frames)) / fps
            clearance = np.interp(frame_t, states["t"], states["tcp_to_human"])
            breach = clearance < threshold
        else:
            breach = np.zeros(len(frames), dtype=bool)

        annotated = [
            draw_overlay_frame(frames[i], header, header_rgb, metric_lines, bool(breach[i]))
            for i in range(len(frames))
        ]
        out = run_dir / f"clip_{cam}.mp4"
        imageio.mimwrite(out, annotated, fps=fps, codec="libx264", quality=8,
                         macro_block_size=16)
        clips[cam] = out

    return clips
