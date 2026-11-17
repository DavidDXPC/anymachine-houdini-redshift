"""Per-mechanism close-up renders of an SVD file (source FBX or detailed GLB).
  blender --background --python svd_closeups.py -- <in> <outdir> <tag> [grey|pbr] [samples] [only,names]
grey: flat light-grey clay look (input for the image model).  pbr: the file's own materials in the studio.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detail_common as dc  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT, TAG = a[0], a[1], a[2]
LOOK = a[3] if len(a) > 3 else "grey"
SAMPLES = int(a[4]) if len(a) > 4 else 48
ONLY = a[5].split(",") if len(a) > 5 else None
os.makedirs(OUT, exist_ok=True)

# name: (target, camera offset from target, lens)   world metres, muzzle -Y, up +Z, gun's right side is -X
CAMS = {
    "receiver_r": ((0, 0.00, -0.012), (-0.30, -0.10, 0.10), 50),
    "receiver_l": ((0, 0.00, -0.012), (0.30, -0.08, 0.10), 50),
    "bolt": ((-0.02, -0.075, 0.0), (-0.17, -0.07, 0.10), 50),
    "magazine": ((0, -0.055, -0.065), (-0.21, -0.13, -0.03), 50),
    "safety": ((-0.02, 0.035, -0.025), (-0.17, 0.06, 0.04), 50),
    "stock": ((0, 0.25, -0.04), (0.42, 0.18, 0.12), 50),
    "handguard": ((0, -0.28, 0.0), (0.30, -0.14, 0.12), 50),
    "gasblock": ((0, -0.47, 0.012), (0.17, -0.09, 0.09), 50),
    "frontsight": ((0, -0.765, 0.012), (0.15, -0.11, 0.07), 50),
    "stock_r": ((0, 0.27, -0.06), (-0.36, 0.26, 0.10), 50),
    "butt": ((0, 0.38, -0.07), (0.16, 0.26, 0.05), 50),
    "rearsight": ((0, -0.165, 0.02), (0.11, 0.12, 0.09), 50),
}

dc.reset()
dc.load(SRC, flat=(LOOK == "grey"))
dc.use_cycles(SAMPLES)
if LOOK == "grey":
    for m in bpy.data.materials:
        b = m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
        if b:
            col = b.inputs["Base Color"].default_value
            g = min(0.3, col[0] * 1.2 + 0.08)
            b.inputs["Base Color"].default_value = (g, g, g, 1)
            b.inputs["Metallic"].default_value = 0.2
            b.inputs["Roughness"].default_value = 0.6
    dc.studio(bg=0.75, strength=1.0)
else:
    dc.studio(bg=0.14, strength=0.9)
for name, (t, d, lens) in CAMS.items():
    if ONLY and name not in ONLY:
        continue
    t = Vector(t)
    cam = dc.add_camera("c_" + name, t + Vector(d), t, lens=lens)
    dc.render_still(cam, os.path.join(OUT, "%s_cu_%s.png" % (TAG, name)), (1536, 1024))
print("CLOSEUPS DONE")
