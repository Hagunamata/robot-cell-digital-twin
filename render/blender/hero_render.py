"""Blender Cycles + OptiX photoreal "hero" render (Windows HOST, not the container).

M6 — consumes a `blender_export/` produced by render/blender/export_scene.py and
renders a photoreal clip with the RTX card. Runs under Blender's bundled Python:

    blender --background --python render/blender/hero_render.py -- \
        --export outputs/<scenario>/<run>/blender_export \
        --out    outputs/<scenario>/<run>/hero_front.mp4 \
        [--samples 64] [--resolution 1280 720]

Host-side ONLY: GPU passthrough into WSL2/Docker is not assumed, so this is a
deliberately separate optional step (see docs/02-development.md). Targets Blender
3.6–4.x; import operators + OptIX enabling differ across versions and are handled
defensively — expect to tweak per your Blender install (verify like the M5 loop).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy          # provided by Blender's Python; not a pip dependency
import numpy as np
from mathutils import Matrix, Quaternion, Vector


def _argv_after_ddash() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _import_mesh(path: Path):
    """Import an .obj/.stl and return the newly-added mesh object (version-tolerant)."""
    before = set(bpy.data.objects)
    ext = path.suffix.lower()
    if ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):          # Blender >= 4.0
            bpy.ops.wm.obj_import(filepath=str(path))
        else:                                          # Blender <= 3.x
            bpy.ops.import_scene.obj(filepath=str(path))
    elif ext == ".stl":
        if hasattr(bpy.ops.wm, "stl_import"):          # Blender >= 4.1
            bpy.ops.wm.stl_import(filepath=str(path))
        else:
            bpy.ops.import_mesh.stl(filepath=str(path))
    else:
        raise ValueError(f"unsupported mesh type: {path}")
    added = [o for o in bpy.data.objects if o not in before]
    # Join multiple parts into one object so keyframing is per-geom.
    if len(added) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in added:
            o.select_set(True)
        bpy.context.view_layer.objects.active = added[0]
        bpy.ops.object.join()
        added = [added[0]]
    return added[0]


def _enable_optix() -> str:
    """Enable the OptiX GPU backend if available; return the device type used."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dtype in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dtype
            prefs.get_devices()
            any_gpu = False
            for dev in prefs.devices:
                dev.use = dev.type in (dtype, "OPTIX", "CUDA")
                any_gpu = any_gpu or dev.use
            if any_gpu:
                scene.cycles.device = "GPU"
                return dtype
        except (TypeError, KeyError):
            continue
    scene.cycles.device = "CPU"
    return "CPU"


def _setup_camera(cam_info: dict) -> None:
    cam_data = bpy.data.cameras.new("hero_cam")
    cam_obj = bpy.data.objects.new("hero_cam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    m = cam_info["mat"]
    rot = Matrix(((m[0], m[1], m[2]), (m[3], m[4], m[5]), (m[6], m[7], m[8])))
    cam_obj.matrix_world = Matrix.Translation(Vector(cam_info["pos"])) @ rot.to_4x4()
    cam_data.sensor_fit = "VERTICAL"
    cam_data.angle_y = np.radians(cam_info["fovy_deg"])
    bpy.context.scene.camera = cam_obj


def _setup_world_and_ground() -> None:
    world = bpy.data.worlds.new("hero_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.06, 0.08, 1.0)
    bpy.context.scene.world = world

    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("sun", sun_data)
    sun.rotation_euler = (np.radians(50), 0.0, np.radians(30))
    bpy.context.collection.objects.link(sun)

    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0.3, 0.0, 0.0))
    ground = bpy.context.active_object
    mat = bpy.data.materials.new("ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.18, 0.19, 0.21, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.6
    ground.data.materials.append(mat)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", required=True, help="blender_export dir")
    parser.add_argument("--out", required=True, help="output .mp4 path")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--resolution", type=int, nargs=2, default=(1280, 720))
    args = parser.parse_args(_argv_after_ddash())

    export_dir = Path(args.export)
    repo_root = Path(__file__).resolve().parents[2]
    manifest = json.loads((export_dir / "manifest.json").read_text())
    tf = np.load(export_dir / "transforms.npz")
    pos, quat = tf["pos"], tf["quat"]           # (F,G,3), (F,G,4 wxyz)
    n_frames = manifest["n_frames"]

    _reset_scene()
    backend = _enable_optix()
    _setup_world_and_ground()
    _setup_camera(manifest["camera"])

    objects = []
    for j, g in enumerate(manifest["geoms"]):
        mesh_file = g.get("mesh_file")
        if not mesh_file:
            print(f"[hero] WARN no mesh file for geom {g.get('geom_name')}, skipping")
            objects.append(None)
            continue
        obj = _import_mesh(repo_root / mesh_file)
        obj.rotation_mode = "QUATERNION"
        objects.append(obj)

    for f in range(n_frames):
        for j, obj in enumerate(objects):
            if obj is None:
                continue
            obj.location = Vector([float(x) for x in pos[f, j]])
            obj.rotation_quaternion = Quaternion([float(x) for x in quat[f, j]])
            obj.keyframe_insert("location", frame=f)
            obj.keyframe_insert("rotation_quaternion", frame=f)

    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 0, max(0, n_frames - 1)
    scene.render.fps = int(round(manifest.get("fps", 24)))
    scene.render.resolution_x, scene.render.resolution_y = args.resolution
    scene.cycles.samples = args.samples
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.filepath = str(args.out)

    print(f"[hero] backend={backend} frames={n_frames} -> {args.out}")
    bpy.ops.render.render(animation=True)
    print("[hero] done")


if __name__ == "__main__":
    main()
