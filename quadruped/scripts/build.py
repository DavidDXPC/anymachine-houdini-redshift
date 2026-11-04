"""AnyMachine experiment 3: generated quadruped GLB -> rigged walking robot (.blend).

blender -b --factory-startup --python build.py -- --glb gen/meshy/model.glb --out out/quadruped.blend [--length 0.70]

1. normalise: Meshy is Z-up / front -Y; scale so the overall Y extent = --length, centre XY, feet on z = 0.
2. measure (automatic): body underside/top/half-width; per leg the foot ball (centre, radius), the hip (HFE) housing
   centre from the outboard side profile, the knee barrel from the profile's extreme; then symmetrise.
3. body: keep the generated shell, bisect off everything outboard of the body wall (actuators, legs).
4. rebuild per leg: HAA flange + HFE motor (rotate with HAA), thigh slab, shin slab, knee cap, rubber ball foot.
   Every moving part lives in its own lateral slab, coaxial with its joint, so adjacent links cannot clip.
5. rig: root -> body -> 4 x (haa -> hfe -> kfe), Limit Rotation per joint, IK targets + IK (switch `ik`),
   gait params as custom props, `gait.py` embedded; actions trot, trot_forward, idle, sit, stand baked linear.
"""
import bpy, bmesh, sys, os, math, json
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gait

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None, c=str: c(argv[argv.index(k) + 1]) if k in argv else d
GLB, OUT, LEN = opt("--glb"), os.path.abspath(opt("--out")), opt("--length", 0.70, float)
REP = {"glb": GLB, "length_m": LEN}

# ---------------------------------------------------------------- import + normalise
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in ms:
    mw = o.matrix_world.copy()
    o.parent = None
    o.data.transform(mw)
    o.matrix_world = Matrix.Identity(4)
for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
    bpy.data.objects.remove(o)
vl = bpy.context.view_layer
for o in ms:
    o.select_set(True)
vl.objects.active = ms[0]
if len(ms) > 1:
    bpy.ops.object.join()
gen = vl.objects.active
me = gen.data
vs = [v.co for v in me.vertices]
lo = Vector([min(v[i] for v in vs) for i in range(3)])
hi = Vector([max(v[i] for v in vs) for i in range(3)])
s = LEN / (hi.y - lo.y)
me.transform(Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))
vs = [v.co.copy() for v in me.vertices]
lo = Vector([min(v[i] for v in vs) for i in range(3)])
hi = Vector([max(v[i] for v in vs) for i in range(3)])
REP["gen_dims_m"] = [round(x, 4) for x in hi - lo]
REP["gen_tris"] = len(me.polygons)


def pct(a, p):
    a = sorted(a)
    return a[min(len(a) - 1, max(0, int(p * len(a))))]


