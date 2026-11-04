"""Normalise the Meshy quadruped and measure the leg mechanism from geometry.

blender -b --factory-startup --python probe.py -- --glb gen/meshy/model.glb --out gen/measure.json [--length 0.70]
Meshy: Z-up, front -Y already. Scale so the Y extent = --length, centre XY, feet on z=0.
Prints body extents, per-quadrant foot centres/radius, hip (HFE) centre, knee centre, and side-profile centrelines.
"""
import bpy, sys, json, math
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None, c=str: c(argv[argv.index(k) + 1]) if k in argv else d
GLB, OUT, LEN = opt("--glb"), opt("--out"), opt("--length", 0.70, float)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
vs = []
for o in ms:
    vs += [o.matrix_world @ v.co for v in o.data.vertices]
lo = Vector([min(v[i] for v in vs) for i in range(3)])
hi = Vector([max(v[i] for v in vs) for i in range(3)])
s = LEN / (hi.y - lo.y)
c = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
vs = [(v - c) * s for v in vs]
lo = Vector([min(v[i] for v in vs) for i in range(3)])
hi = Vector([max(v[i] for v in vs) for i in range(3)])
R = {"scale": s, "offset": list(c), "dims": list(hi - lo)}


def pct(a, p):
    a = sorted(a)
    return a[min(len(a) - 1, max(0, int(p * len(a))))] if a else None


# body: central column (|x|<0.04, |y|<0.12) -> underside and top
col = [v for v in vs if abs(v.x) < 0.04 and abs(v.y) < 0.12]
R["body_bottom"] = pct([v.z for v in col], 0.01)
R["body_top"] = pct([v.z for v in col], 0.995)
mid = [v for v in vs if abs(v.y) < 0.12 and v.z > R["body_bottom"] + 0.01]
R["body_hw"] = pct([abs(v.x) for v in mid], 0.99)
body = [v for v in vs if abs(v.x) < R["body_hw"] and v.z > R["body_bottom"] - 0.005]
R["body_y"] = [pct([v.y for v in body], 0.002), pct([v.y for v in body], 0.998)]
# x-histogram at hip height bands to see the outboard actuators
legs = {}
for sx in (-1, 1):
    for sy in (-1, 1):
        k = ("L" if sx < 0 else "R") + ("F" if sy < 0 else "H")
        q = [v for v in vs if v.x * sx > 0 and v.y * sy > 0]
        low = [v for v in q if v.z < 0.07]
        zmin = min(v.z for v in low)
        ball = [v for v in low if v.z < zmin + 0.05]
        rb = (max(v.x for v in ball) - min(v.x for v in ball)) / 2
        ball = [v for v in low if v.z < zmin + rb]
        fc = Vector((sum(v.x for v in ball) / len(ball), sum(v.y for v in ball) / len(ball), zmin + rb))
        out = [v for v in q if abs(v.x) > R["body_hw"] + 0.004]
        # side-profile centreline of the leg: per 1 cm z bin, y range and x range of outboard + below-body verts
        legv = [v for v in q if abs(v.x) > R["body_hw"] + 0.004 or v.z < R["body_bottom"] - 0.01]
        prof = []
        for zb in range(int(zmin * 100), int(R["body_top"] * 100) + 1):
            b = [v for v in legv if zb / 100 <= v.z < (zb + 1) / 100]
            if len(b) > 20:
                prof.append([zb / 100 + 0.005, round(pct([v.y for v in b], 0.02), 3), round(pct([v.y for v in b], 0.98), 3),
                             round(pct([v.x for v in b], 0.02), 3), round(pct([v.x for v in b], 0.98), 3), len(b)])
        ozt = max(v.z for v in out)
        top = [v for v in out if v.z > ozt - 0.02]
        legs[k] = {"foot_c": [round(x, 4) for x in fc], "foot_r": round(rb, 4), "outboard_ztop": round(ozt, 4),
                   "outboard_top_y": [round(min(v.y for v in top), 3), round(max(v.y for v in top), 3)],
                   "outboard_x": [round(pct([abs(v.x) for v in out], 0.01), 3), round(pct([abs(v.x) for v in out], 0.99), 3)],
                   "profile": prof}
R["legs"] = legs
json.dump(R, open(OUT, "w"), indent=1)
print("PROBE", json.dumps({k: v for k, v in R.items() if k != "legs"}))
for k, l in legs.items():
    print(k, {a: b for a, b in l.items() if a != "profile"})
    for p in l["profile"]:
        print("   ", p)
