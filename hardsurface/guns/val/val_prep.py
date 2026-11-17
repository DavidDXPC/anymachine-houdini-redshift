"""VAL bake preparation: work/val_geo.blend -> work/val_prebake.blend (normals, UVs, decal sheets, bake materials).
The bake itself (val_bake.py) can then run anywhere: the render farm or this machine.

  blender --background --python val_prep.py
"""
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import detail_shader as ds  # noqa: E402

MDIR = os.path.dirname(HERE)
WORK = os.path.join(MDIR, "work")
OUT_RES = 2048
bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "val_geo.blend"))
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
sc = bpy.context.scene


def sheet(name, side, y0, y1, z0, z1, depth, items, res_w=4096):
    """side +1 = left face of the gun (+X), -1 = right.  items written with (y, z)."""
    conv = []
    for it in items:
        it = list(it)
        it[1], it[2] = ((it[1] - y0) if side > 0 else (y1 - it[1])), it[2] - z0
        conv.append(tuple(it))
    if side > 0:
        return dict(name=name, origin=(0, y0, z0), right=(0, 1, 0), up=(0, 0, 1), w=y1 - y0, h=z1 - z0, res_w=res_w,
                    facing=(1, 0, 0), depth=depth, items=conv)
    return dict(name=name, origin=(0, y1, z0), right=(0, -1, 0), up=(0, 0, 1), w=y1 - y0, h=z1 - z0, res_w=res_w,
                facing=(-1, 0, 0), depth=depth, items=conv)


def grooves(y, z0, n, length, pitch=0.55, w=0.16):
    return [("slot", y, z0 + i * pitch, length, w, 0, "recess") for i in range(n)]


rec_l = [("text", 6.6, -5.0, 0.30, "17 0429", "recess"), ("ring", 3.6, -5.0, 0.17, 0.045, "recess")]
rec_r = [("circle", -2.6, -0.6, 0.11, "recess"), ("circle", -2.6, -0.6, 0.09, "paint"),      # selector positions
         ("circle", -2.9, -1.35, 0.11, "recess"), ("circle", -2.9, -1.35, 0.09, "paint"),
         ("circle", -2.55, -1.35, 0.11, "recess"), ("circle", -2.55, -1.35, 0.09, "paint"),
         ("text", -5.6, -5.3, 0.26, "93", "recess")]
hg = grooves(-15.0, -3.6, 7, 7.0)
mag = [("text", -6.6, -19.2, 0.30, "9x39", "raise")]
CFG = dict(
    name="val", bevel=0.00035, wear_radius=0.0009, stipple_scale=11.0, lathe_scale=16.0, lathe_h=0.03, scratch_k=0.45,
    sheets=[
        sheet("RL", 1, -12, 16, -9, 3, (1.3, 2.2), rec_l),
        sheet("RR", -1, -12, 16, -9, 3, (1.3, 2.2), rec_r),
        sheet("HL", 1, -21, -9, -7, 3, (2.3, 2.7), hg, res_w=2048),
        sheet("HR", -1, -21, -9, -7, 3, (2.3, 2.7), hg, res_w=2048),
        sheet("ML", 1, -14, -1, -22, -3, (1.2, 1.6), mag, res_w=2048),
    ],
)

# ------------------------------------------------------------------ normals
bpy.context.view_layer.objects.active = ob
for o in sc.objects:
    o.select_set(o is ob)
wn = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
wn.keep_sharp = True
wn.weight = 50
wn.mode = "FACE_AREA"
bpy.ops.object.modifier_apply(modifier="WN")

# ------------------------------------------------------------------ explode the animated parts for the bake
nv = len(me.vertices)
co0 = np.zeros(nv * 3, dtype=np.float32)
me.vertices.foreach_get("co", co0)
at = me.attributes.new("opos", "FLOAT_VECTOR", "POINT")
at.data.foreach_set("vector", co0)
co1 = co0.reshape(-1, 3).copy()
for v in me.vertices:
    for ge in v.groups:
        if ge.weight > 0.5:
            co1[v.index, 2] -= 150.0 * (ge.group + 1)
            break

# ------------------------------------------------------------------ UVs
while me.uv_layers:
    me.uv_layers.remove(me.uv_layers[0])
me.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0, correct_aspect=True,
                         scale_to_bounds=False)
bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode="OBJECT")
bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)
random.seed(1)
dirs = []
while len(dirs) < 24:
    d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
    if 0.1 < d.length < 1:
        dirs.append(d.normalized())
vis = []
for f in bm.faces:
    c = f.calc_center_median() + f.normal * 0.01
    free = tot = 0
    for d in dirs:
        if d.dot(f.normal) < 0.15:
            continue
        tot += 1
        if bvh.ray_cast(c, d, 200.0)[0] is None:
            free += 1
    vis.append(free / max(tot, 1))
uvl = bm.loops.layers.uv.active
parent = list(range(len(bm.faces)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for e in bm.edges:
    if len(e.link_faces) != 2:
        continue
    la, lb = e.link_loops[0], e.link_loops[1]
    a0, a1 = la[uvl].uv, la.link_loop_next[uvl].uv
    b0, b1 = lb[uvl].uv, lb.link_loop_next[uvl].uv
    if (a0 - b1).length < 1e-5 and (a1 - b0).length < 1e-5:
        ra, rb = find(la.face.index), find(lb.face.index)
        if ra != rb:
            parent[ra] = rb
isl = {}
for f in bm.faces:
    isl.setdefault(find(f.index), []).append(f)
# what the player looks at gets the texels: rear and top of the gun; the far muzzle end and the stock get fewer
PRIO = [((-3, 3, -30, 14, -1.5, 4), 1.35), ((-3, 3, -62, -30, -4, 4), 0.8), ((-3, 3, 14.5, 48, -17, 0), 0.6)]
hidden = 0
for fs in isl.values():
    area = sum(f.calc_area() for f in fs)
    v = sum(vis[f.index] * f.calc_area() for f in fs) / max(area, 1e-9)
    k = 0.3 if v < 0.04 else (0.6 if v < 0.2 else 1.0)
    cen = sum((f.calc_center_median() for f in fs), Vector()) / len(fs)
    for box, kk in PRIO:
        if box[0] <= cen.x <= box[1] and box[2] <= cen.y <= box[3] and box[4] <= cen.z <= box[5]:
            k *= kk
    if k < 1:
        hidden += 1
    if k != 1.0:
        loops = [l for f in fs for l in f.loops]
        cu = sum((l[uvl].uv for l in loops), Vector((0, 0))) / len(loops)
        for l in loops:
            l[uvl].uv = cu + (l[uvl].uv - cu) * k
print("VAL uv islands %d, scaled down %d" % (len(isl), hidden))
bm.to_mesh(me)
bm.free()
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
try:
    bpy.ops.uv.pack_islands(margin=0.0012, rotate=True, shape_method="CONCAVE", margin_method="FRACTION")
except TypeError:
    bpy.ops.uv.pack_islands(margin=0.0012, rotate=True)
bpy.ops.object.mode_set(mode="OBJECT")
me.calc_loop_triangles()
uv = np.zeros(len(me.loops) * 2)
me.uv_layers[0].data.foreach_get("uv", uv)
uv = uv.reshape(-1, 2)
a_uv = a_3d = 0.0
for t in me.loop_triangles:
    p = [uv[i] for i in t.loops]
    a_uv += abs((p[1][0] - p[0][0]) * (p[2][1] - p[0][1]) - (p[2][0] - p[0][0]) * (p[1][1] - p[0][1])) / 2
    a_3d += t.area
print("VAL tris %d  surface %.0f cm2  uv fill %.2f  texel density %.2f px/mm at %d" %
      (len(me.loop_triangles), a_3d, a_uv, math.sqrt(a_uv * OUT_RES * OUT_RES / (a_3d * 100.0)), OUT_RES))

# ------------------------------------------------------------------ decal sheets, bake materials
sc.render.engine = "CYCLES"
sheets = ds.render_sheets(CFG, WORK)
for _, img in sheets:
    img.pack()
group = ds.build_group(CFG, sheets)
for i, m in enumerate(list(me.materials)):
    cls = m.name[2:]
    me.materials[i] = ds.make_bake_material("BAKE_%d_%s" % (i, cls), group, ds.CLASS_PARAMS[cls])
me.vertices.foreach_set("co", co1.ravel())
me.update()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "val_prebake.blend"), compress=True)
print("VAL PREP DONE", os.path.getsize(os.path.join(WORK, "val_prebake.blend")))
