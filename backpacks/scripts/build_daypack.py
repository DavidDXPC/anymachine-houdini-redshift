"""Bag 2: zip daypack. Generated Meshy skin -> rigged daypack.

blender -b --factory-startup --python build_daypack.py -- --glb gen/daypack_meshy/model.glb --out out/daypack/daypack.blend

Controls (custom props on `daypack_rig`, 0..1, clamped):
  zip           slider travels the U-zip (right side up, over the top, down the left); the front panel peels open
                behind it and falls forward (12 in-between shape keys on the rebuilt panel + slider bone)
  pocket_fill   front pocket bulge (shape key)
  fill          body sag/bulge (deformer bones + slack folds)
  strap_length  shoulder straps (shared ShoulderStraps)
Baked jiggle: zip puller, strap tails.
"""
import bpy, bmesh, sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
from softlib import *
from rig_parts import *
from straps import ShoulderStraps
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
GLB, OUT = os.path.abspath(opt("--glb")), os.path.abspath(opt("--out"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
report = {"bag": "daypack", "glb": GLB}
H = 0.44
ob = load_gen(GLB, 0, H)
fix_gen_material(ob, rough=0.88)
me = ob.data
OFF = -((-0.153) + 0.035) / 2
me.transform(Matrix.Translation((0, OFF, 0)))
P = lambda x, y, z: Vector((x, y + OFF, z))
YCUT = -0.080 + OFF  # the zip runs along the front edge of the gusset (top-view probe: puller ends at y = -0.083)
YBK = 0.035 + OFF
YF = -0.153 + OFF
ZB = 0.06  # zip ends this high on both sides; below it the panel is sewn (the hinge)
samp = tex_sampler(ob)

bm = bmesh.new()
bm.from_mesh(me)
nv0 = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)


def comps(faces):
    fs, out = set(faces), []
    while fs:
        st = [fs.pop()]
        comp = [st[0]]
        while st:
            f = st.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in fs:
                        fs.remove(g)
                        st.append(g)
                        comp.append(g)
        out.append(comp)
    return out


kill = set()
for c in comps(list(bm.faces)):
    vs = [v.co for f in c for v in f.verts]
    lo = Vector([min(p[i] for p in vs) for i in range(3)])
    hi = Vector([max(p[i] for p in vs) for i in range(3)])
    if lo.y > 0.04 + OFF or (len(c) < 6000 and min(abs(lo.x), abs(hi.x)) > 0.13):  # straps; side zip pullers
        kill.update(c)
# Meshy fused the shoulder straps to the back: cut everything behind the back plane, press the rest onto it
kill.update(f for f in bm.faces if f.calc_center_median().y > YBK + 0.011)
bmesh.ops.delete(bm, geom=list(kill), context="FACES")
for v in bm.verts:
    if v.co.y > YBK + 0.003:
        v.co.y = YBK + 0.003
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
bm.to_mesh(me)
bm.free()
me.update()

# ------------------------------------------------------------------ sample the generated front (rays from -Y)
me.calc_loop_triangles()
uvl = me.uv_layers.active.data
TRI = [tuple(t.vertices) for t in me.loop_triangles]
TRIL = [tuple(t.loops) for t in me.loop_triangles]
TRIUV = [tuple(Vector((*uvl[l].uv, 0)) for l in tl) for tl in TRIL]
CO = [v.co.copy() for v in me.vertices]
bvh = BVHTree.FromPolygons(CO, TRI)


def hit(x, z):
    loc, n, ti, d = bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
    if loc is None:
        return None
    a, b, c = (CO[i] for i in TRI[ti])
    la, lb, lc = TRIUV[ti]
    uv = barycentric_transform(loc, a, b, c, la, lb, lc)
    return loc, (uv.x, uv.y)


def front(x, z):
    """Front surface at (x, z); the generator left the upper right of the panel peeled open, so where one side sits
    clearly behind its mirror, the mirror is used (geometry and texture)."""
    h1, h2 = hit(x, z), hit(-x, z)
    if h1 is None and h2 is None:
        return None
    if h1 is None or (h2 is not None and z > 0.2 and (x > 0.0 or h1[0].y - h2[0].y > 0.006)):
        loc, uv = h2
        return Vector((x, loc.y, z)), uv, True
    return h1[0], h1[1], False


def row_extent(z):
    xs = [i * 0.004 for i in range(0, 46)]
    best = None
    for x in xs:
        f = front(x, z)
        if f and f[0].y < YCUT:
            best = x
    return best


rows = []
z = 0.012
while z < 0.45:
    xr = row_extent(z)
    if xr is None or xr < 0.012:
        break
    rows.append((z, xr))
    z += 0.007
NC = 36
# ---- bake the panel texture: texel (u, v) -> panel point -> generated surface (mirror rule) -> source texel
import numpy as np
SRC = base_color_image(ob)
sw, sh = SRC.size
SA = np.empty(sw * sh * 4, np.float32)
SRC.pixels.foreach_get(SA)
SA = SA.reshape(sh, sw, 4)
TW, TH_ = 384, 480
TEX = np.ones((TH_, TW, 4), np.float32)
RZ = [z for z, _ in rows]
RX = [xr for _, xr in rows]
for ty in range(TH_):
    fv = (ty + 0.5) / TH_ * (len(rows) - 1)
    j0 = min(int(fv), len(rows) - 2)
    t = fv - j0
    z = lerp(RZ[j0], RZ[j0 + 1], t)
    xr = lerp(RX[j0], RX[j0 + 1], t)
    for tx in range(TW):
        x = lerp(-xr, xr, (tx + 0.5) / TW)
        fr = front(x, z)
        if fr is None:
            continue
        uu, vv = fr[1]
        TEX[ty, tx] = SA[min(sh - 1, max(0, int((vv % 1.0) * sh))), min(sw - 1, max(0, int((uu % 1.0) * sw)))]
ptex = bpy.data.images.new("panel_tex", TW, TH_)
ptex.pixels.foreach_set(TEX.ravel())
ptex.pack()
pmat = ob.data.materials[0].copy()
pmat.name = "panel_fabric"
for n in pmat.node_tree.nodes:
    if n.type == "TEX_IMAGE" and n.image == SRC:
        n.image = ptex
    elif n.type == "TEX_IMAGE":  # source normal/ORM maps don't match the new UVs
        for l in list(n.outputs[0].links) + list(n.outputs[1].links if len(n.outputs) > 1 else []):
            pmat.node_tree.links.remove(l)
mirrored = 0
outer, uvs, colors = [], [], []
for (z, xr) in rows:
    for i in range(NC + 1):
        u = i / NC
        x = lerp(-xr, xr, u)
        f = front(x, z)
        y = min(f[0].y, YCUT) if f else YCUT
        if i in (0, NC):
            y = YCUT
        outer.append(Vector((x, y, z)))
        uvs.append(f[1] if f else (0, 0))
        mirrored += int(bool(f and f[2]))
        colors.append(samp(f[1]) if f else (1, 1, 1))
NR = len(rows)
report["panel"] = {"rows": NR, "cols": NC + 1, "mirrored_samples": mirrored, "top_z": round(rows[-1][0], 3)}

# remove the generated panel (everything in front of the zip plane) + leftovers inside the opening
bm = bmesh.new()
bm.from_mesh(me)
xr_of = lambda zz: max([xr for (z_, xr) in rows if abs(z_ - zz) < 0.006] or [0.0])
dead = []
for f in bm.faces:
    c = f.calc_center_median()
    if c.y < YCUT - 0.001:
        dead.append(f)
    elif c.y < YCUT + 0.05 and abs(c.x) < xr_of(c.z) - 0.015 and ZB < c.z < rows[-1][0] - 0.015:
        dead.append(f)  # the generator's peeled lining sitting inside the opening
bmesh.ops.delete(bm, geom=dead, context="FACES")
bm.to_mesh(me)
bm.free()
me.update()
# decimate the body skin (Meshy is 150k tris)
ob.name = "body"
report["skin"] = {"verts_in": nv0, "verts_kept": len(me.vertices)}

# ------------------------------------------------------------------ panel mesh (outer skin + liner + zip tape edge)
liner_m = mat("liner", (srgb2lin(0.16), srgb2lin(0.165), srgb2lin(0.17)), 0.9)
tape_m = mat("zip_tape", (srgb2lin(0.12), srgb2lin(0.12), srgb2lin(0.125)), 0.6)
T = 0.004
W = NC + 1
inner = [v + Vector((0, T, 0)) for v in outer]
verts = outer + inner
faces, fmat = [], []
idx = lambda j, i, layer=0: layer * NR * W + j * W + i
for j in range(NR - 1):
    for i in range(NC):
        faces.append((idx(j, i), idx(j, i + 1), idx(j + 1, i + 1), idx(j + 1, i)))
        fmat.append(2 if i in (0, NC - 1) or j == NR - 2 else 0)
        faces.append((idx(j, i, 1), idx(j + 1, i, 1), idx(j + 1, i + 1, 1), idx(j, i + 1, 1)))
        fmat.append(1)
ring = [idx(j, 0) for j in range(NR)] + [idx(NR - 1, i) for i in range(1, W)] + [idx(j, NC) for j in range(NR - 2, -1, -1)] + \
       [idx(0, i) for i in range(NC - 1, 0, -1)]
for a, b in zip(ring, ring[1:] + ring[:1]):
    faces.append((b, a, a + NR * W, b + NR * W))
    fmat.append(2)
panel = new_mesh_obj("panel", verts, faces, [pmat, liner_m, tape_m])
pm = panel.data
for p, m_ in zip(pm.polygons, fmat):
    p.material_index = m_
uvp = pm.uv_layers.new(name="UVMap")


def tri_under(x, z):
    """Source triangle for a panel face centred at (x, z), honouring the same mirror rule as front()."""
    r1 = bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))  # (legacy helper, unused)
    r2 = bvh.ray_cast(Vector((-x, -1.0, z)), Vector((0, 1, 0)))
    if r1[0] is None or (r2[0] is not None and z > 0.2 and r1[0].y - r2[0].y > 0.006):
        return (r2[2], True) if r2[0] is not None else (None, False)
    return r1[2], False


