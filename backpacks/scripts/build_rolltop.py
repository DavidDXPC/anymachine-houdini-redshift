"""Bag 3: roll-top. Generated Tripo skin (body kept below the roll) -> rebuilt collar that really rolls.

blender -b --factory-startup --python build_rolltop.py -- --glb gen/rolltop_tripo/model.glb --out out/rolltop/rolltop.blend

Controls (custom props on `rolltop_rig`, 0..1, clamped):
  roll          0..3 turns: the top of a flattened collar tube curls into an Archimedean spiral (40-bone chain,
                curvature 1/r(d) from the tip, r = sqrt(r0^2 + t d / pi)); the roll travels down as it grows
  clip          side straps swing up and the female buckles meet the male buckles at the roll ends
                (valid at roll = 1: a dependent joint, see NOTES)
  fill          body sag/bulge (deformer bones + slack folds); the collar rides on the body top
  strap_length  shoulder straps
Baked jiggle: strap tails.
"""
import bpy, bmesh, sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
from softlib import *
from rig_parts import *
from straps import ShoulderStraps
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
GLB, OUT = os.path.abspath(opt("--glb")), os.path.abspath(opt("--out"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
report = {"bag": "rolltop", "glb": GLB}
ob = load_gen(GLB, -90, 0.50)
fix_gen_material(ob, rough=0.6)
me = ob.data
OFF = -((-0.165) + 0.052) / 2
me.transform(Matrix.Translation((0, OFF, 0)))
P = lambda x, y, z: Vector((x, y + OFF, z))
YBK, YF = 0.050 + OFF, -0.165 + OFF
ZC = 0.385  # the generated roll + buckles sit above this; the body is cut here
samp = tex_sampler(ob)

bm = bmesh.new()
bm.from_mesh(me)
nv0 = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
uvl = bm.loops.layers.uv.active
cols = []
for f in bm.faces:
    c = f.calc_center_median()
    if 0.25 < c.z < 0.35 and abs(c.x) < 0.1 and c.y < YF + 0.03:
        us = [l[uvl].uv for l in f.loops]
        cols.append(samp((sum(u[0] for u in us) / len(us), sum(u[1] for u in us) / len(us))))
tint = [sorted(c[i] for c in cols)[len(cols) // 2] for i in range(3)]
# cut at the roll, cut the fused shoulder straps off the back
kill = [f for f in bm.faces if (lambda c: c.z > ZC or c.y > YBK + 0.011)(f.calc_center_median())]
bmesh.ops.delete(bm, geom=kill, context="FACES")
for v in bm.verts:
    if v.co.y > YBK + 0.003:
        v.co.y = YBK + 0.003
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
# the rim: boundary verts near the cut define the collar's bottom ring
rim = [v.co.copy() for v in bm.verts if v.is_boundary and v.co.z > ZC - 0.02]
bm.to_mesh(me)
bm.free()
me.update()
ob.name = "body"
report["skin"] = {"verts_in": nv0, "verts_kept": len(me.vertices), "tint_srgb": [round(x, 3) for x in tint]}

# rim cross-section: for each angle, the farthest rim point in that direction from the centre
yc = sum(p.y for p in rim) / len(rim)
NK = 48
ring = []
for k in range(NK):
    a = 2 * math.pi * k / NK
    d = Vector((math.cos(a), math.sin(a), 0))
    best = max(rim, key=lambda p: (Vector((p.x, p.y - yc, 0))).normalized().dot(d) * 10 + Vector((p.x, p.y - yc, 0)).length)
    # project: radius along d where rim points lie within 15 deg
    cand = [p for p in rim if Vector((p.x, p.y - yc, 0)).length > 1e-4 and Vector((p.x, p.y - yc, 0)).normalized().dot(d) > math.cos(math.radians(6))]
    r = max((Vector((p.x, p.y - yc, 0)).length for p in cand), default=Vector((best.x, best.y - yc, 0)).length)
    ring.append(Vector((d.x * r, d.y * r, 0)))
W2 = max(abs(p.x) for p in ring)
D2 = max(abs(p.y) for p in ring)
report["rim"] = {"half_width": round(W2, 3), "half_depth": round(D2, 3), "yc": round(yc, 4)}

# ------------------------------------------------------------------ collar tube
HC, SEG = 0.40, 0.006
NB = int(round(HC / SEG))
FLAT = 0.0016  # half thickness of the flattened collar (two layers of coated fabric)
LEVELS = [i * 0.005 for i in range(int(HC / 0.005) + 1)]
cverts = []
for a in LEVELS:
    t = smoothstep(0.0, 0.045, a)
    for p in ring:
        # flatten the opening: depth -> FLAT, width grows a little (perimeter is kept roughly)
        x = p.x * lerp(1.0, 1.06, t)
        y = p.y * lerp(1.0, FLAT / D2, t)
        cverts.append(Vector((x, yc + y, ZC - 0.004 + a)))
cfaces = []
NL = len(LEVELS)
for j in range(NL - 1):
    for k in range(NK):
        a, b = j * NK + k, j * NK + (k + 1) % NK
        cfaces.append((a, b, b + NK, a + NK))
cfaces.append(tuple((NL - 1) * NK + k for k in range(NK)))  # sealed top (the welded stiffener edge)
coat = mat("collar_coated", tuple(srgb2lin(c) for c in tint), 0.55)
stiff = mat("stiffener", (srgb2lin(0.05), srgb2lin(0.05), srgb2lin(0.055)), 0.5)
collar = new_mesh_obj("collar", cverts, cfaces, [coat, stiff])
for p in collar.data.polygons:
    if min(collar.data.vertices[i].co.z for i in p.vertices) > ZC - 0.004 + HC - 0.022:
        p.material_index = 1

# ------------------------------------------------------------------ armature
arm = new_armature("rolltop_rig")
Bn = Bones(arm)
Bn.add("root", (0, 0, 0), (0, 0, 0.1))
Bn.add("fill_top", Vector((0, yc, ZC)), Vector((0, yc, ZC + 0.04)), "root")
Bn.add("fill_front", P(0, -0.165, 0.2), P(0, -0.21, 0.2), "root")
Bn.add("fill_side.L", P(0.172, -0.05, 0.2), P(0.215, -0.05, 0.2), "root")
Bn.add("fill_side.R", P(-0.172, -0.05, 0.2), P(-0.215, -0.05, 0.2), "root")
CH = [Vector((0, yc, ZC - 0.004 + i * SEG)) for i in range(NB + 1)]
roll = Bn.chain("roll.", CH, parent="fill_top", up=Vector((0, -1, 0)))
BX = W2 * 1.06 + 0.012
for side, sx in (("L", 1), ("R", -1)):
    tip = CH[-1]
    Bn.add(f"mbuck.{side}", tip + Vector((sx * BX, 0, 0)), tip + Vector((sx * BX, 0, -0.03)), "fill_top", up=Vector((0, -1, 0)))
    anc = Vector((sx * 0.172, yc, 0.24))
    Bn.add(f"side.{side}", anc, anc + Vector((0, 0, -0.08)), f"fill_side.{side}", up=Vector((sx, 0, 0)))
    Bn.add(f"fbuck.{side}", anc + Vector((0, 0, -0.08)), anc + Vector((0, 0, -0.11)), f"fill_side.{side}", up=Vector((sx, 0, 0)))
SS = ShoulderStraps(top=lambda sx: P(sx * 0.065, 0.055, 0.36), bottom=lambda sx: P(sx * 0.13, 0.055, 0.03), lp=0.44,
                    web=(0.06, 0.20), web_tot=0.32, s_def=0.4, lift=(0.05, 0.14))
SS.add_bones(Bn)
Bn.build()
FILL_BONES = ["fill_top", "fill_front", "fill_side.L", "fill_side.R"]


def fill_w(v):
    u = v.x / 0.172
    vv = (YBK - v.y) / (YBK - YF)
    h = v.z / ZC
    rimfade = 1 - smoothstep(0.82, 0.99, h)
    wf = smoothstep(0.35, 0.95, vv) * smoothstep(0.04, 0.3, h) * rimfade * (1 - 0.5 * u * u)
    wt = smoothstep(0.55, 0.99, h)
    wl = smoothstep(0.35, 1.0, u) * smoothstep(0.04, 0.3, h) * rimfade
    wr = smoothstep(0.35, 1.0, -u) * smoothstep(0.04, 0.3, h) * rimfade
    tot = wf + wt + wl + wr
    if tot > 1:
        wf, wt, wl, wr = wf / tot, wt / tot, wl / tot, wr / tot
    return {"fill_front": wf, "fill_top": wt, "fill_side.L": wl, "fill_side.R": wr, "root": max(0.0, 1 - tot)}


G = {n: [0.0] * len(me.vertices) for n in FILL_BONES + ["root"]}
for i, v in enumerate(me.vertices):
    for k, w in fill_w(v.co).items():
        G[k][i] = w
skin(ob, arm, G)
F0 = 0.6
ob.shape_key_add(name="Basis", from_mix=False)
sk = ob.shape_key_add(name="slack", from_mix=False)
for i, v in enumerate(me.vertices):
    w = sum(fill_w(v.co)[k] for k in ("fill_front", "fill_side.L", "fill_side.R"))
    if w > 1e-3:
        fold = math.sin(2 * math.pi * v.co.z / 0.06 + 2.2 * math.sin(2 * math.pi * v.co.x / 0.24) + 1.5 * math.sin(2 * math.pi * v.co.y / 0.2))
        sk.data[i].co = v.co + v.normal * 0.0035 * fold * min(1.0, w)
SLACK = f"min(max(({F0} - p) / {F0}, 0.0), 1.0)"
drive_shape_key(sk, arm, "fill", SLACK)
# collar weights: by height along the chain
cw = chain_weights([Vector((0, yc, v.co.z)) for v in collar.data.vertices], CH, roll, falloff=0.5)
skin(collar, arm, cw)

# ------------------------------------------------------------------ parts
plast = mat("buckle_plastic", (srgb2lin(0.05), srgb2lin(0.05), srgb2lin(0.055)), 0.45)
web_m = mat("webbing", (srgb2lin(0.06), srgb2lin(0.06), srgb2lin(0.065)), 0.8)
pad_m = mat("strap_pad", (srgb2lin(0.07), srgb2lin(0.07), srgb2lin(0.075)), 0.85)
parts = SS.build_meshes(arm, pad_m, web_m, plast)
for side, sx in (("L", 1), ("R", -1)):
    mb = arm.data.bones[f"mbuck.{side}"]
    m = buckle_male(f"buckle_m.{side}", mb.head_local, DOWN, Vector((sx, 0, 0)), material=plast)
    rigid_to_bone(m, arm, f"mbuck.{side}")
    # short tab from the collar edge to the buckle
    tab_pts = [mb.head_local - Vector((sx * 0.016, 0, -0.004)), mb.head_local + Vector((0, 0, 0.004))]
    t_ob, _ = strap_object(f"tab.{side}", resample(tab_pts, 0.004), [Vector((0, -1, 0))] * len(resample(tab_pts, 0.004)), 0.02, 0.003, web_m)
    skin(t_ob, arm, {f"mbuck.{side}": [1.0] * len(t_ob.data.vertices)})
    sb = arm.data.bones[f"side.{side}"]
    pts = [sb.head_local.lerp(sb.tail_local, t / 8) + Vector((sx * 0.004, 0, 0)) for t in range(9)]
    s_ob, _ = strap_object(f"sidestrap.{side}", pts, [Vector((sx, 0, 0))] * 9, 0.02, 0.003, web_m)
    skin(s_ob, arm, {f"side.{side}": [1.0] * len(s_ob.data.vertices)})
    fbb = arm.data.bones[f"fbuck.{side}"]
    fb = buckle_female(f"buckle_f.{side}", fbb.head_local + Vector((sx * 0.004, 0, 0)), DOWN, Vector((sx, 0, 0)), material=plast)
    rigid_to_bone(fb, arm, f"fbuck.{side}")
    parts += [m, t_ob, s_ob, fb]
# padded back panel over the cut strap roots
bp_v, bp_f = [], []
NX, NZ = 14, 18
for j in range(NZ + 1):
    for i in range(NX + 1):
        x, z = lerp(-0.14, 0.14, i / NX), lerp(0.08, 0.37, j / NZ)
        r = 0.006 * (1 - (2 * i / NX - 1) ** 2) * (1 - (2 * j / NZ - 1) ** 4) + 0.003
        bp_v.append(Vector((x, YBK + r, z)))
for j in range(NZ):
    for i in range(NX):
        a = j * (NX + 1) + i
        bp_f.append((a, a + NX + 1, a + NX + 2, a + 1))
backp = new_mesh_obj("back_panel", bp_v, bp_f, [pad_m])
skin(backp, arm, {"root": [1.0] * len(bp_v)})

# ------------------------------------------------------------------ controls
R0, TP, TURNS = 0.012, 0.007, 2.5


def rolled_len(n):
    return 2 * math.pi * n * R0 + math.pi * TP * n * n


LR_MAX = rolled_len(TURNS)
report["roll"] = {"rolled_length_m_at_3_turns": round(LR_MAX, 3), "collar_m": HC, "segments": NB}


def roll_pts(r):
    Lr = min(rolled_len(TURNS * r), HC - 0.01)
    pts = [CH[0].copy()]
    ang = 0.0
    for i in range(NB):
        d_hi = HC - i * SEG  # distance from the tip at this segment's start
        d_lo = HC - (i + 1) * SEG
        # rolled part of this segment: distances from the tip below Lr
        lo, hi = d_lo, min(d_hi, Lr)
        dang = 0.0
        if hi > lo:
            # integrate curvature 1/r(d) over [lo, hi]: d(theta)/dd = 1/sqrt(R0^2 + TP d / pi)
            F = lambda d: (2 * math.pi / TP) * math.sqrt(R0 * R0 + TP * d / math.pi)
            dang = F(hi) - F(lo)
        a_mid = ang + dang * 0.5
        pts.append(pts[-1] + Vector((0, -math.sin(a_mid), math.cos(a_mid))) * SEG)
        ang += dang
    return pts


def pose_roll(r):
    pts = roll_pts(r)
    out, armm = chain_locals(arm, roll, pts)
    tip = pts[-1]
    # buckles ride the roll ends (on short swivel tabs: they stay pointing down)
    for side, sx in (("L", 1), ("R", -1)):
        bn = f"mbuck.{side}"
        M = aim_matrix(rest(arm, bn), tip + Vector((sx * BX, 0, -0.006 if r > 0 else 0)), DOWN, 1.0)
        out[bn] = rest(arm, bn).inverted() @ M
    return out


ROLL_BONES = roll + ["mbuck.L", "mbuck.R"]
act_roll = control_action(arm, "roll", ROLL_BONES, pose_roll, nsamp=72)
tip1 = roll_pts(1.0)[-1]


def pose_clip(c):
    out = {}
    for side, sx in (("L", 1), ("R", -1)):
        sb, fb = arm.data.bones[f"side.{side}"], arm.data.bones[f"fbuck.{side}"]
        anc = sb.head_local
        male_bottom = tip1 + Vector((sx * BX, 0, -0.006 - 0.045 + 0.022))
        hang = anc + Vector((sx * 0.004, 0.0, -0.08))
        # swing the strap up the side through an arc away from the body
        d0 = (hang - anc).normalized()
        d1 = (male_bottom - anc).normalized()
        e = smoothstep(0.0, 1.0, c)
        d = d0.slerp(d1, e) if hasattr(d0, "slerp") else d0.lerp(d1, e).normalized()
        d = (d + Vector((sx * 0.35 * math.sin(math.pi * e), 0, 0))).normalized()
        L = lerp(0.08, (male_bottom - anc).length, e)
        end = anc + d * L
        Ms = aim_matrix(sb.matrix_local, anc, end - anc, L / sb.length)
        out[f"side.{side}"] = (rest(arm, f"fill_side.{side}") @ (arm.data.bones[f"fill_side.{side}"].matrix_local.inverted() @ sb.matrix_local)).inverted() @ Ms
        Mf = aim_matrix(fb.matrix_local, end, -d if e > 0.5 else d, 1.0) if False else aim_matrix(fb.matrix_local, end, d, 1.0)
        out[f"fbuck.{side}"] = (rest(arm, f"fill_side.{side}") @ (arm.data.bones[f"fill_side.{side}"].matrix_local.inverted() @ fb.matrix_local)).inverted() @ Mf
    return out


CLIP_BONES = ["side.L", "side.R", "fbuck.L", "fbuck.R"]
act_clip = control_action(arm, "clip", CLIP_BONES, pose_clip)


def pose_fill(f):
    e = max(0.0, (F0 - f) / F0)
    q = max(0.0, (f - F0) / (1 - F0))
    T_ = {"fill_top": Vector((0, 0.008 * e, -0.05 * e + 0.008 * q)), "fill_front": Vector((0, 0.055 * e - 0.025 * q, -0.01 * e))}
    for side, sx in (("L", 1), ("R", -1)):
        T_[f"fill_side.{side}"] = Vector((-sx * 0.022 * e + sx * 0.014 * q, 0, -0.006 * e))
    return {bn: rest(arm, bn).inverted() @ Matrix.Translation(t) @ rest(arm, bn) for bn, t in T_.items()}


act_fill = control_action(arm, "fill", FILL_BONES, pose_fill)
act_strap = control_action(arm, "strap_length", SS.bones(), lambda s: SS.pose(arm, s))
wire_control(arm, "roll", act_roll, ROLL_BONES, 1.0)
wire_control(arm, "clip", act_clip, CLIP_BONES, 1.0)
wire_control(arm, "fill", act_fill, FILL_BONES, F0)
wire_control(arm, "strap_length", act_strap, SS.bones(), SS.S_DEF)
lvl_excl = [i for i in range(len(collar.data.vertices)) if i < 6 * NK]  # bottom rings sit on the body rim
spec = {
    "anymachine": "soft-goods/v0", "bag": "rolltop", "height": 0.66,
    "controls": [
        {"param": "roll", "type": "roll", "default": 1.0, "range": [0, 1], "bones": ROLL_BONES,
         "map": f"turns = {TURNS} * roll; rolled length = 2 pi n r0 + pi t n^2 (r0 {R0} m = stiffener core, pitch {TP} m) = {LR_MAX:.3f} m at {TURNS} turns; 72-sample action"},
        {"param": "clip", "type": "strap", "default": 1.0, "range": [0, 1], "bones": CLIP_BONES, "requires": {"roll": 1.0},
         "map": "0 = side straps hang, buckles open; 1 = female buckles clipped onto the roll-end males (pose solved at roll = 1)"},
        {"param": "fill", "type": "fill", "default": F0, "range": [0, 1], "bones": FILL_BONES, "shape_keys": ["body:slack"],
         "shape_key_expr": {"slack": SLACK}, "map": "0 = empty (top drops 5 cm), 1 = bulging"},
        {"param": "strap_length", "type": "strap", "default": SS.S_DEF, "range": [0, 1], "bones": SS.bones(),
         "map": "webbing below the adjuster 6..20 cm"},
    ],
    "jiggle": {"chains": [{"prefix": f"tail.{s}_", "k": 40, "c": 3.0} for s in "LR"]},
    "demo": {"keys": [[1, {}], [12, {"clip": 1}], [36, {"clip": 0}], [44, {"roll": 1}], [104, {"roll": 0}], [124, {"roll": 0}],
                      [184, {"roll": 1}], [192, {"clip": 0}], [216, {"clip": 1}], [222, {"fill": F0}], [246, {"fill": 0}],
                      [258, {"fill": 0}], [284, {"fill": 1}], [296, {"fill": 1}], [310, {"fill": F0}], [314, {"strap_length": 0.4}],
                      [334, {"strap_length": 1}], [356, {"strap_length": 0}], [370, {"strap_length": 0.4}]], "bob": [[376, 424]]},
    "check": {
        "body": "body",
        "moving": [{"name": "collar", "object": "collar", "exclude_verts": lvl_excl},
                   {"name": "buckle_m.L", "object": "buckle_m.L"}, {"name": "buckle_m.R", "object": "buckle_m.R"},
                   {"name": "buckle_f.L", "object": "buckle_f.L"}, {"name": "buckle_f.R", "object": "buckle_f.R"},
                   {"name": "strap.L", "object": "strap.L", "exclude_near": [[list(SS.rest["L"]["pad"][0]), 0.03]]},
                   {"name": "strap.R", "object": "strap.R", "exclude_near": [[list(SS.rest["R"]["pad"][0]), 0.03]]}],
        "self": [{"object": "collar", "ring": NK, "min_level_gap": 4}],
        "pairs": [["roll", "fill"], ["roll", "clip"], ["fill", "strap_length"]],
    },
}
arm["anymachine"] = json.dumps(spec)
report.update({"bones": len(arm.data.bones), "controls": [c["param"] for c in spec["controls"]]})
set_controls(arm, {"roll": 1.0, "clip": 1.0, "fill": F0, "strap_length": SS.S_DEF})
save(OUT)
json.dump(report, open(OUT.replace(".blend", "_build.json"), "w"), indent=1)
print("BUILT", json.dumps(report), flush=True)
