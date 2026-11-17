"""VAL geometry stage: pack mesh -> welded, bevelled, with re-modelled and added parts.  Saves work/val_geo.blend.

  blender --background --python val_build.py

Rules kept (see README in models/val): pack armature untouched, every vertex 100% in one bone group or none
(= neutral_bone), same origin / axes / centimetres, hand-contact surfaces within 0.4 mm of the source.
Coordinates: mesh-local cm, muzzle -Y, up +Z, the gun's left is +X.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import detail_common as dc  # noqa: E402
import val_parts as vp  # noqa: E402

ROOT = os.environ.get("GAME_ROOT", ".")   # the game project that holds the base meshes (not in this repo)
MDIR = os.path.dirname(HERE)
WORK = os.path.join(MDIR, "work")
os.makedirs(WORK, exist_ok=True)
CLAMP = "--noclamp" not in sys.argv
BEVEL = 0.035          # cm: 0.35 mm real chamfer on the pack mesh's hard convex edges
CLASSES = ["steel_park", "steel_blued", "steel_milled", "polymer", "polymer_mag", "rubber", "lacquer", "copper", "pin"]
PREVIEW = {"steel_park": (0.10, 0.5), "steel_blued": (0.07, 0.8), "steel_milled": (0.3, 0.9), "polymer": (0.04, 0.0),
           "polymer_mag": (0.06, 0.0), "rubber": (0.03, 0.0), "lacquer": (0.2, 0.6), "copper": (0.4, 1.0), "pin": (0.25, 0.9)}

dc.reset()
objs = dc.load(os.path.join(ROOT, r"export\all\fbx\Meshes\Weapons\ASVal\SKM_AS_Val.fbx"), flat=False)
ob = [o for o in objs if o.type == "MESH"][0]
arm = [o for o in objs if o.type == "ARMATURE"][0]
me = ob.data
src_bones = {b.name: (tuple(b.head_local), tuple(b.tail_local)) for b in arm.data.bones}

me.materials.clear()
SLOT = {}
for i, c in enumerate(CLASSES):
    m = bpy.data.materials.new("C_" + c)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    g, mt = PREVIEW[c]
    b.inputs["Base Color"].default_value = (g, g, g, 1)
    b.inputs["Metallic"].default_value = mt
    b.inputs["Roughness"].default_value = 0.45
    me.materials.append(m)
    SLOT[c] = i

bm = bmesh.new()
bm.from_mesh(me)
dl = bm.verts.layers.deform.verify()
gname = {g.index: g.name for g in ob.vertex_groups}


E = vp.Emitter(bm, ob, SLOT)


def vgroup(v):
    for k, w in v[dl].items():
        if w > 0.5:
            return gname[k]
    return None


# ------------------------------------------------------------------ weld per bone group
buckets = {}
for v in bm.verts:
    buckets.setdefault(vgroup(v), []).append(v)
n0 = len(bm.verts)
for k, vs in buckets.items():
    bmesh.ops.remove_doubles(bm, verts=vs, dist=0.002)
bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0001)
print("VAL weld verts %d -> %d, tris %d" % (n0, len(bm.verts), len(bm.faces)))
SRC_TRIS = len(bm.faces)
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.6), verts=bm.verts[:], edges=bm.edges[:], delimit={"SHARP"})
print("VAL planar dissolve: faces", len(bm.faces), "verts", len(bm.verts))


def components():
    seen = set()
    out = []
    for v in bm.verts:
        if v in seen:
            continue
        st = [v]
        seen.add(v)
        c = []
        while st:
            a = st.pop()
            c.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b not in seen:
                    seen.add(b)
                    st.append(b)
        out.append(c)
    return out


def bbox(c):
    return (Vector([min(v.co[i] for v in c) for i in range(3)]), Vector([max(v.co[i] for v in c) for i in range(3)]))


COMPS = [(c, bbox(c), vgroup(c[0])) for c in components()]


def find(lo, hi, group=None, nv=None):
    """source components whose bounds lie inside the box (cm)"""
    out = []
    for c, (mn, mx), g in COMPS:
        if g != group:
            continue
        if nv is not None and len(c) != nv:
            continue
        if all(mn[i] >= lo[i] - 0.03 and mx[i] <= hi[i] + 0.03 for i in range(3)):
            out.append(c)
    return out


def largest(comps):
    return sorted(comps, key=len)[-1:]


def set_class(comps, cls, box=None):
    assert comps, cls
    n = 0
    for c in comps:
        for f in {f for v in c for f in v.link_faces}:
            if box:
                p = f.calc_center_median()
                if not (box[0] <= p.x <= box[1] and box[2] <= p.y <= box[3] and box[4] <= p.z <= box[5]):
                    continue
            f.material_index = SLOT[cls]
            n += 1
    return n


def drop(comps, what):
    vs = [v for c in comps for v in c]
    print("VAL replace %-22s %d source verts" % (what, len(vs)))
    global COMPS
    COMPS = [c for c in COMPS if not any(c[0] is x for x in comps)]
    assert vs, what
    bmesh.ops.delete(bm, geom=vs, context="VERTS")


for f in bm.faces:
    f.material_index = SLOT["steel_park"]
BIG = (-99, -99, -99), (99, 99, 99)
set_class(find(*BIG, group="Mag"), "polymer_mag")
set_class(find((-0.8, -3.2, -12), (0.8, -1.6, -5.6), group="Mag"), "steel_park")           # follower spring plate
set_class(find(*BIG, group="Bolt"), "steel_milled")
set_class(find(*BIG, group="Trigger"), "steel_blued")
set_class(largest(find((-2.6, -20.4, -6.6), (2.6, -9.3, 2.5))), "polymer")                   # handguard
set_class(largest(find((-1.9, -9.5, -16.5), (1.8, 14.1, 0.2))), "polymer", box=(-9, 9, 4.2, 14.6, -17, -6.3))   # grip
set_class(largest(find((-1.7, 44.7, -16), (1.7, 47.5, -2.4))), "rubber", box=(-9, 9, 46.2, 48, -17, 0))        # butt pad

bm.normal_update()
for f in bm.faces:
    p = f.calc_center_median()
    if f.material_index == SLOT["polymer"] and p.y > 4.2 and -15.6 < p.z < -8.0 and abs(f.normal.x) > 0.6:
        f[E.zl["stipple"]] = 1.0

# parts rebuilt below
drop(find((-2.6, -60.3, -3.8), (2.6, -10.3, 1.3), nv=292), "suppressor tube")
drop(find(*BIG, group="Bullets"), "cartridges")
drop(find((-0.3, -58.4, 2.5), (0.3, -57.8, 3.3)), "front sight post")
drop(find((-0.8, -26.8, 2.3), (0.8, -26.5, 2.6), nv=16), "rear sight pivot pin")
drop(find((-1.7, -22.25, 1.9), (1.6, -21.1, 3.0)), "rear sight drums")
drop(find((0.7, 12.6, -5.3), (1.6, 13.95, -0.8), nv=16), "stock hinge pin")
drop(find((-1.25, -1.65, -7.05), (1.25, -0.8, -6.25), nv=32), "mag well cross pin heads")

# ------------------------------------------------------------------ real bevels on the pack geometry
bm.edges.ensure_lookup_table()
bm.normal_update()
edges = []
for e in bm.edges:
    if len(e.link_faces) != 2 or e.calc_length() < 0.06:
        continue
    try:
        ang = e.calc_face_angle()
    except ValueError:
        continue
    if ang > math.radians(28) and e.is_convex:
        edges.append(e)
t0 = sum(len(f.verts) - 2 for f in bm.faces)
r = bmesh.ops.bevel(bm, geom=edges, offset=BEVEL, offset_type="OFFSET", segments=2, profile=0.5, affect="EDGES",
                    clamp_overlap=CLAMP)
bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0002)
t1 = sum(len(f.verts) - 2 for f in bm.faces)
print("VAL bevel %d edges at %.2f mm: tris %d -> %d" % (len(edges), BEVEL * 10, t0, t1))

bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)
BV_FACES = list(bm.faces)


def snap(y, z, side, x=None, axis=None, pos=None, reach=None):
    """Ray from outside onto the gun along an axis.  Returns (hit, group) or None."""
    ax = Vector(vp.AX[axis] if axis else ((1, 0, 0) if side > 0 else (-1, 0, 0)))
    p = Vector(pos) if pos else Vector((0, y, z))
    start = (p + ax * reach) if reach else (p - ax * p.dot(ax) + ax * 40.0)
    hit, nrm, fi, dist = bvh.ray_cast(start, -ax, 80.0)
    if hit is None:
        print("VAL snap MISS", [round(v, 2) for v in p], tuple(ax))
        return None
    if nrm.dot(ax) < 0.85:
        print("VAL snap on a slope (%.2f)" % nrm.dot(ax), [round(v, 2) for v in hit])
    return hit, vgroup(BV_FACES[fi].verts[0]), ax


def stud(geo, y=0, z=0, side=1, cls="pin", sink=0.012, roll=0.0, zone=None, tag=None, axis=None, pos=None, group=0, reach=None):
    s = snap(y, z, side, axis=axis, pos=pos, reach=reach)
    if not s:
        return None
    hit, g, ax = s
    E.add(geo, vp.frame(hit - ax * sink, tuple(ax), roll), cls, group=g if group == 0 else group, zone=zone, tag=tag)
    return hit


def both(geo, y, z, **kw):
    return [stud(geo, y, z, s, **kw) for s in (1, -1)]


# ================================================================== SUPPRESSOR (lathe-turned tube, 48 sides)
SEG = 48
SUP = vp.frame((0, 0, -1.235), "-y")           # local z = distance towards the muzzle (z = -y)
prof = [
    (2.03, 10.30), (2.03, 20.36), (2.46, 20.40), (2.53, 20.47),
    (2.53, 21.33), (2.46, 21.40), (2.36, 21.43), (2.32, 21.62),          # locking collar, fluted
    (2.32, 23.90), (2.295, 23.95), (2.295, 24.05), (2.32, 24.10),
    (2.32, 29.66), (2.27, 29.82), (2.27, 34.08), (2.31, 34.40), (2.31, 35.20), (2.30, 35.40),
    (2.30, 38.00), (2.272, 38.06), (2.272, 38.20), (2.30, 38.26),
    (2.30, 38.60), (2.272, 38.66), (2.272, 38.80), (2.30, 38.86),
    (2.30, 50.20), (2.272, 50.26), (2.272, 50.40), (2.30, 50.46),
    (2.30, 53.28), (2.34, 53.40), (2.34, 54.78), (2.29, 54.90), (2.29, 55.20),
]
E.add(vp.lathe(prof, SEG, flute=(0.05, 3, 4)), SUP, "steel_blued", zone="lathe", tag="suppressor")
E.add(vp.tube_band(55.20, 56.00, 2.29, SEG, holes=12, hole_r=0.2, depth=0.4, span=2, phase=1), SUP, "steel_blued",
      tag="suppressor")
prof2 = [
    (2.29, 56.00), (2.29, 56.24), (2.36, 56.34), (2.36, 59.52), (2.41, 59.72),
    (2.41, 60.08), (2.33, 60.18), (2.04, 60.18), (1.96, 60.10), (1.96, 60.06),
]
E.add(vp.lathe(prof2, SEG, flute=(0.05, 4, 5)), SUP, "steel_blued", zone="lathe", tag="suppressor")
E.add(vp.disc_holes(0.95, 1.96, 60.06, SEG, 8, 0.2, 1.45, 0.5, phase=math.pi / 8), SUP, "steel_blued", tag="suppressor")
prof3 = [(0.95, 60.06), (0.95, 60.14), (0.90, 60.18), (0.67, 60.18), (0.58, 60.09), (0.58, 57.0), (0.0001, 57.0)]
E.add(vp.lathe(prof3, SEG), SUP, "steel_blued", tag="suppressor")
# ================================================================== CARTRIDGES (two visible rounds, 16 sides)
case = [(0.0001, 0.0), (0.16, 0.0), (0.16, -0.04), (0.20, -0.04), (0.20, 0.0), (0.44, 0.0), (0.485, 0.045), (0.485, 0.15),
        (0.41, 0.21), (0.41, 0.31), (0.485, 0.40), (0.48, 3.35), (0.39, 3.72), (0.385, 4.08)]
bullet = [(0.37, 4.08), (0.365, 4.45), (0.335, 4.95), (0.27, 5.35), (0.17, 5.62), (0.08, 5.71), (0.0001, 5.72)]
for cx, cz in ((-0.495, -3.925), (0.295, -4.515)):
    M = vp.frame((cx, -2.33, cz), "-y")
    E.add(vp.lathe(case, 16), M, "lacquer", group="Bullets", tag="cartridges")
    E.add(vp.lathe(bullet, 16), M, "copper", group="Bullets", tag="cartridges")

# ================================================================== FRONT SIGHT
M = vp.frame((0, -58.08, 2.45), "+z")
E.add(vp.lathe([(0.27, 0.0), (0.27, 0.22), (0.22, 0.27), (0.10, 0.27)], 20, flute=(0.03, 0, 1)), M, "steel_park", tag="front sight")
E.add(vp.lathe([(0.10, 0.20), (0.085, 0.30), (0.085, 0.77), (0.06, 0.81)], 12, cap_top=True), M, "steel_milled", tag="front sight",
      zone="bare")
both(vp.pin_head(0.17, 0.05), -58.6, 1.45, tag="front sight")
both(vp.slot_screw(0.2, 0.07), -58.1, 2.15, roll=25, tag="front sight")

# ================================================================== REAR SIGHT
M = vp.frame((-0.86, -26.655, 2.435), "+x")
E.add(vp.lathe([(0.0001, 0.0), (0.15, 0.0), (0.19, 0.03), (0.19, 0.10), (0.115, 0.12), (0.115, 1.60), (0.19, 1.62),
                (0.19, 1.69), (0.15, 1.72), (0.0001, 1.72)], 16), M, "pin", tag="rear sight")
knob = [(0.0001, 0.0), (0.28, 0.0), (0.28, 0.42), (0.46, 0.42), (0.52, 0.48), (0.52, 1.02), (0.46, 1.08), (0.30, 1.08),
        (0.26, 1.12), (0.26, 1.20), (0.0001, 1.20)]
E.add(vp.lathe(knob, 28, flute=(0.045, 4, 5)), vp.frame((0.29, -21.66, 2.45), "+x"), "steel_park", tag="rear sight")
E.add(vp.lathe(knob, 28, flute=(0.045, 4, 5)), vp.frame((-0.29, -21.66, 2.45), "-x"), "steel_park", tag="rear sight")
for s, ax in ((1, "+x"), (-1, "-x")):                      # coin slot in each drum's end
    E.add(vp.slot_screw(0.2, 0.06, 16), vp.frame((s * 1.48, -21.66, 2.45), ax, roll=30), "pin", tag="rear sight")

# ================================================================== STOCK HINGE (left side, vertical pin)
HP = (1.14, 13.27, -5.25)
M = vp.frame(HP, "+z")
E.add(vp.lathe([(0.0001, -0.02), (0.20, -0.02), (0.30, 0.03), (0.30, 0.14), (0.21, 0.16), (0.21, 4.29), (0.30, 4.31),
                (0.30, 4.42), (0.20, 4.47), (0.0001, 4.47)], 16), M, "pin", tag="hinge")
for z0, z1 in ((0.18, 1.38), (1.52, 2.93), (3.07, 4.27)):
    c = 0.05
    E.add(vp.lathe([(0.24, z0), (0.43, z0), (0.47, z0 + c), (0.47, z1 - c), (0.43, z1), (0.24, z1)], 20), M, "steel_park", tag="hinge")

# ================================================================== FASTENERS on the receiver
E.add(vp.pin_head(0.36, 0.16, 18), vp.frame((1.055, -1.23, -6.65), "+x"), "pin", tag="fasteners")
E.add(vp.pin_head(0.36, 0.16, 18), vp.frame((-1.055, -1.23, -6.65), "-x"), "pin", tag="fasteners")
F = [  # (y, z, kind, sides)
    (3.9, -3.5, "pin", (1,)),            # trigger pin (left: the lever covers it on the right)
    (1.6, -3.05, "pin", (1,)),           # hammer pin
    (-8.1, -3.0, "rivet", (-1,)),        # front trunnion
    (-8.1, -4.6, "rivet", (1, -1)),
    (11.4, -0.6, "rivet", (1, -1)),      # rear trunnion
    (11.4, -3.6, "rivet", (1, -1)),
    (-4.2, -5.6, "rivet", (1, -1)),      # magazine well reinforcement
    (-7.4, -6.2, "rivet", (1, -1)),
]
for y, z, kind, sides in F:
    for s in sides:
        geo = vp.pin_head(0.2, 0.05) if kind == "pin" else vp.rivet(0.21, 0.085)
        stud(geo, y, z, s, tag="fasteners")
# grip bolt underneath, handguard cross screw
stud(vp.socket_screw(0.3, 0.06), tag="fasteners", axis="-z", pos=(0, 9.6, 0))

# ================================================================== SERRATIONS (thumb / finger surfaces)
for k in range(5):                                   # magazine release paddle, rear face
    stud(vp.box(1.3, 0.13, 0.05, c=0.03), tag="serrations", axis="+y", pos=(0, 0, -9.25 + k * 0.2), cls="steel_park", reach=1.3)
for k in range(5):                                   # bolt handle: ridges across the swept bar, top and bottom
    t = 0.45 + 0.12 * k
    for ax in ("+z", "-z"):
        stud(vp.box(0.09, 0.34, 0.04, c=0.02), tag="serrations", axis=ax, pos=(-1.6 - 2.2 * t, -7.15 - 1.05 * t, -0.93),
             cls="steel_milled", roll=25.5 if ax == "+z" else -25.5, reach=1.0)

# ================================================================== STOCK: butt ribs, weld beads
for k in range(15):
    stud(vp.box(2.5, 0.2, 0.07, c=0.05), tag="stock", axis="+y", pos=(0, 48, -14.6 + k * 0.8), cls="rubber", sink=0.02, reach=3)


def bead(c, rx, rz, r=0.075, n=20):
    pts = [(c[0] + math.cos(2 * math.pi * i / n) * rx, c[1] + math.sin(i * 2.4) * 0.02, c[2] + math.sin(2 * math.pi * i / n) * rz)
           for i in range(n)]
    E.add(vp.pipe(pts, r, 6, closed=True), Matrix.Identity(4), "steel_park", tag="stock", zone="bare")


bead((0, 19.05, -2.80), 0.93, 0.80)
bead((0, 46.02, -3.685), 0.93, 0.93)

# ------------------------------------------------------------------ finish
bm.normal_update()
T = math.radians(35)
for e in bm.edges:
    e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(0) < T
for f in bm.faces:
    f.smooth = True
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
# weights check: every vertex in at most one group at weight 1
bad = 0
cnt = {}
for v in bm.verts:
    ws = [(k, w) for k, w in v[dl].items() if w > 0]
    if len(ws) > 1 or (ws and abs(ws[0][1] - 1) > 1e-6):
        bad += 1
    cnt[gname[ws[0][0]] if ws else "neutral_bone"] = cnt.get(gname[ws[0][0]] if ws else "neutral_bone", 0) + 1
print("VAL weights: blended verts", bad, cnt)
assert bad == 0
tris = sum(len(f.verts) - 2 for f in bm.faces)
print("VAL parts added", E.count, E.tris)
print("VAL tris source %d -> %d" % (SRC_TRIS, tris))
mn = [min(v.co[i] for v in bm.verts) for i in range(3)]
mx = [max(v.co[i] for v in bm.verts) for i in range(3)]
print("VAL bounds", [round(v, 2) for v in mn], [round(v, 2) for v in mx])
bm.faces.layers.int.remove(E.new_layer)
bm.to_mesh(me)
bm.free()
me.update()
for b in arm.data.bones:
    assert (tuple(b.head_local), tuple(b.tail_local)) == src_bones[b.name]
print("VAL bones untouched", list(src_bones))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "val_geo.blend"))
print("VAL GEO DONE")