# ---------------------------------------------------------------- measure
col = [v for v in vs if abs(v.x) < 0.04 and abs(v.y) < 0.12]
body_bottom, body_top = pct([v.z for v in col], 0.01), pct([v.z for v in col], 0.995)
hw = pct([abs(v.x) for v in vs if abs(v.y) < 0.12 and v.z > body_bottom + 0.01], 0.99)
REP.update(body_bottom=round(body_bottom, 4), body_top=round(body_top, 4), body_hw=round(hw, 4))
meas = {}
for sx in (-1, 1):
    for sy in (-1, 1):
        n = ("F" if sy < 0 else "H") + ("L" if sx < 0 else "R")
        q = [v for v in vs if v.x * sx > 0 and v.y * sy > 0]
        low = [v for v in q if v.z < 0.08]
        zmin = min(v.z for v in low)
        ball = [v for v in low if v.z < zmin + 0.05]
        rb = (pct([v.x for v in ball], 0.99) - pct([v.x for v in ball], 0.01)) / 2
        ball = [v for v in low if v.z < zmin + rb]
        F = Vector((0, sum(v.y for v in ball) / len(ball), zmin + rb))
        fx = sum(v.x for v in ball) / len(ball)
        legv = [v for v in q if abs(v.x) > hw + 0.004]
        bins = {}
        for v in legv:
            bins.setdefault(int(v.z * 200), []).append(v.y)  # 5 mm bins
        prof = {}
        for b, ys in bins.items():
            if len(ys) > 15:
                prof[(b + 0.5) / 200] = (pct(ys, 0.02), pct(ys, 0.98))
        ztop = max(z for z in prof)
        # hip housing: widest bin in the top 9 cm of the outboard profile -> radius = half width, centre z = top - r
        top = {z: r for z, r in prof.items() if z > ztop - 0.09}
        zw = max(top, key=lambda z: top[z][1] - top[z][0])
        rh = (top[zw][1] - top[zw][0]) / 2
        Hc = Vector((0, (top[zw][0] + top[zw][1]) / 2, ztop + 0.0025 - rh))
        # knee: between foot and hip, the profile point that deviates most from the hip-foot line (either side)
        def dev(z, y):
            t = (z - F.z) / (Hc.z - F.z)
            return y - (F.y + t * (Hc.y - F.y))
        mid = {z: r for z, r in prof.items() if F.z + 0.06 < z < Hc.z - 0.07}
        zb = max(mid, key=lambda z: max(dev(z, mid[z][1]), -dev(z, mid[z][0])))
        back = dev(zb, mid[zb][1]) > -dev(zb, mid[zb][0])
        rk = (mid[zb][1] - mid[zb][0]) / 2
        near = [z for z in mid if abs(abs(dev(z, mid[z][1 if back else 0])) - abs(dev(zb, mid[zb][1 if back else 0]))) < 0.003]
        Kz = sum(near) / len(near)
        Ky = (mid[zb][1] - rk) if back else (mid[zb][0] + rk)
        K = Vector((0, Ky, Kz))
        meas[n] = {"hip": [round(Hc.y, 4), round(Hc.z, 4)], "hip_r": round(rh, 4), "knee": [round(K.y, 4), round(K.z, 4)],
                   "knee_r": round(rk, 4), "knee_points": "back" if back else "front", "foot": [round(fx, 4), round(F.y, 4), round(F.z, 4)],
                   "foot_r": round(rb, 4), "thigh_len": round((K - Hc).length, 4), "shin_len": round((F - K).length, 4),
                   "thigh": [K.y - Hc.y, K.z - Hc.z], "shin": [F.y - K.y, F.z - K.z]}
REP["measured_legs"] = {k: {a: b for a, b in v.items() if a not in ("thigh", "shin")} for k, v in meas.items()}
print("MEASURE", json.dumps(REP["measured_legs"]), flush=True)

# symmetrise: one leg design for all four (mean of measured thigh/shin vectors), hips per end (mean of L/R)
mean = lambda xs: sum(xs) / len(xs)
t0 = [mean([m["thigh"][i] for m in meas.values()]) for i in (0, 1)]
s0 = [mean([m["shin"][i] for m in meas.values()]) for i in (0, 1)]
z_hip = mean([m["hip"][1] for m in meas.values()])
y_hip = {"F": mean([meas["FL"]["hip"][0], meas["FR"]["hip"][0]]), "H": mean([meas["HL"]["hip"][0], meas["HR"]["hip"][0]])}
foot_r = mean([m["foot_r"] for m in meas.values()])
L1, L2 = math.hypot(*t0), math.hypot(*s0)
psi0 = math.atan2(s0[1], s0[0]) - math.atan2(t0[1], t0[0])

# lateral layout (outboard offsets from the measured body wall hw); all slabs are disjoint in x
X = {"pivot": hw - 0.030, "disc": (hw - 0.007, hw + 0.005), "flange": (hw + 0.016, hw + 0.025), "motor": (hw + 0.025, hw + 0.061),
     "shin": (hw + 0.039, hw + 0.059), "stripe": (hw + 0.059, hw + 0.0605), "thigh": (hw + 0.063, hw + 0.087),
     "cap": (hw + 0.088, hw + 0.093), "plane": hw + 0.049}
R = {"disc": 0.050, "flange": 0.022, "motor": 0.048, "thigh_hip": 0.040, "thigh_knee": 0.030, "shin_knee": 0.026, "shin_foot": 0.013,
     "cap": 0.019}
