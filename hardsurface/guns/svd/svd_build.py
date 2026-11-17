"""SVD remodel, geometry stage.

  blender --background --python svd_build.py -- [preview]

Imports the pack's rigged FBX (armature untouched), welds the pack mesh, drops everything forward of the receiver
(barrel, sights, gas system, handguard: all rebuilt in svd_parts.py), chamfers the kept pack parts, appends the new
parts and small hardware, then unwraps and sets up the bake materials.  Saves models/svd/work/svd_prebake.blend,
which svd_bake.py bakes (on the farm or locally) and svd_finish.py turns into the final .blend and .glb.
'preview' stops after the geometry and saves work/svd_geo.blend with flat class colours.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import detail_common as dc  # noqa: E402
import detail_parts as dp  # noqa: E402
import detail_shader as ds  # noqa: E402
import svd_parts as sp  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = "preview" in a
ROOT = os.environ.get("GAME_ROOT", ".")   # the game project that holds the base meshes (not in this repo)
MDIR = os.path.join(ROOT, "models", "svd")
WORK = os.path.join(MDIR, "work")
os.makedirs(WORK, exist_ok=True)
OUT_RES = 2048
XC = sp.XC

CFG = dict(
    name="svd",
    sharp_angle=35,
    bevel=0.0004, wear_radius=0.0009,
    sheets=[],
)
SRC_CLASS = {0: "steel_milled", 1: "steel_blued", 3: "steel_park", 7: "wood", 11: "steel_milled", 12: "steel_park",
             14: "steel_milled"}

dc.reset()
objs = dc.load(os.path.join(ROOT, r"export\all\fbx\Meshes\Weapons\SVD\SKM_SVD.fbx"), flat=False)
ob = [o for o in objs if o.type == "MESH"][0]
me = ob.data
src_mn, src_mx = dc.world_bounds([ob])
me.calc_loop_triangles()
print("SVD source tris", len(me.loop_triangles))

bm = bmesh.new()
bm.from_mesh(me)
dl = bm.verts.layers.deform.verify()
gindex = {g.name: g.index for g in ob.vertex_groups}
gname = {v: k for k, v in gindex.items()}


def vkey(v):
    return tuple(sorted(k for k, w in v[dl].items() if w > 0.5))


# ---- weld within each bone group
buckets = {}
for v in bm.verts:
    buckets.setdefault(vkey(v), []).append(v)
for vs in buckets.values():
    bmesh.ops.remove_doubles(bm, verts=vs, dist=0.002)
bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0001)

# ---- components; drop the static ones forward of the receiver, and hidden clutter
bm.verts.ensure_lookup_table()
seen = set()
comps = []
for v in bm.verts:
    if v in seen:
        continue
    st = [v]
    seen.add(v)
    c = []
    while st:
        x = st.pop()
        c.append(x)
        for e in x.link_edges:
            y = e.other_vert(x)
            if y not in seen:
                seen.add(y)
                st.append(y)
    comps.append(c)
drop = []
cheek_faces = set()
stock_v, cheek_v = [], []
for c in comps:
    ys = [v.co.y for v in c]
    static = not vkey(c[0])
    fs = {f for v in c for f in v.link_faces}
    if static and max(ys) < -12.1:
        drop += c
    elif static and 20 < min(ys) and max(ys) < 32.5 and any(f.material_index == 12 for f in fs):
        cheek_faces |= fs
        cheek_v += c
    elif static and any(f.material_index == 7 for f in fs):
        stock_v += c
print("SVD dropped %d verts of pack geometry forward of the receiver" % len(drop))
REMESHED = []
for vs, vox, it, tris, nm in ((stock_v, 0.10, 10, 4200, "stock"), (cheek_v, 0.08, 5, 900, "cheek")):
    fs = list({f for v in vs for f in v.link_faces})
    if nm == "stock":          # remember where the steel butt plate was
        pv = []
        pf = []
        for f in fs:
            if f.material_index == 12:
                pf.append([len(pv) + i for i in range(len(f.verts))])
                pv += [v.co.copy() for v in f.verts]
        PLATE = BVHTree.FromPolygons(pv, pf)
    part = bmesh.new()
    vm = {v: part.verts.new(v.co) for v in vs}
    for f in fs:
        part.faces.new([vm[v] for v in f.verts])
    REMESHED.append((sp.remesh(part, vox, it, tris), nm))
    drop += vs
bmesh.ops.delete(bm, geom=drop, context="VERTS")

# ---- material classes: one slot per class
class_slot = {}


def slot(cls):
    if cls not in class_slot:
        m = bpy.data.materials.new("C_" + cls)
        me.materials.append(m)
        class_slot[cls] = len(me.materials) - 1
    return class_slot[cls]


for f in bm.faces:
    if f in cheek_faces:
        f.material_index = slot("leather")
    else:
        f.material_index = slot(SRC_CLASS.get(f.material_index, "steel_park"))

# ---- chamfer the kept pack parts (real geometry; the bake rounds the chamfers further)
bm.normal_update()
n0 = len(bm.faces)
bm.normal_update()
springs = set()
bm.verts.ensure_lookup_table()
steel = [f for f in bm.faces if f.material_index not in (slot("wood"), slot("leather"))
         and not (-9 < f.calc_center_median().y < 12.5 and 0.6 < f.calc_center_median().z < 1.5
                  and abs(f.calc_center_median().x - XC) < 0.5)]          # leave the recoil spring coils alone
sp.bev(bm, 0.045, segs=1, angle=28, faces=steel)
print("SVD chamfer faces %d -> %d" % (n0, len(bm.faces)))


def emit(pb, cls, group, override=None):
    s = slot(cls)
    ov = {}
    if override:
        s2 = slot(override[1])
        ov = {tuple(sorted(v.index for v in f.verts)) for f in override[0]}
    else:
        bmesh.ops.triangulate(pb, faces=[f for f in pb.faces if len(f.verts) > 4])
    pb.verts.index_update()
    vm = {}
    for v in pb.verts:
        nv = bm.verts.new(v.co)
        if group:
            nv[dl][gindex[group]] = 1.0
        vm[v] = nv
    for f in pb.faces:
        try:
            nf = bm.faces.new([vm[v] for v in f.verts])
        except ValueError:
            continue
        nf.material_index = s2 if ov and tuple(sorted(v.index for v in f.verts)) in ov else s
    pb.free()


for pb, nm in REMESHED:
    if nm == "cheek":
        emit(pb, "leather", None)
        continue
    plate = [f for f in pb.faces if PLATE.find_nearest(f.calc_center_median())[3] < 0.13]
    emit(pb, "wood", None, override=(set(plate), "steel_park"))
for pb, cls, group in sp.all_parts():
    emit(pb, cls, group)

# ---- small hardware snapped onto the surface (rides with whatever it lands on)
bm.verts.index_update()
bm.faces.ensure_lookup_table()
HW = []
L, R = "+x", "-x"
for y, z in ((-12.7, -0.9), (-12.7, -3.2), (-11.2, -2.9), (12.6, -4.1), (11.2, -1.25), (14.6, -3.0)):
    HW.append(dict(pos=(0, y, z), axis=L, snap=True, kind="rivet", r=0.19, h=0.07, slot=slot("steel_milled")))
for y, z in ((-12.7, -0.9), (-12.7, -3.2), (-11.2, -2.9), (12.6, -4.1), (14.6, -3.0)):
    HW.append(dict(pos=(0, y, z), axis=R, snap=True, kind="rivet", r=0.19, h=0.07, slot=slot("steel_milled")))
for y, z in ((2.6, -4.35), (5.6, -4.35)):                 # hammer and trigger axis pins
    HW.append(dict(pos=(0, y, z), axis=L, snap=True, kind="pin", r=0.17, h=0.05, slot=slot("steel_milled")))
# stock: sling swivel on the left, butt plate screws, cheek rest strap studs
HW.append(dict(pos=(0, 34.5, -9.6), axis=L, snap=True, kind="box", size=(1.2, 0.6, 0.12), slot=slot("steel_park"), roll=90))
HW.append(dict(pos=(0, 34.5, -9.6), axis=L, snap=True, kind="ring", r=0.55, t=0.09, slot=slot("steel_park"), lift=0.08))
HW.append(dict(pos=(0, -43.55, -1.2), axis=L, snap=True, kind="box", size=(1.1, 0.55, 0.12), slot=slot("steel_park"), roll=90))
HW.append(dict(pos=(0, -43.55, -1.2), axis=L, snap=True, kind="ring", r=0.5, t=0.085, slot=slot("steel_park"), lift=0.08))
for z in (-3.6, -10.8):
    HW.append(dict(pos=(XC, 0, z), axis="+y", snap=True, kind="pin", r=0.3, h=0.06, slot=slot("steel_milled")))
for y in (22.0, 30.4):
    for ax in (L, R):
        HW.append(dict(pos=(0, y, -1.2), axis=ax, snap=True, kind="rivet", r=0.2, h=0.08, slot=slot("steel_milled")))
for ax in (L, R):                                          # handguard ferrule and cap pins
    HW.append(dict(pos=(0, -14.7, -1.0), axis=ax, snap=True, kind="pin", r=0.16, h=0.05, slot=slot("steel_milled")))
    HW.append(dict(pos=(0, -43.55, 0.9), axis=ax, snap=True, kind="pin", r=0.14, h=0.05, slot=slot("steel_milled")))
print("SVD hardware", dp.add_parts(bm, dl, gindex, HW))

# ---- shading
T = math.radians(CFG["sharp_angle"])
for e in bm.edges:
    e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(0) < T
for f in bm.faces:
    f.smooth = True
bm.normal_update()
# pack slots that survived on bevel faces take a neighbour class; weights are snapped back to rigid
for f in bm.faces:
    if f.material_index < 15:
        nb = [g.material_index for e in f.edges for g in e.link_faces if g.material_index >= 15]
        f.material_index = nb[0] if nb else slot("steel_park")
for v in bm.verts:
    ws = sorted(((w, k) for k, w in v[dl].items()), reverse=True)
    v[dl].clear()
    if ws and ws[0][0] > 0.5:
        v[dl][ws[0][1]] = 1.0
bad = sum(1 for v in bm.verts if len([1 for k, w in v[dl].items() if w > 0]) > 1 or any(0 < w < 1 for k, w in v[dl].items()))
print("SVD blended-weight verts:", bad)
bm.to_mesh(me)
bm.free()
me.update()
# drop the now unused pack slots
used = sorted({p.material_index for p in me.polygons})
remap = {}
keep = [me.materials[i] for i in used]
for i, u in enumerate(used):
    remap[u] = i
idx = np.zeros(len(me.polygons), dtype=np.int32)
me.polygons.foreach_get("material_index", idx)
idx = np.array([remap[i] for i in idx], dtype=np.int32)
me.materials.clear()
for m in keep:
    me.materials.append(m)
me.polygons.foreach_set("material_index", idx)
me.update()
me.calc_loop_triangles()
print("SVD tris", len(me.loop_triangles), "slots", [m.name for m in me.materials])
mn, mx = dc.world_bounds([ob])
print("SVD bounds src", [round(v, 4) for v in src_mn], [round(v, 4) for v in src_mx])
print("SVD bounds new", [round(v, 4) for v in mn], [round(v, 4) for v in mx])

PREV = {"wood": (0.42, 0.16, 0.04, 0.0, 0.4), "leather": (0.08, 0.05, 0.03, 0.0, 0.6), "steel_blued": (0.04, 0.045, 0.05, 0.8, 0.4),
        "steel_park": (0.035, 0.035, 0.038, 0.6, 0.55), "steel_milled": (0.3, 0.3, 0.3, 1.0, 0.35)}
if PREVIEW:
    for m in me.materials:
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        c = PREV[m.name[2:]]
        b.inputs["Base Color"].default_value = (*c[:3], 1)
        b.inputs["Metallic"].default_value = c[3]
        b.inputs["Roughness"].default_value = c[4]
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    wn = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    bpy.ops.object.modifier_apply(modifier="WN")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "svd_geo.blend"))
    print("SVD PREVIEW SAVED")
    sys.exit(0)

exec(open(os.path.join(HERE, "svd_uvbake_setup.py")).read())
