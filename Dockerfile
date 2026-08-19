# Headless MuJoCo image (CPU, no GPU) for the default WSL2/Docker path.
# Rendering uses OSMesa software GL so it works without a GPU/driver. Where a
# GPU is available you can instead set MUJOCO_GL=egl at run time.
#
# Blender hero rendering is NOT in this image — it runs natively on the Windows
# host (see render/blender/ and docs/02-development.md).

FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    MUJOCO_GL=osmesa \
    PYOPENGL_PLATFORM=osmesa

# git: used by assets/fetch_menagerie.py (sparse checkout).
# libosmesa6 + mesa GL: software offscreen rendering for MuJoCo.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        make \
        libosmesa6 \
        libgl1 \
        libglx-mesa0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["make", "help"]