for p in pm.polygons:
    for li in p.loop_indices:
        vi = pm.loops[li].vertex_index % (NR * W)
        uvp.data[li].uv = ((vi % W) / NC, (vi // W) / (NR - 1))

# ------------------------------------------------------------------ body liner (inside of the bag, dark)
liner = ob.copy()
liner.data = ob.data.copy()
liner.name = "liner"
bpy.context.scene.collection.objects.link(liner)
lm = liner.data
for v in lm.vertices:
    v.co -= v.normal * 0.006
lm.flip_normals()
lm.materials.clear()
lm.materials.append(liner_m)

# ------------------------------------------------------------------ zip path (right bottom -> over the top -> left bottom)
jb = next(j for j, (z, _) in enumerate(rows) if z >= ZB)
path_idx = [idx(j, NC) for j in range(jb, NR)] + [idx(NR - 1, i) for i in range(NC - 1, 0, -1)] + [idx(j, 0) for j in range(NR - 1, jb - 1, -1)]
PATH = [outer[i] for i in path_idx]
ARC = [0.0]
for a, b in zip(PATH, PATH[1:]):
    ARC.append(ARC[-1] + (b - a).length)
LZ = ARC[-1]


def path_at(L):
    L = max(0.0, min(LZ, L))
    for k in range(len(ARC) - 1):
        if ARC[k + 1] >= L:
            t = (L - ARC[k]) / max(1e-9, ARC[k + 1] - ARC[k])
            return PATH[k].lerp(PATH[k + 1], t), (PATH[k + 1] - PATH[k]).normalized()
    return PATH[-1], (PATH[-1] - PATH[-2]).normalized()


def outward(p):
    o = Vector((p.x, 0, p.z - 0.2))
    o.y = 0
    return (o.normalized() * 0.8 + Vector((0, -0.6, 0))).normalized()


NK = 12
HINGE_Y, HINGE_Z = YCUT, ZB
rest_all = verts


def panel_shape(s):
    """Panel vertex positions for zip = s."""
    Lz = s * LZ
    zipped = [PATH[k] for k in range(len(PATH)) if ARC[k] > Lz + 0.01]
    kd = None
    if zipped:
        kd = KDTree(len(zipped))
        for k, p in enumerate(zipped):
            kd.insert(p, k)
        kd.balance()
    TH = math.radians(98) * smoothstep(0.1, 1.0, s) ** 1.15
    out = []
    for vi, v in enumerate(rest_all):
        r = outer[vi % (NR * W)]
        d = kd.find(r)[2] if kd else 1.0
        w = smoothstep(0.0, 0.15, d) * smoothstep(ZB - 0.005, ZB + 0.06, r.z)
        sag = math.radians(16) * math.sin(TH) * smoothstep(ZB, 0.4, r.z)
        a = TH * w + sag * w
        dy, dz = v.y - HINGE_Y, v.z - HINGE_Z
        y2 = HINGE_Y + dy * math.cos(a) - dz * math.sin(a)
        z2 = HINGE_Z + dy * math.sin(a) + dz * math.cos(a)
        z2 = max(z2, 0.003 + (0.004 if vi >= NR * W else 0.0))  # lies on the floor, not through it
        out.append(Vector((v.x, y2, z2)))
    return out


panel.shape_key_add(name="Basis", from_mix=False)
for k in range(1, NK + 1):
    kb = panel.shape_key_add(name=f"zip_{k:02d}", from_mix=False)
    for vi, co in enumerate(panel_shape(k / NK)):
        kb.data[vi].co = co
# pocket bulge
PX, PZ0, PZ1 = 0.117, 0.03, 0.193
kb = panel.shape_key_add(name="pocket", from_mix=False)
for vi, v in enumerate(rest_all):
    r = outer[vi % (NR * W)]
    if abs(r.x) < PX and PZ0 < r.z < PZ1:
        e = min(PX - abs(r.x), r.z - PZ0, PZ1 - r.z)
        b = smoothstep(0.0, 0.035, e)
        kb.data[vi].co = v + Vector((0, -0.022 * b, 0.002 * b))

# ------------------------------------------------------------------ armature
arm = new_armature("daypack_rig")
Bn = Bones(arm)
Bn.add("root", (0, 0, 0), (0, 0, 0.1))
Bn.add("fill_top", P(0, -0.06, 0.40), P(0, -0.06, 0.45), "root")
Bn.add("fill_front", P(0, -0.153, 0.2), P(0, -0.2, 0.2), "root")
Bn.add("fill_side.L", P(0.167, -0.06, 0.2), P(0.21, -0.06, 0.2), "root")
Bn.add("fill_side.R", P(-0.167, -0.06, 0.2), P(-0.21, -0.06, 0.2), "root")
p0, t0 = path_at(0.0)
Bn.add("slider", p0 + outward(p0) * 0.006, p0 + outward(p0) * 0.006 + t0 * 0.03, "root", up=outward(p0))
sp = p0 + outward(p0) * 0.012
Bn.chain("pull.", [sp, sp + DOWN * 0.022, sp + DOWN * 0.044], parent="slider", up=Vector((0, -1, 0)))
SS = ShoulderStraps(top=lambda sx: P(sx * 0.06, 0.04, 0.37), bottom=lambda sx: P(sx * 0.13, 0.04, 0.03), lp=0.42,
                    web=(0.06, 0.19), web_tot=0.30, s_def=0.4, lift=(0.04, 0.13))
SS.add_bones(Bn)
Bn.build()

FILL_BONES = ["fill_top", "fill_front", "fill_side.L", "fill_side.R"]


def fill_w(v):
    u = v.x / 0.167
    vv = (YBK - v.y) / (YBK - YF)
    h = v.z / 0.40
    wf = smoothstep(0.35, 0.95, vv) * smoothstep(0.04, 0.3, h) * (1 - 0.5 * smoothstep(0.8, 1.0, h)) * (1 - 0.5 * u * u)
    wt = smoothstep(0.6, 0.98, h) * (0.3 + 0.7 * smoothstep(0.1, 0.6, vv))
    wl = smoothstep(0.35, 1.0, u) * smoothstep(0.04, 0.3, h) * (1 - 0.5 * smoothstep(0.85, 1.0, h))
    wr = smoothstep(0.35, 1.0, -u) * smoothstep(0.04, 0.3, h) * (1 - 0.5 * smoothstep(0.85, 1.0, h))
    tot = wf + wt + wl + wr
    if tot > 1:
        wf, wt, wl, wr = wf / tot, wt / tot, wl / tot, wr / tot
    return {"fill_front": wf, "fill_top": wt, "fill_side.L": wl, "fill_side.R": wr, "root": max(0.0, 1 - tot)}


def fill_groups(cos):
    G = {n: [0.0] * len(cos) for n in FILL_BONES + ["root"]}
    for i, c in enumerate(cos):
        for k, w in fill_w(c).items():
            G[k][i] = w
    return G


for o in (ob, liner):
    skin(o, arm, fill_groups([v.co for v in o.data.vertices]))
skin(panel, arm, fill_groups([outer[i % (NR * W)] for i in range(len(verts))]))
# slack folds on the body for the empty pack
F0 = 0.6
ob.shape_key_add(name="Basis", from_mix=False)
sk = ob.shape_key_add(name="slack", from_mix=False)
for i, v in enumerate(me.vertices):
    w = sum(fill_w(v.co)[k] for k in ("fill_front", "fill_side.L", "fill_side.R"))
    if w > 1e-3:
        fold = math.sin(2 * math.pi * v.co.z / 0.05 + 2.5 * math.sin(2 * math.pi * v.co.x / 0.21) + 1.7 * math.sin(2 * math.pi * v.co.y / 0.17))
        sk.data[i].co = v.co + v.normal * 0.003 * fold * min(1.0, w)
SLACK = f"min(max(({F0} - p) / {F0}, 0.0), 1.0)"
drive_shape_key(sk, arm, "fill", SLACK)
ZIPX = {f"zip_{k:02d}": f"max(0.0, 1.0 - abs(min(max(p, 0.0), 1.0) * {NK} - {k}))" for k in range(1, NK + 1)}
for kn, ex in ZIPX.items():
    drive_shape_key(panel.data.shape_keys.key_blocks[kn], arm, "zip", ex)
POCKX = "min(max(p, 0.0), 1.0)"
drive_shape_key(panel.data.shape_keys.key_blocks["pocket"], arm, "pocket_fill", POCKX)

# ------------------------------------------------------------------ rigid + strap parts
plast = mat("buckle_plastic", (srgb2lin(0.05), srgb2lin(0.05), srgb2lin(0.055)), 0.45)
metal = mat("zip_metal", (0.35, 0.36, 0.38), 0.35, 0.9)
pad_m = mat("strap_pad", (srgb2lin(0.22), srgb2lin(0.22), srgb2lin(0.23)), 0.9)
web_m = mat("webbing", (srgb2lin(0.19), srgb2lin(0.19), srgb2lin(0.2)), 0.8)
parts = SS.build_meshes(arm, pad_m, web_m, plast)
# slider body: a small rounded box on the zip
o_ = outward(p0)
sl = buckle_female("zip_slider", p0 + o_ * 0.002 - t0 * 0.012, t0, o_, w=0.011, l=0.024, t=0.008, material=metal)
rigid_to_bone(sl, arm, "slider")
pts = [sp, sp + DOWN * 0.022, sp + DOWN * 0.044]
pl_ob, _ = strap_object("zip_pull", resample(pts, 0.004), [Vector((0, -1, 0))] * len(resample(pts, 0.004)), 0.008, 0.003, metal)
skin(pl_ob, arm, chain_weights([v.co for v in pl_ob.data.vertices], pts, ["pull.0", "pull.1"], falloff=0.4))
# cord loop on the puller
cord = mat("cord", (srgb2lin(0.18), srgb2lin(0.18), srgb2lin(0.19)), 0.8)
cl = [pts[-1] + Vector((0.005 * math.sin(a), 0, -0.018 * (1 - math.cos(a)) / 2 * 2)) for a in [i * math.pi * 2 / 16 for i in range(17)]]
c_ob, _ = strap_object("zip_cord", cl, [Vector((0, -1, 0))] * len(cl), 0.004, 0.004, cord)
skin(c_ob, arm, {"pull.1": [1.0] * len(c_ob.data.vertices)})
# back panel (padded), covers where the generated straps were cut off
bp_v, bp_f = [], []
NX, NZ = 14, 18
for j in range(NZ + 1):
    for i in range(NX + 1):
        z = lerp(0.04, 0.345, j / NZ)
        prof = [(0.0, 0.15), (0.2, 0.15), (0.26, 0.135), (0.30, 0.122), (0.34, 0.098), (0.36, 0.085)]
        hw = next(lerp(w0, w1, (z - z0) / (z1 - z0)) for (z0, w0), (z1, w1) in zip(prof, prof[1:]) if z0 <= z <= z1) - 0.015
        x = lerp(-hw, hw, i / NX)
        r = 0.006 * (1 - (2 * i / NX - 1) ** 2) * (1 - (2 * j / NZ - 1) ** 4) + 0.003
        bp_v.append(Vector((x, YBK + r, z)))
for j in range(NZ):
    for i in range(NX):
        a = j * (NX + 1) + i
        bp_f.append((a, a + NX + 1, a + NX + 2, a + 1))
backp = new_mesh_obj("back_panel", bp_v, bp_f, [pad_m])
skin(backp, arm, {"root": [1.0] * len(bp_v)})
parts += [sl, pl_ob, c_ob, backp]
# zip track: a clean tape swept along the whole panel outline, covering the generator's noisy zip-tape edge
track = [outer[i] + Vector((0, -0.001, 0)) for i in ring] + [outer[ring[0]] + Vector((0, -0.001, 0))]
track = resample(track, 0.006)
tr_ob, _ = strap_object("zip_track", track, [Vector((0, -1, 0))] * len(track), 0.018, 0.005, tape_m, seg=2)
skin(tr_ob, arm, fill_groups([v.co for v in tr_ob.data.vertices]))
parts.append(tr_ob)


# ------------------------------------------------------------------ controls
def pose_fill(f):
    e = max(0.0, (F0 - f) / F0)
    q = max(0.0, (f - F0) / (1 - F0))
    T_ = {"fill_top": Vector((0, 0.01 * e, -0.045 * e + 0.01 * q)), "fill_front": Vector((0, 0.03 * e - 0.025 * q, -0.01 * e))}
    for side, sx in (("L", 1), ("R", -1)):
        T_[f"fill_side.{side}"] = Vector((-sx * 0.022 * e + sx * 0.014 * q, 0, -0.006 * e))
    return {bn: rest(arm, bn).inverted() @ Matrix.Translation(t) @ rest(arm, bn) for bn, t in T_.items()}


act_fill = control_action(arm, "fill", FILL_BONES, pose_fill)


def pose_zip(s):
    p, t = path_at(s * LZ)
    o_ = outward(p)
    M = aim_matrix(rest(arm, "slider"), p + o_ * 0.006, t, 1.0, up_hint=o_)
    out = {"slider": rest(arm, "slider").inverted() @ M}
    # the puller hangs from the slider: point it down in armature space
    for bn in ("pull.0", "pull.1"):
        b = arm.data.bones[bn]
        Pm = M if bn == "pull.0" else Mp
        head = (Pm @ (b.parent.matrix_local.inverted() @ b.matrix_local)).translation if bn == "pull.0" else Mp @ Vector((0, arm.data.bones["pull.0"].length, 0))
        Mb = aim_matrix(b.matrix_local, head, DOWN + o_ * 0.25, 1.0)
        out[bn] = (Pm @ (b.parent.matrix_local.inverted() @ b.matrix_local)).inverted() @ Mb
        Mp = Mb
    return out


Mp = None
ZIP_BONES = ["slider", "pull.0", "pull.1"]
act_zip = control_action(arm, "zip", ZIP_BONES, pose_zip, nsamp=48)
act_strap = control_action(arm, "strap_length", SS.bones(), lambda s: SS.pose(arm, s))
wire_control(arm, "fill", act_fill, FILL_BONES, F0)
wire_control(arm, "zip", act_zip, ZIP_BONES, 0.0)
wire_control(arm, "strap_length", act_strap, SS.bones(), SS.S_DEF)
arm["pocket_fill"] = 0.0
arm.id_properties_ui("pocket_fill").update(min=-1.0, max=2.0, soft_min=0.0, soft_max=1.0, default=0.0)

spec = {
    "anymachine": "soft-goods/v0", "bag": "daypack", "height": H,
    "controls": [
        {"param": "zip", "type": "zip_path", "default": 0.0, "range": [0, 1], "bones": ZIP_BONES,
         "shape_keys": [f"panel:{k}" for k in ZIPX], "shape_key_expr": {k: v.replace("min(max(p, 0.0), 1.0)", "p") for k, v in ZIPX.items()},
         "map": f"slider arclength = zip * {LZ:.3f} m along the U path (right side up, over the top, down the left); panel opening angle 0..98 deg about the bottom hinge, pinned within 15 cm of still-zipped teeth; {NK} in-between shape keys"},
        {"param": "pocket_fill", "type": "fill", "default": 0.0, "range": [0, 1], "bones": [], "shape_keys": ["panel:pocket"],
         "shape_key_expr": {"pocket": "p"}, "map": "front pocket bulges 2.2 cm"},
        {"param": "fill", "type": "fill", "default": F0, "range": [0, 1], "bones": FILL_BONES, "shape_keys": ["body:slack"],
         "shape_key_expr": {"slack": SLACK}, "map": "0 = empty (top drops 4.5 cm, front caves 3 cm, slack folds); 0.6 = generated; 1 = bulging"},
        {"param": "strap_length", "type": "strap", "default": SS.S_DEF, "range": [0, 1], "bones": SS.bones(),
         "map": "webbing below the adjuster 6..19 cm; tail = 30 cm - webbing"},
    ],
    "jiggle": {"chains": [{"prefix": "pull.", "k": 30, "c": 2.5}] + [{"prefix": f"tail.{s}_", "k": 40, "c": 3.0} for s in "LR"]},
    "demo": {"keys": [[1, {}], [12, {"zip": 0}], [60, {"zip": 0.5}], [72, {"zip": 0.5}], [110, {"zip": 1}], [140, {"zip": 1}],
                      [190, {"zip": 0}], [196, {"pocket_fill": 0}], [218, {"pocket_fill": 1}], [236, {"pocket_fill": 1}],
                      [254, {"pocket_fill": 0}], [260, {"fill": F0}], [284, {"fill": 0}], [298, {"fill": 0}], [324, {"fill": 1}],
                      [336, {"fill": 1}], [350, {"fill": F0}], [354, {"strap_length": 0.4}], [374, {"strap_length": 1}],
                      [396, {"strap_length": 0}], [410, {"strap_length": 0.4}]], "bob": [[414, 462]]},
    "check": {
        "body": "body",
        "moving": [{"name": "panel", "object": "panel", "exclude_ring_m": 0.02},
                   {"name": "zip_slider", "object": "zip_slider"}, {"name": "zip_pull", "object": "zip_pull"},
                   {"name": "strap.L", "object": "strap.L", "exclude_near": [[list(SS.rest["L"]["pad"][0]), 0.03]]},
                   {"name": "strap.R", "object": "strap.R", "exclude_near": [[list(SS.rest["R"]["pad"][0]), 0.03]]}],
        "pairs": [["zip", "fill"], ["zip", "pocket_fill"], ["fill", "strap_length"]],
        "floor": ["panel", "zip_pull"],
    },
    "zip_path_m": round(LZ, 4),
}
# panel-edge exclusion for the check: vertices on the zip ring touch the body by construction
ring_set = set(ring) | {r + NR * W for r in ring}
spec["check"]["moving"][0]["exclude_verts"] = sorted(ring_set)
arm["anymachine"] = json.dumps(spec)
report.update({"zip_path_m": round(LZ, 3), "bones": len(arm.data.bones), "controls": [c["param"] for c in spec["controls"]]})
bpy.context.scene.render.fps = 24
set_controls(arm, {"fill": F0, "zip": 0.0, "strap_length": SS.S_DEF, "pocket_fill": 0.0})
save(OUT)
json.dump(report, open(OUT.replace(".blend", "_build.json"), "w"), indent=1)
print("BUILT", json.dumps(report), flush=True)
