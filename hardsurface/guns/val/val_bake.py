"""Bake the VAL's base / ORM / normal maps.  Self-contained (runs on the render farm or locally).

  blender --background work/val_prebake.blend --python val_bake.py -- <outdir> [bake_res=4096] [samples=48] [out_res=2048]
"""
import os
import sys
import time

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
OUT = a[0]
BAKE_RES = int(a[1]) if len(a) > 1 else 4096
SAMPLES = int(a[2]) if len(a) > 2 else 48
OUT_RES = int(a[3]) if len(a) > 3 else 2048
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
except Exception as e:  # noqa
    print("gpu setup failed", e)
print("VALBAKE device", dev)
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = False
sc.cycles.use_adaptive_sampling = False
sc.view_settings.view_transform = "Standard"
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
bpy.context.view_layer.objects.active = ob
for o in sc.objects:
    o.select_set(o is ob)


def set_pass(m, pass_name, image):
    nt = m.node_tree
    gn, out, em, bs, tg = (nt.nodes[k] for k in ("G", "OUT", "EM", "BS", "TARGET"))
    for l in list(out.inputs[0].links):
        nt.links.remove(l)
    for l in list(em.inputs[0].links):
        nt.links.remove(l)
    if pass_name == "normal":
        nt.links.new(bs.outputs[0], out.inputs[0])
    else:
        nt.links.new(gn.outputs["Base" if pass_name == "base" else "ORM"], em.inputs[0])
        nt.links.new(em.outputs[0], out.inputs[0])
    tg.image = image
    for nd in nt.nodes:
        nd.select = False
    tg.select = True
    nt.nodes.active = tg


for pass_name, kind, colorspace in (("base", "EMIT", "sRGB"), ("orm", "EMIT", "Non-Color"), ("normal", "NORMAL", "Non-Color")):
    t0 = time.time()
    img = bpy.data.images.new("bake_" + pass_name, BAKE_RES, BAKE_RES, alpha=False)
    img.colorspace_settings.name = colorspace
    for m in me.materials:
        set_pass(m, pass_name, img)
    sc.render.bake.margin = max(4, BAKE_RES // 256)
    sc.render.bake.use_clear = True
    if kind == "NORMAL":
        sc.render.bake.normal_space = "TANGENT"
    bpy.ops.object.bake(type=kind)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(BAKE_RES, BAKE_RES, 4)
    k = BAKE_RES // OUT_RES
    if k > 1:
        px = px.reshape(OUT_RES, k, OUT_RES, k, 4).mean(axis=(1, 3))
    if pass_name == "normal":
        n = px[:, :, :3] * 2 - 1
        n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6)
        px[:, :, :3] = n * 0.5 + 0.5
    px[:, :, 3] = 1
    res = px.shape[0]
    out = bpy.data.images.new("val_%s" % pass_name, res, res, alpha=False)
    out.colorspace_settings.name = colorspace
    out.pixels.foreach_set(px.ravel())
    out.filepath_raw = os.path.join(OUT, "val_%s.png" % pass_name)
    out.file_format = "PNG"
    out.save()
    print("VALBAKE", pass_name, res, "%.1fs" % (time.time() - t0))
print("VALBAKE DONE")