KNEE_INTERIOR = (30.0, 170.0)  # deg, the thigh-shin interior angle range
psi_rng = sorted([math.copysign(math.radians(180 - KNEE_INTERIOR[1]), psi0), math.copysign(math.radians(180 - KNEE_INTERIOR[0]), psi0)])
limits = {"haa": [math.radians(-18), math.radians(18)], "hfe": [math.radians(-60), math.radians(60)],
          "kfe": [psi_rng[0] - psi0, psi_rng[1] - psi0]}
geo = {"t0": t0, "s0": s0, "L1": L1, "L2": L2, "psi0": psi0, "foot_r": foot_r, "z_hip": z_hip, "y_hip": y_hip, "hw": hw,
       "layout_x": X, "radii": R, "limits_rad": limits,
       "limits_deg": {k: [round(math.degrees(a), 2) for a in v] for k, v in limits.items()}}
REP["design"] = {"L1": round(L1, 4), "L2": round(L2, 4), "knee_rest_interior_deg": round(180 - abs(math.degrees(psi0)), 2),
                 "thigh_rest_from_vertical_deg": round(math.degrees(math.atan2(t0[0], -t0[1])), 2), "z_hip": round(z_hip, 4),
                 "y_hip": {k: round(v, 4) for k, v in y_hip.items()}, "foot_r": round(foot_r, 4), "limits_deg": geo["limits_deg"],
                 "leg_plane_x": round(X["plane"], 4), "haa_pivot_x": round(X["pivot"], 4)}
print("DESIGN", json.dumps(REP["design"]), flush=True)

# ---------------------------------------------------------------- body: generated shell minus everything outboard
bm = bmesh.new()
bm.from_mesh(me)
cut = hw + 0.003
for sx in (-1, 1):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(sx * cut, 0, 0), plane_no=(sx, 0, 0), clear_outer=True)
# drop small islands (bits of leg that survived inside the wall)
bm.verts.ensure_lookup_table()
seen, islands = set(), []
for v0 in bm.verts:
    if v0.index in seen:
        continue
    st, isl = [v0], []
    seen.add(v0.index)
    while st:
        v = st.pop()
        isl.append(v)
        for e in v.link_edges:
            w = e.other_vert(v)
            if w.index not in seen:
                seen.add(w.index)
                st.append(w)
    islands.append(isl)
big = max(len(i) for i in islands)
small = [isl for isl in islands if len(isl) < 0.02 * big and min(v.co.z for v in isl) < body_bottom + 0.01]
REP["body_islands_removed"] = len(small)
bmesh.ops.delete(bm, geom=[v for isl in small for v in isl], context="VERTS")
bm.to_mesh(me)
bm.free()
gen.name = me.name = "body_shell"
REP["body_tris"] = len(me.polygons)
for p in me.polygons:
    p.use_smooth = True

