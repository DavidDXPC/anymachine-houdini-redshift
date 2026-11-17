"""Bake the SVD texture set from svd_prebake.blend.  Runs on the bake farm or locally.

  blender --background <svd_prebake.blend> --python svd_bake.py -- --out <dir> [--res 4096] [--samples 48]

Writes svd_base.png, svd_normal.png, svd_orm.png at half the bake resolution.
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detail_shader as ds  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:]


def arg(k, d):
    return a[a.index(k) + 1] if k in a else d


OUT = arg("--out", ".")
RES = int(arg("--res", "4096"))
SAMPLES = int(arg("--samples", "48"))
OUT_RES = RES // 2
os.makedirs(OUT, exist_ok=True)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
dev = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == kind
                sc.cycles.device = "GPU"
                dev = kind
                break
        except Exception:
            continue
except Exception as e:
    print("gpu setup failed", e)
print("SVD bake device", dev, "res", RES, "samples", SAMPLES)
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = False
sc.cycles.use_adaptive_sampling = False
sc.view_settings.view_transform = "Standard"

ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
bpy.context.view_layer.objects.active = ob
for o in bpy.data.objects:
    o.select_set(o is ob)
mats = [m for m in me.materials]
for pass_name, kind, colorspace in (("base", "EMIT", "sRGB"), ("orm", "EMIT", "Non-Color"), ("normal", "NORMAL", "Non-Color")):
    img = bpy.data.images.new("bake_" + pass_name, RES, RES, alpha=False)
    img.colorspace_settings.name = colorspace
    for m in mats:
        ds.set_pass(m, pass_name, img)
    sc.render.bake.margin = max(4, RES // 256)
    sc.render.bake.use_clear = True
    if kind == "NORMAL":
        sc.render.bake.normal_space = "TANGENT"
    bpy.ops.object.bake(type=kind)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)
    px = px.reshape(OUT_RES, 2, OUT_RES, 2, 4).mean(axis=(1, 3))
    if pass_name == "normal":
        n = px[:, :, :3] * 2 - 1
        n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6)
        px[:, :, :3] = n * 0.5 + 0.5
    px[:, :, 3] = 1
    out = bpy.data.images.new("svd_" + pass_name, OUT_RES, OUT_RES, alpha=False)
    out.colorspace_settings.name = colorspace
    out.pixels.foreach_set(px.ravel())
    out.filepath_raw = os.path.join(OUT, "svd_%s.png" % pass_name)
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(img)
    print("SVD baked", pass_name, OUT_RES)
print("SVD BAKE DONE")
