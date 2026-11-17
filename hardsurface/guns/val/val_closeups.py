"""Grey close-up renders per mechanism (inputs for the reference images, and later before/after pairs).
  blender --background --python val_closeups.py -- <fbx|glb|blend> <outdir> <tag> [grey|pbr] [samples]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detail_common as dc
import bpy
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT, TAG = a[0], a[1], a[2]
STYLE = a[3] if len(a) > 3 else "grey"
os.makedirs(OUT, exist_ok=True)
dc.reset(); dc.load(SRC); dc.use_cycles(int(a[4]) if len(a) > 4 else 48)
if STYLE == "grey":
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
    mn, mx = dc.world_bounds()
    dc.studio(bg=0.14, strength=0.9)
# name: (camera position, target) in metres, lens / ortho span.  Muzzle -Y, up +Z, gun's left +X.
V = {
    "receiver_r": ((-0.6, 0.02, -0.01), (0, 0.02, -0.025), dict(ortho=0.30)),
    "receiver_l": ((0.6, 0.02, -0.01), (0, 0.02, -0.025), dict(ortho=0.30)),
    "bolt":       ((-0.22, -0.20, 0.10), (-0.01, -0.03, -0.005), dict(lens=70)),
    "handguard":  ((0.30, -0.42, 0.14), (0, -0.20, -0.01), dict(lens=60)),
    "suppressor": ((0.34, -0.70, 0.16), (0, -0.40, -0.01), dict(lens=60)),
    "magazine":   ((0.36, -0.22, -0.16), (0, -0.07, -0.10), dict(lens=70)),
    "grip":       ((-0.33, 0.20, -0.10), (0, 0.10, -0.07), dict(lens=70)),
    "stock":      ((0.50, 0.50, 0.14), (0, 0.30, -0.07), dict(lens=60)),
    "hinge":      ((0.16, 0.30, 0.10), (0, 0.16, -0.03), dict(lens=70)),
    "rear_sight": ((0.11, -0.12, 0.10), (0, -0.24, 0.025), dict(lens=70)),
    "front_sight": ((0.10, -0.47, 0.10), (0, -0.585, 0.02), dict(lens=70)),
    "muzzle":     ((0.10, -0.76, 0.06), (0, -0.59, -0.005), dict(lens=70)),
    "top":        ((0.02, 0.26, 0.20), (0, -0.05, 0.0), dict(lens=50)),
}
only = a[5].split(",") if len(a) > 5 else list(V)
for k in only:
    p, t, kw = V[k]
    cam = dc.add_camera(k, p, t, **kw)
    dc.render_still(cam, os.path.join(OUT, "%s_%s.png" % (TAG, k)), (1600, 900))
print("CLOSEUPS DONE")