# sample the shell's light grey from its texture (sRGB -> linear), for the rebuilt leg covers
grey = (0.40, 0.41, 0.43)
try:
    import numpy as np
    mat0 = me.materials[0]
    bsdf = next(n for n in mat0.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    img = None
    st = [bsdf.inputs["Base Color"]]
    while st and img is None:
        sock = st.pop()
        for l in sock.links:
            if l.from_node.type == "TEX_IMAGE":
                img = l.from_node.image
            else:
                st += [i for i in l.from_node.inputs if i.is_linked]
    if img:
        w_, h_ = img.size
        px = np.empty(w_ * h_ * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(h_, w_, 4)
        uvl = me.uv_layers.active.data
        cs = []
        for p in me.polygons:
            if p.normal.z > 0.95 and p.center.z > body_top - 0.01 and abs(p.center.x) < 0.05 and abs(p.center.y) < 0.15:
                u, v = uvl[p.loop_start].uv
                cs.append(px[min(h_ - 1, int(v % 1 * h_)), min(w_ - 1, int(u % 1 * w_)), :3])
        if cs:
            m = np.median(np.array(cs), axis=0)
            grey = tuple(float(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in m) if img.colorspace_settings.name == "sRGB" else tuple(float(c) for c in m)
    REP["shell_material_inputs"] = {i.name: [l.from_node.type for l in i.links] for i in bsdf.inputs if i.is_linked}
except Exception as e:  # noqa
    REP["grey_sample_error"] = repr(e)
REP["leg_grey_linear"] = [round(c, 4) for c in grey]


# ---------------------------------------------------------------- materials + primitive builders
def mat(name, col, metal=0.0, rough=0.5, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    return m


M = {"cover": mat("leg_cover", grey, 0.0, 0.42, 0.3), "dark": mat("actuator_dark", (0.018, 0.019, 0.021), 0.3, 0.38),
     "metal": mat("machined_alu", (0.55, 0.56, 0.58), 1.0, 0.28), "rubber": mat("rubber", (0.012, 0.012, 0.012), 0.0, 0.85),
     "stripe": mat("stripe_dark", (0.03, 0.03, 0.033), 0.0, 0.5)}


def new_obj(name, bm, material, smooth_deg=35):
    m = bpy.data.meshes.new(name)
    bm.to_mesh(m)
    bm.free()
    o = bpy.data.objects.new(name, m)
    bpy.context.scene.collection.objects.link(o)
    m.materials.append(material)
    for p in m.polygons:
        p.use_smooth = True
    try:
        m.set_sharp_from_angle(angle=math.radians(smooth_deg))
    except Exception:
        pass
    return o


def bevel(o, w=0.0015, seg=2):
    md = o.modifiers.new("bevel", "BEVEL")
    md.width, md.segments, md.limit_method = w, seg, "ANGLE"
    md.angle_limit = math.radians(40)
    vl.objects.active = o
    with bpy.context.temp_override(object=o, active_object=o):
        bpy.ops.object.modifier_apply(modifier="bevel")


def hull2(pts):
    pts = sorted(set((round(p[0], 7), round(p[1], 7)) for p in pts))
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo_, up = [], []
    for p in pts:
        while len(lo_) >= 2 and cr(lo_[-2], lo_[-1], p) <= 0:
            lo_.pop()
        lo_.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo_[:-1] + up[:-1]


def extrude_x(poly, x0, x1):
    """poly: CCW list of (y, z); prism between x0 and x1."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in poly]
    b = [bm.verts.new((x1, y, z)) for y, z in poly]
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def stadium(c1, r1, c2, r2, x0, x1, seg=40):
    pts = []
    for c, r in ((c1, r1), (c2, r2)):
        pts += [(c[0] + r * math.cos(2 * math.pi * i / seg), c[1] + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    return extrude_x(hull2(pts), min(x0, x1), max(x0, x1))


def cyl_x(c, r, x0, x1, seg=48):
    return extrude_x([(c[0] + r * math.cos(2 * math.pi * i / seg), c[1] + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)],
                     min(x0, x1), max(x0, x1))


def sphere(c, r):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r, matrix=Matrix.Translation(c))
    return bm


# ---------------------------------------------------------------- rest geometry per leg
LEGS = {}
for n in gait.LEGS:
    sgn = -1 if n[1] == "L" else 1
    yh = y_hip[n[0]]
    H = (yh, z_hip)
    K = (yh + t0[0], z_hip + t0[1])
    F = (K[0] + s0[0], K[1] + s0[1])
    LEGS[n] = {"s": sgn, "haa_pivot": [sgn * X["pivot"], yh, z_hip], "hfe": [sgn * X["plane"], yh, z_hip],
               "knee": [sgn * X["plane"], K[0], K[1]], "foot": [sgn * X["plane"], F[0], F[1]]}
rest_foot_z = min(l["foot"][2] for l in LEGS.values())
REP["rest_foot_centre_z"] = round(rest_foot_z, 4)

parts = {}  # object -> (group, bone)


def add(o, group, bone):
    parts[o.name] = (group, bone)
    o["group"] = group
    return o


body_shell = add(gen, "body", "body")
for n, L in LEGS.items():
    sg = L["s"]
    xs = lambda rng: (sg * rng[0], sg * rng[1])
    H = (L["hfe"][1], L["hfe"][2])
    K = (L["knee"][1], L["knee"][2])
    F = (L["foot"][1], L["foot"][2])
    o = new_obj(f"{n}_haa_disc", cyl_x(H, R["disc"], *xs(X["disc"])), M["dark"])
    bevel(o, 0.002)
    add(o, "body", "body")
    o = new_obj(f"{n}_haa_flange", cyl_x(H, R["flange"], *xs(X["flange"])), M["metal"])
    bevel(o, 0.001)
    add(o, f"{n}_haa", f"{n}_haa")
    o = new_obj(f"{n}_hfe_motor", cyl_x(H, R["motor"], *xs(X["motor"])), M["dark"])
    bevel(o, 0.004, 3)
    add(o, f"{n}_haa", f"{n}_haa")
    o = new_obj(f"{n}_hfe_ring", cyl_x(H, R["motor"] + 0.0012, *xs((X["motor"][1] - 0.006, X["motor"][1] - 0.003))), M["metal"])
    add(o, f"{n}_haa", f"{n}_haa")
    o = new_obj(f"{n}_thigh", stadium(H, R["thigh_hip"], K, R["thigh_knee"], *xs(X["thigh"])), M["cover"])
    bevel(o, 0.003, 3)
    add(o, f"{n}_thigh", f"{n}_hfe")
    o = new_obj(f"{n}_shin", stadium(K, R["shin_knee"], F, R["shin_foot"], *xs(X["shin"])), M["cover"])
    bevel(o, 0.0025, 3)
    add(o, f"{n}_shin", f"{n}_kfe")
    d = Vector((0, F[0] - K[0], F[1] - K[1]))
    a_ = (K[0] + d.y * 0.32, K[1] + d.z * 0.32)
    b_ = (K[0] + d.y * 0.78, K[1] + d.z * 0.78)
    o = new_obj(f"{n}_shin_stripe", stadium(a_, 0.0065, b_, 0.005, *xs(X["stripe"])), M["stripe"])
    add(o, f"{n}_shin", f"{n}_kfe")
    o = new_obj(f"{n}_knee_cap", cyl_x(K, R["cap"], *xs(X["cap"])), M["dark"])
    bevel(o, 0.0015)
    add(o, f"{n}_shin", f"{n}_kfe")
    dn = d.normalized()
    nc = (K[0] + dn.y * 0.011, K[1] + dn.z * 0.011)
    o = new_obj(f"{n}_knee_mark", stadium((K[0] + dn.y * 0.005, K[1] + dn.z * 0.005), 0.0025, nc, 0.0025,
                                          *xs((X["cap"][1], X["cap"][1] + 0.001))), M["metal"])
    add(o, f"{n}_shin", f"{n}_kfe")
    o = new_obj(f"{n}_foot", sphere(Vector(L["foot"]), foot_r), M["rubber"])
    add(o, f"{n}_shin", f"{n}_kfe")

# ---------------------------------------------------------------- armature
ad = bpy.data.armatures.new("quadruped_rig")
arm = bpy.data.objects.new("quadruped_rig", ad)
bpy.context.scene.collection.objects.link(arm)
ad.display_type = "STICK"
vl.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = ad.edit_bones
y_c = (y_hip["F"] + y_hip["H"]) / 2
b = eb.new("root"); b.head, b.tail, b.roll = (0, 0, 0), (0, 0.15, 0), 0
b = eb.new("body"); b.head, b.tail, b.roll = (0, y_c, z_hip), (0, y_c + 0.1, z_hip), 0
b.parent = eb["root"]
for n, L in LEGS.items():
    P = Vector(L["haa_pivot"])
    b = eb.new(n + "_haa"); b.head, b.tail, b.roll = P, P + Vector((0, -L["s"] * 0.06, 0)), 0
    b.parent = eb["body"]
    for nm, h, t, par in ((n + "_hfe", L["hfe"], L["knee"], n + "_haa"), (n + "_kfe", L["knee"], L["foot"], n + "_hfe")):
        b = eb.new(nm)
        b.head, b.tail = Vector(h), Vector(t)
        yb = (b.tail - b.head).normalized()
        b.align_roll(Vector((1, 0, 0)).cross(yb))
        b.parent = eb[par]
        b.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")
for bn in ad.bones:
    if bn.name.endswith(("_hfe", "_kfe")):
        xa = bn.matrix_local.col[0].xyz
        assert (xa - Vector((1, 0, 0))).length < 1e-4, (bn.name, xa)
    if bn.name.endswith("_haa"):
        assert abs(abs(bn.matrix_local.col[1].xyz.y) - 1) < 1e-6
    if bn.name in ("root", "body"):
        assert (bn.matrix_local.to_3x3() - Matrix.Identity(3)).median_scale < 1e-6 if hasattr(Matrix, "median_scale") else True

spec = {"version": 1, "kind": "quadruped", "legs": LEGS, "geometry": geo, "body_head": [0, y_c, z_hip],
        "joint_order": ["haa", "hfe", "kfe"], "conventions": {
            "haa": "bone-local Y; + = foot outward (abduction)", "hfe": "about +X; + = foot swings backward",
            "kfe": "about +X; + = knee opens", "body": "loc (0,dy,dz), euler XYZ (pitch, roll, 0); nose-up = -pitch",
            "front": "-Y", "up": "+Z", "units": "m, rad"}}
arm["anymachine"] = json.dumps(spec)
for k, v in gait.DEFAULTS.items():
    arm[k] = v
arm["ik"] = 0.0
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
    j = pb.name.split("_")[-1]
    if j in limits:
        lo_, hi_ = limits[j]
        c = pb.constraints.new("LIMIT_ROTATION")
        c.owner_space = "LOCAL"
        c.use_limit_x = c.use_limit_y = c.use_limit_z = True
        ax = 1 if j == "haa" else 0
        for i, a in enumerate("xyz"):
            setattr(c, f"min_{a}", lo_ if i == ax else 0)
            setattr(c, f"max_{a}", hi_ if i == ax else 0)
        for i, a in enumerate("xyz"):
            setattr(pb, f"lock_ik_{a}", i != ax)
        setattr(pb, f"use_ik_limit_{'xyz'[ax]}", True)
        setattr(pb, f"ik_min_{'xyz'[ax]}", lo_)
        setattr(pb, f"ik_max_{'xyz'[ax]}", hi_)

# IK foot targets (empties on the root bone) + IK on each knee bone, switched by the rig's `ik` prop
for n, L in LEGS.items():
    e = bpy.data.objects.new(f"ik_{n}", None)
    e.empty_display_type, e.empty_display_size = "SPHERE", 0.035
    bpy.context.scene.collection.objects.link(e)
    e.parent, e.parent_type, e.parent_bone = arm, "BONE", "root"
    vl.update()
    e.matrix_world = Matrix.Translation(Vector(L["foot"]))
    pb = arm.pose.bones[n + "_kfe"]
    c = pb.constraints.new("IK")
    c.target, c.chain_count, c.use_tail, c.iterations = e, 3, True, 500
    pb.constraints.move(len(pb.constraints) - 1, 0)
    fc = c.driver_add("influence")
    fc.driver.type = "SCRIPTED"
    v = fc.driver.variables.new()
    v.name, v.targets[0].id, v.targets[0].data_path = "ik", arm, '["ik"]'
    fc.driver.expression = "ik"

# rigid parts on bones
vl.update()
for name, (grp, bone) in parts.items():
    o = bpy.data.objects[name]
    o.parent, o.parent_type, o.parent_bone = arm, "BONE", bone
    vl.update()
    o.matrix_world = Matrix.Identity(4)

# ---------------------------------------------------------------- gaits
txt = bpy.data.texts.new("gait.py")
txt.write(open(os.path.join(HERE, "gait.py")).read())
p = dict(gait.DEFAULTS)
g, acts = gait.build_all(spec, p)
REP["ik_reach"] = {k: all(s_["reach"] for s_ in v[2]) for k, v in acts.items()}
REP["clamped_keys"] = gait.bake(arm, acts)
sc = bpy.context.scene
sc.render.fps = p["fps"]
sc.frame_start, sc.frame_end = 1, len(acts["trot_forward"][0])
arm.animation_data.action = bpy.data.actions["trot_forward"]
REP["actions"] = {k: len(v[0]) for k, v in acts.items()}
REP["parts"] = {k: v[0] for k, v in parts.items()}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump(REP, open(os.path.join(os.path.dirname(OUT), "build.json"), "w"), indent=1)
print("BUILT", OUT, json.dumps({k: REP[k] for k in ("body_tris", "ik_reach", "clamped_keys", "actions", "leg_grey_linear")}), flush=True)
