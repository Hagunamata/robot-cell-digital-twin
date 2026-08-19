"""Headless MuJoCo render + overlay -> MP4 (default video path).

Placeholder package scaffolded at M0. Implementation lands in M4:
render frames headless (EGL/OSMesa), overlay the verdict/metrics and a
highlighted clearance breach with OpenCV/matplotlib, and encode an MP4
via imageio-ffmpeg. Runs inside WSL2/Docker — no GPU required.
"""
