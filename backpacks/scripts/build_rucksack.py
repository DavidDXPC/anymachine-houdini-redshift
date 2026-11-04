"""Bag 1: top-loading rucksack. Generated Tripo skin -> rigged soft rucksack.

blender -b --factory-startup --python build_rucksack.py -- --glb gen/rucksack_tripo/model.glb --out out/rucksack/rucksack.blend

Controls (custom props on `rucksack_rig`, each 0..1, clamped):
  fill          body sag <-> bulge (translation/rotation deformer bones + a 'slack' wrinkle shape key)
  lid_open      lid flap: 5-bone fabric chain (the generated lid skin, kept), hinge at the back-top seam
  strap_length  shoulder straps: padded strap re-curves, webbing below the adjuster lengthens, tail shortens
Baked: `jiggle` (lid-strap and strap-tail chains swing during a carry bob) -> demo action only.
"""
import bpy, bmesh, sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
from softlib import *
from rig_parts import *
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
GLB, OUT = os.path.abspath(opt("--glb")), os.path.abspath(opt("--out"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
report = {"bag": "rucksack", "glb": GLB}

# ------------------------------------------------------------------ skin: import, weld, segment
ob = load_gen(GLB, -90, 0.62)
fix_gen_material(ob, rough=0.8)
me = ob.data
samp = tex_sampler(ob)
bm = bmesh.new()
bm.from_mesh(me)
nv0 = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
uvl = bm.loops.layers.uv.active


def fcol(f):
    us = [l[uvl].uv for l in f.loops]
    return samp((sum(u[0] for u in us) / len(us), sum(u[1] for u in us) / len(us)))


def neutral(c):
    return max(c) - min(c) < 0.07


# (a) generated lid straps + buckles hang in front of the collar: found by texture (neutral black/grey) + region
kill = {f for f in bm.faces if (lambda c: c.z > 0.47 and c.y < -0.085 and c.z < 0.64 and abs(c.x) > 0.06)(f.calc_center_median())
        and neutral(fcol(f))}


# (b) components that live behind the back plane: shoulder straps, load lifters, hip pads
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


removed = []
for c in comps([f for f in bm.faces if f not in kill]):
    ys = [v.co.y for f in c for v in f.verts]
    zs = [v.co.z for f in c for v in f.verts]
    if min(ys) > 0.02 or (len(c) < 40 and max(zs) > 0.47 and min(ys) < -0.1):
        kill.update(c)
        removed.append((len(c), round(min(ys), 3), round(max(ys), 3)))
bmesh.ops.delete(bm, geom=list(kill), context="FACES")
# (c) what is left of the hip-belt / back pads behind the back plane gets pressed onto it
YB = 0.040
for v in bm.verts:
    if v.co.y > YB and v.co.z < 0.47:
        v.co.y = YB + (v.co.y - YB) * 0.15
bm.to_mesh(me)
bm.free()
me.update()
report["skin"] = {"verts_in": nv0, "verts_kept": len(me.vertices), "removed_components": len(removed)}

# recentre the body (not the straps) on y = 0
OFF = -((-0.218) + 0.035) / 2
me.transform(Matrix.Translation((0, OFF, 0)))
P = lambda x, y, z: Vector((x, y + OFF, z))
YF, YBK = -0.218 + OFF, 0.035 + OFF  # body front / back planes
ZT = 0.50  # body top
verts = [v.co.copy() for v in me.vertices]

# ------------------------------------------------------------------ armature
arm = new_armature("rucksack_rig")
B = Bones(arm)
X = Vector((1, 0, 0))
HINGE = P(0, 0.015, 0.465)
B.add("root", (0, 0, 0), (0, 0, 0.1))
B.add("fill_top", HINGE, HINGE + Vector((0.06, 0, 0)), "root")  # rotates the upper body about the hinge axis
B.add("fill_front", P(0, -0.22, 0.25), P(0, -0.27, 0.25), "root")
B.add("fill_side.L", P(0.175, -0.09, 0.25), P(0.225, -0.09, 0.25), "root")
B.add("fill_side.R", P(-0.175, -0.09, 0.25), P(-0.225, -0.09, 0.25), "root")
# lid chain along the generated (open) lid's outer centre-line profile, measured from the side ortho probe
LID_REST = [P(0, 0.015, 0.465), P(0, 0.035, 0.53), P(0, 0.02, 0.585), P(0, -0.02, 0.612), P(0, -0.075, 0.612), P(0, -0.135, 0.585)]
lid = B.chain("lid", LID_REST, parent="fill_top", up=Vector((0, 0, 1)))
LIDLEN = [(LID_REST[i + 1] - LID_REST[i]).length for i in range(len(lid))]

# shoulder straps --------------------------------------------------
LP, NPAD = 0.50, 9  # padded length, segments
WEB_TOT = 0.34  # webbing between adjuster and bottom anchor + free tail
SIDES = {"L": 1, "R": -1}


def strap_path(sx, s):
    """Shoulder-strap centre-line for strap_length s: top anchor A on the back panel, bottom anchor C at the bottom
    corner; a cubic whose bulge is solved so the length = padded + webbing(s)."""
    A = P(sx * 0.065, 0.045, 0.445)
    C = P(sx * 0.135, 0.045, 0.045)
    Lw = lerp(0.07, 0.21, s)

    def curve(beta):
        c1 = A + Vector((sx * 0.01, beta * 0.9, 0.05))
        c2 = C + Vector((sx * 0.01, beta, 0.16))
        pts = []
        for i in range(161):
            t = i / 160
            pts.append(A * (1 - t) ** 3 + c1 * 3 * t * (1 - t) ** 2 + c2 * 3 * t * t * (1 - t) + C * t ** 3)
        return pts

    def length(pts):
        return sum((b - a).length for a, b in zip(pts, pts[1:]))

    lo, hi = 0.0, 0.6
    for _ in range(40):
        mid = (lo + hi) / 2
        if length(curve(mid)) < LP + Lw:
            lo = mid
        else:
            hi = mid
    pts = curve((lo + hi) / 2)
    return pts, Lw


def split_path(pts, at_len):
    acc = 0.0
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        seg = (b - a).length
        if acc + seg >= at_len:
            q = a.lerp(b, (at_len - acc) / seg)
            return pts[:i + 1] + [q], [q] + pts[i + 1:]
        acc += seg
    return pts, [pts[-1]]


def strap_ups(pts):
    ups = []
    for i in range(len(pts)):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        u = t.cross(X)  # strap face normal lies in the y-z plane
        if u.y < 0 and i < len(pts) // 2:
            u = -u
        ups.append(u.normalized())
    # keep a consistent sign along the strap
    for i in range(1, len(ups)):
        if ups[i].dot(ups[i - 1]) < 0:
            ups[i] = -ups[i]
    return ups


S_DEF = 0.4
strap_rest = {}
for side, sx in SIDES.items():
    pts, Lw = strap_path(sx, S_DEF)
    pad, web = split_path(pts, LP)
    padpts = resample(pad, LP / NPAD)[:NPAD + 1]
    padpts[-1] = pad[-1]
    ups = strap_ups(padpts)
    names = B.chain(f"sh.{side}_", padpts, parent="root", ups=ups)
    B.add(f"web.{side}", padpts[-1], web[-1], names[-1], up=ups[-1])
    tail_len = WEB_TOT - Lw
    adj = padpts[-1]
    tail = [adj + Vector((0, 0.012, 0)) + DOWN * (tail_len * i / 3) for i in range(4)]
    tnames = B.chain(f"tail.{side}_", tail, parent=names[-1], up=Vector((0, 1, 0)))
    strap_rest[side] = dict(pad=padpts, ups=ups, names=names, web=web[-1], tail=tail, tnames=tnames, Lw=Lw)

# lid straps (rebuilt): anchor on the lid's front edge, two jiggle links, male buckle at the end
LS_LEN = [0.05, 0.045, 0.045]
LSX = 0.10
for side, sx in SIDES.items():
    a = LID_REST[-1] + Vector((sx * LSX, -0.004, 0))
    pts = [a + DOWN * sum(LS_LEN[:i]) for i in range(4)]
    B.chain(f"ls.{side}_", pts, parent=lid[-1], up=Vector((0, -1, 0)))
B.build()
for b in arm.data.bones:
    b.use_deform = True

# ------------------------------------------------------------------ body weights (fill deformer + lid)
u_ = lambda v: v.x / 0.175
v_ = lambda v: (YBK - v.y) / (YBK - YF)  # 0 back .. 1 front
h_ = lambda v: v.z / ZT


def lid_pred(c):
    return c.z > 0.525 or (c.z > 0.465 and c.y > -0.03 + OFF)


nv = len(verts)
lidw = [1.0 if lid_pred(v) else 0.0 for v in verts]
# smooth the lid mask across the hinge seam so the fabric bends instead of tearing
adj = [[] for _ in range(nv)]
for e in me.edges:
    a, b = e.vertices
    adj[a].append(b)
    adj[b].append(a)
for it in range(6):
    nw = lidw[:]
    for i, v in enumerate(verts):
        if v.y > -0.05 + OFF and 0.43 < v.z < 0.56 and adj[i]:
            nw[i] = 0.5 * lidw[i] + 0.5 * sum(lidw[j] for j in adj[i]) / len(adj[i])
    lidw = nw
W = {n: [0.0] * nv for n in ["root", "fill_top", "fill_front", "fill_side.L", "fill_side.R"] + lid}
proj = [Vector((0, v.y, v.z)) for v in verts]
CW = chain_weights(proj, LID_REST, lid, falloff=0.4)
for i, v in enumerate(verts):
    u, vv, h = u_(v), v_(v), h_(v)
    wf = smoothstep(0.35, 0.95, vv) * smoothstep(0.04, 0.3, h) * (1 - 0.6 * smoothstep(0.8, 1.0, h)) * (1 - 0.5 * u * u)
    wt = smoothstep(0.55, 0.97, h)
    wl = smoothstep(0.35, 1.0, u) * smoothstep(0.04, 0.3, h) * (1 - 0.5 * smoothstep(0.85, 1.0, h))
    wr = smoothstep(0.35, 1.0, -u) * smoothstep(0.04, 0.3, h) * (1 - 0.5 * smoothstep(0.85, 1.0, h))
    tot = wf + wt + wl + wr
    if tot > 1:
        wf, wt, wl, wr = wf / tot, wt / tot, wl / tot, wr / tot
    body = 1 - lidw[i]
    W["fill_front"][i], W["fill_top"][i], W["fill_side.L"][i], W["fill_side.R"][i] = wf * body, wt * body, wl * body, wr * body
    W["root"][i] = max(0.0, 1 - (wf + wt + wl + wr)) * body
    for n in lid:
        W[n][i] = CW[n][i] * lidw[i]
ob.name = "body"
skin(ob, arm, W)

# slack wrinkles (shape key) for the empty pack: horizontal crumple folds on the front + sides
ob.shape_key_add(name="Basis", from_mix=False)
sk = ob.shape_key_add(name="slack", from_mix=False)
for i, v in enumerate(verts):
    w = W["fill_front"][i] + W["fill_side.L"][i] + W["fill_side.R"][i] + 0.6 * W["fill_top"][i]
    if w < 1e-3:
        continue
    n = me.vertices[i].normal
    fold = math.sin(2 * math.pi * v.z / 0.055 + 2.5 * math.sin(2 * math.pi * v.x / 0.23) + 1.7 * math.sin(2 * math.pi * v.y / 0.19))
    sk.data[i].co = v + n * 0.0035 * fold * min(1.0, w)
F0 = 0.6  # the generated pack is "fairly full": fill = 0.6 is the rest shape
drive_shape_key(sk, arm, "fill", f"min(max(({F0} - p) / {F0}, 0.0), 1.0)")

# ------------------------------------------------------------------ rebuilt parts
black = mat("webbing", (srgb2lin(0.06), srgb2lin(0.065), srgb2lin(0.07)), 0.75)
pad_m = mat("strap_pad", (srgb2lin(0.10), srgb2lin(0.12), srgb2lin(0.10)), 0.85)
plast = mat("buckle_plastic", (srgb2lin(0.05), srgb2lin(0.05), srgb2lin(0.055)), 0.45)
parts = []
for side, sx in SIDES.items():
    r = strap_rest[side]
    # padded strap: dense sweep along the padded points, tapered at the top
    dense = resample(r["pad"], 0.01)
    dups = strap_ups(dense)
    wid = [lerp(0.6, 1.0, smoothstep(0.0, 0.12, i / len(dense))) for i in range(len(dense))]
    s_ob, idx = strap_object(f"strap.{side}", dense, dups, 0.065, 0.016, pad_m, widths=wid)
    vco = [v.co for v in s_ob.data.vertices]
    skin(s_ob, arm, chain_weights(vco, r["pad"], r["names"], falloff=0.45))
    # webbing from the adjuster to the bottom anchor (stretches with strap_length)
    wpts = [r["pad"][-1].lerp(r["web"], t / 6) for t in range(7)]
    w_ob, _ = strap_object(f"webbing.{side}", wpts, [strap_ups(r["pad"])[-1]] * 7, 0.025, 0.003, black)
    skin(w_ob, arm, {f"web.{side}": [1.0] * len(w_ob.data.vertices)})
    # free tail below the adjuster (jiggle chain)
    tpts = resample(r["tail"], 0.01)
    t_ob, _ = strap_object(f"tail.{side}", tpts, [Vector((0, 1, 0))] * len(tpts), 0.025, 0.003, black)
    skin(t_ob, arm, chain_weights([v.co for v in t_ob.data.vertices], r["tail"], r["tnames"], falloff=0.4))
    # adjuster (ladder lock) at the end of the padded part
    d = (r["pad"][-1] - r["pad"][-2]).normalized()
    lk = ladder_lock(f"adjuster.{side}", r["pad"][-1] - d * 0.012, d, r["ups"][-1], material=plast)
    rigid_to_bone(lk, arm, r["names"][-1])
    parts += [s_ob, w_ob, t_ob, lk]

# lid straps + buckles
for side, sx in SIDES.items():
    names = [f"ls.{side}_{i}" for i in range(3)]
    pts = [arm.data.bones[n].head_local for n in names] + [arm.data.bones[names[-1]].tail_local]
    dense = resample(pts, 0.008)
    l_ob, _ = strap_object(f"lidstrap.{side}", dense, [Vector((0, -1, 0))] * len(dense), 0.025, 0.003, black)
    skin(l_ob, arm, chain_weights([v.co for v in l_ob.data.vertices], pts, names, falloff=0.4))
    mb = buckle_male(f"buckle_m.{side}", pts[-1] - DOWN * 0.004, DOWN, Vector((0, -1, 0)), material=plast)
    rigid_to_bone(mb, arm, names[-1])
    parts += [l_ob, mb]

bpy.context.view_layer.update()
bvh_body = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())


def body_hit(x, z):
    loc, n, i, d = bvh_body.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
    return loc, n


# collision proxy for draping: the body without the lid (rest pose = fill default)
bvh_nolid = BVHTree.FromPolygons([v.co for v in me.vertices],
                                 [tuple(p.vertices) for p in me.polygons if all(lidw[i] < 0.5 for i in p.vertices)])


def push_out(q, gap=0.010):
    loc, n, fi, d = bvh_nolid.find_nearest(q)
    if loc is not None and d < 0.06 and (q - loc).dot(n) < gap:
        return loc + n * gap
    return q


def drape(pts, lens, extra=0.045):
    """Hanging chain resting on the body: push links out, keep link lengths; extra = rigid buckle past the end."""
    pts = [p.copy() for p in pts]
    for _ in range(5):
        for i in range(1, len(pts)):
            q = push_out(pts[i])
            pts[i] = pts[i - 1] + (q - pts[i - 1]).normalized() * lens[i - 1]
        end = pts[-1] + (pts[-1] - pts[-2]).normalized() * extra
        e2 = push_out(end)
        if (e2 - end).length > 1e-5:
            pts[-1] = pts[-2] + (e2 - pts[-2]).normalized() * lens[-1]
    return pts


# ------------------------------------------------------------------ controls
def pose_fill(f):
    out = {}
    e = max(0.0, (F0 - f) / F0)
    q = max(0.0, (f - F0) / (1 - F0))
    ang = math.radians(10.0 * e - 2.5 * q)  # +X rotation drops the front of the top
    R = Matrix.Translation(HINGE) @ Matrix.Rotation(ang, 4, "X") @ Matrix.Translation(-HINGE)
    out["fill_top"] = rest(arm, "fill_top").inverted() @ R @ rest(arm, "fill_top")
    tf = Vector((0, 0.075 * e - 0.03 * q, -0.015 * e))
    out["fill_front"] = rest(arm, "fill_front").inverted() @ Matrix.Translation(tf) @ rest(arm, "fill_front")
    for side, sx in SIDES.items():
        ts = Vector((-sx * 0.03 * e + sx * 0.018 * q, 0, -0.01 * e))
        bn = f"fill_side.{side}"
        out[bn] = rest(arm, bn).inverted() @ Matrix.Translation(ts) @ rest(arm, bn)
    return out


FILL_BONES = ["fill_top", "fill_front", "fill_side.L", "fill_side.R"]
act_fill = control_action(arm, "fill", FILL_BONES, pose_fill)

# lid: closed pose = chain fitted along a path that drapes over the collar and down the front
CLOSED_PATH = [P(0, 0.015, 0.465), P(0, 0.010, 0.545), P(0, -0.04, 0.588), P(0, -0.10, 0.597), P(0, -0.16, 0.585),
               P(0, -0.207, 0.553), P(0, -0.232, 0.50), P(0, -0.238, 0.40)]
closed_pts = fit_chain_to_path(LID_REST[0], CLOSED_PATH, LIDLEN)


def yz_ang(d):
    return math.atan2(d.z, d.y)


rest_ang = [yz_ang(LID_REST[i + 1] - LID_REST[i]) for i in range(len(lid))]
closed_ang = [yz_ang(closed_pts[i + 1] - closed_pts[i]) for i in range(len(lid))]
for i in range(len(lid)):  # unwrap so interpolation takes the short way
    while closed_ang[i] - rest_ang[i] > math.pi:
        closed_ang[i] -= 2 * math.pi
    while closed_ang[i] - rest_ang[i] < -math.pi:
        closed_ang[i] += 2 * math.pi
LID_OPEN_MAX = 1.0  # open = 1 is the generated pose


P_GEN = 0.65  # lid_open value of the generated pose; beyond it the flap folds back past the hinge


def lid_pts(p_in):
    n = len(lid)
    pts = [LID_REST[0].copy()]
    if p_in > P_GEN:  # past the generated pose: the whole flap tips back 50 deg, the outer part droops behind
        q = (p_in - P_GEN) / (1 - P_GEN)
        for i in range(n):
            a = rest_ang[i] - math.radians(50) * q - math.radians(30) * q * (i / (n - 1)) ** 1.3
            pts.append(pts[-1] + Vector((0, math.cos(a), math.sin(a))) * LIDLEN[i])
        return pts
    p = p_in / P_GEN
    for i in range(n):
        lag = 1.0 + 0.9 * i / (n - 1)  # the far edge lags: a floppy flap peels open from the hinge
        e = p ** lag if p < 1 else 1.0
        a = lerp(closed_ang[i], rest_ang[i], e)
        # gravity sag mid-swing: the outer half of the flap droops while the flap is near vertical
        a -= math.radians(14) * math.sin(math.pi * p) * (i / (n - 1)) ** 1.5 * (1 if p < 1 else 0)
        pts.append(pts[-1] + Vector((0, math.cos(a), math.sin(a))) * LIDLEN[i])
    return pts


FEMALE, CLOSED_STRAP = {}, {}
_lid0 = None


def closed_strap_pts(a, sx):
    """Lid strap lying on the body front: links of fixed length walked downward, kept 6 mm in front of the surface."""
    pts = [a.copy()]
    for L in LS_LEN:
        p = pts[-1]
        q = p + DOWN * L
        for _ in range(4):
            loc, n = body_hit(sx * LSX, q.z)
            if loc is not None:
                q.y = min(q.y, loc.y - 0.006)
            q = p + (q - p).normalized() * L
        pts.append(q)
    return pts


def pose_lid(p):
    pts = lid_pts(p)
    out, armm = chain_locals(arm, lid, pts)
    if p == 0 and not CLOSED_STRAP:
        for side, sx in SIDES.items():
            off = rest(arm, lid[-1]).inverted() @ rest(arm, f"ls.{side}_0").translation
            CLOSED_STRAP[side] = closed_strap_pts(armm[lid[-1]] @ off, sx)
            FEMALE[side] = CLOSED_STRAP[side][-1] + DOWN * 0.022
    for side, sx in SIDES.items():
        names = [f"ls.{side}_{i}" for i in range(3)]
        tip = armm[lid[-1]] @ Vector((0, arm.data.bones[lid[-1]].length, 0))
        a = tip + (armm[lid[-1]].to_3x3() @ (rest(arm, names[0]).translation - rest(arm, lid[-1]).translation - Vector((0, 0, 0))).normalized()) * 0
        # anchor point: the rest offset of the strap root from the lid tip, carried by the lid tip bone
        off = rest(arm, lid[-1]).inverted() @ rest(arm, names[0]).translation
        a = armm[lid[-1]] @ off
        down = DOWN
        k = smoothstep(0.0, 0.18, p)
        cs = CLOSED_STRAP[side]
        pts_s = [a.copy()]
        for i in range(3):  # each link blends from lying on the body (closed) to hanging (open)
            d = (cs[i + 1] - cs[i]).normalized().lerp(down, k).normalized()
            pts_s.append(pts_s[-1] + d * LS_LEN[i])
        if p > 0:
            pts_s = drape(pts_s, LS_LEN)
        o2, _ = chain_locals(arm, names, pts_s, parent_pose=armm[lid[-1]])
        out.update(o2)
    return out


LID_BONES = lid + [f"ls.{s}_{i}" for s in SIDES for i in range(3)]
act_lid = control_action(arm, "lid_open", LID_BONES, pose_lid)


def pose_straps(s):
    out = {}
    for side, sx in SIDES.items():
        r = strap_rest[side]
        pts, Lw = strap_path(sx, s)
        pad, web = split_path(pts, LP)
        padpts = resample(pad, LP / NPAD)[:NPAD + 1]
        padpts[-1] = pad[-1]
        o, armm = chain_locals(arm, r["names"], padpts, ups=strap_ups(padpts))
        out.update(o)
        # webbing bone stretches from the adjuster to the anchor
        o, armw = chain_locals(arm, [f"web.{side}"], [padpts[-1], web[-1]], parent_pose=armm[r["names"][-1]], stretch=True)
        out.update(o)
        # tail: hangs down from the adjuster, length = total webbing - webbing in use
        k = (WEB_TOT - Lw) / (WEB_TOT - r["Lw"])
        a = padpts[-1] + (armm[r["names"][-1]].to_3x3() @ (rest(arm, r["names"][-1]).to_3x3().inverted() @ Vector((0, 0.012, 0))))
        a = padpts[-1] + Vector((0, 0.012, 0))
        tn = r["tnames"]
        b0 = arm.data.bones[tn[0]]
        M = aim_matrix(b0.matrix_local, a, DOWN, k)
        P_ = armm[r["names"][-1]]
        out[tn[0]] = (P_ @ (b0.parent.matrix_local.inverted() @ b0.matrix_local)).inverted() @ M
    return out


STRAP_BONES = [n for s in SIDES for n in strap_rest[s]["names"] + [f"web.{s}", strap_rest[s]["tnames"][0]]]
act_strap = control_action(arm, "strap_length", STRAP_BONES, pose_straps)

# female buckles on the body front, skinned like the body under them (so they ride the fill deformer)
for side in SIDES:
    fb = buckle_female(f"buckle_f.{side}", FEMALE[side] - Vector((0, 0, 0.02)), Vector((0, 0, 1)), Vector((0, -1, 0)), material=plast)
    apply_mods(fb)
    skin(fb, arm, {k: [sum(v) / len(v)] * len(fb.data.vertices) for k, v in
                   weights_from_nearest(fb, ob, FILL_BONES + ["root"]).items()})
    # webbing tab from the buckle down into the body seam
    parts.append(fb)

wire_control(arm, "fill", act_fill, FILL_BONES, F0)
wire_control(arm, "lid_open", act_lid, LID_BONES, 0.0)
wire_control(arm, "strap_length", act_strap, STRAP_BONES, S_DEF)
for o in parts:
    for m in o.modifiers:
        if m.type == "BEVEL":
            pass

spec = {
    "anymachine": "soft-goods/v0", "bag": "rucksack",
    "controls": [
        {"param": "fill", "type": "fill", "default": F0, "range": [0, 1], "bones": FILL_BONES, "shape_keys": ["body:slack"], "shape_key_expr": {"slack": f"min(max(({F0} - p) / {F0}, 0.0), 1.0)"},
         "map": "0 = empty (top rotates 10 deg down about the lid hinge, front caves 7.5 cm, sides pinch 3 cm, slack folds); 0.6 = generated; 1 = bulging"},
        {"param": "lid_open", "type": "flap", "default": 0.0, "range": [0, 1], "bones": LID_BONES,
         "map": "0 = closed and clipped; 0.65 = the generated open pose; 1 = folded back 50 deg past it; chain angles interpolate with tip lag + mid-swing sag"},
        {"param": "strap_length", "type": "strap", "default": S_DEF, "range": [0, 1], "bones": STRAP_BONES,
         "map": "webbing below the adjuster 7..21 cm; tail = 34 cm - webbing"},
    ],
    "jiggle": {"chains": [{"prefix": f"ls.{s}_", "pinned_when": "1 - smoothstep(0.0, 0.15, lid_open)", "k": 45, "c": 3.5} for s in SIDES] + [{"prefix": f"tail.{s}_", "k": 40, "c": 3.0} for s in SIDES], "baked_in": "demo"},
    "demo": {"keys": [[1, {}], [14, {"lid_open": 0}], [44, {"lid_open": 1}], [104, {"lid_open": 1}], [130, {"lid_open": 0}], [136, {"fill": 0.6}], [162, {"fill": 0}], [176, {"fill": 0}], [204, {"fill": 1}], [218, {"fill": 1}], [232, {"fill": 0.6}], [236, {"strap_length": 0.4}], [256, {"strap_length": 1}], [278, {"strap_length": 0}], [292, {"strap_length": 0.4}]], "bob": [[50, 100], [298, 346]]},
    "check": {
        "body": "body", "body_exclude_groups": lid,
        "moving": [{"name": "lid", "object": "body", "groups": lid, "exclude_near": [[list(HINGE), 0.075]]},
                   {"name": "strap.L", "object": "strap.L", "exclude_near": [[list(strap_rest["L"]["pad"][0]), 0.03]]},
                   {"name": "strap.R", "object": "strap.R", "exclude_near": [[list(strap_rest["R"]["pad"][0]), 0.03]]},
                   {"name": "lidstrap.L", "object": "lidstrap.L"}, {"name": "lidstrap.R", "object": "lidstrap.R"},
                   {"name": "buckle_m.L", "object": "buckle_m.L"}, {"name": "buckle_m.R", "object": "buckle_m.R"}],
        "pairs": [["fill", "lid_open"], ["fill", "strap_length"]],
    },
    "hinge": list(HINGE), "female_buckles": {k: list(v) for k, v in FEMALE.items()},
}
arm["anymachine"] = json.dumps(spec)
report["controls"] = [c["param"] for c in spec["controls"]]
report["bones"] = len(arm.data.bones)
report["lid_rest_ang_deg"] = [round(math.degrees(a), 1) for a in rest_ang]
report["lid_closed_ang_deg"] = [round(math.degrees(a), 1) for a in closed_ang]
bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 240
bpy.context.scene.render.fps = 24
set_controls(arm, {"fill": F0, "lid_open": 0.0, "strap_length": S_DEF})
save(OUT)
json.dump(report, open(OUT.replace(".blend", "_build.json"), "w"), indent=1)
print("BUILT", json.dumps(report), flush=True)
