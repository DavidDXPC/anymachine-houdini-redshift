"""AnyMachine experiment 2: generated spider shell -> rigged 8-leg robot spider (.blend) with walk / idle / crouch.

blender -b --factory-startup --python build.py -- --shell gen/shell_meshy.blend --out out/spider.blend \
    [--set '{"step_length": 0.12, "hip_z": 0.10}']

Kept from the generator: the carapace SKIN (top surface + texture, see shell.py).
Rebuilt: chassis (lofted under the skin from its measured outline), 8 hip brackets, and every leg segment as its own rigid
part with coaxial half-barrels in separate axial slabs (see spider_lib docstring), so segments cannot clip by construction.
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spider_lib as SL
import spider_bake as SB

argv = sys.argv[sys.argv.index("--") + 1:]


def opt(k, d=None, cast=str):
    return cast(argv[argv.index(k) + 1]) if k in argv else d


SHELL, OUT = os.path.abspath(opt("--shell")), os.path.abspath(opt("--out"))
P = dict(SL.DEFAULTS)
P.update(json.loads(opt("--set", "{}")))
report = {"params": P}

bpy.ops.wm.open_mainfile(filepath=SHELL)
sc = bpy.context.scene
skin = bpy.data.objects["shell"]
srep = json.loads(skin["anymachine_shell"])
report["shell"] = {k: v for k, v in srep.items() if k not in ("half_width_profile", "footprint_profile")}

# ---------------------------------------------------------------- place the skin in the body rest frame
# generated hip height ~ midway between the generated belly (footprint low z) and the carapace rim
fp = np.array(srep["footprint_profile"])
hp = np.array(srep["half_width_profile"])
zp_gen = float((np.median(fp[:, 2]) + np.median(hp[:, 2])) / 2)
dz = P["hip_z"] - zp_gen
skin.data.transform(Matrix.Translation((0, 0, dz)))
report["measured"] = {"hip_z_generated_m": round(zp_gen, 4), "skin_lift_m": round(dz, 4)}
for m in skin.data.materials:  # experiment-1 rule: generator metallic/roughness maps make plastic look chrome
    if m and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                for k, v in (("Metallic", 0.0), ("Roughness", 0.45)):
                    for l in list(n.inputs[k].links):
                        m.node_tree.links.remove(l)
                    n.inputs[k].default_value = v

# ---------------------------------------------------------------- chassis outline, measured from the placed skin
SV = np.array([v.co[:] for v in skin.data.vertices])
ys = np.arange(SV[:, 1].min() + 0.004, SV[:, 1].max() - 0.004 + 1e-9, 0.01)
hw, rim = [], []
for y in ys:
    m = np.abs(SV[:, 1] - y) < 0.006
    q = SV[m]
    h = float(np.percentile(np.abs(q[:, 0]), 97))
    hw.append(h)
    rim.append(float(np.median(q[np.abs(q[:, 0]) > 0.88 * h, 2])))
med = lambda a: np.array([np.median(a[max(0, i - 2):i + 3]) for i in range(len(a))])
hw, rim = med(np.array(hw)), med(np.array(rim))
fpy, fpz = fp[:, 0], fp[:, 2] + dz
belly = med(np.interp(ys, fpy, fpz))
belly = np.minimum(belly, rim - 0.035)
belly = np.maximum(belly, P["hip_z"] - 0.045)  # keep >= 5.5 cm ground clearance at stand (crouch drops 4.5 cm)
hw_c = 0.96 * hw


def chassis_hw(y):
    return float(np.interp(y, ys, hw_c))


report["measured"]["chassis"] = {"y_range_m": [round(float(ys[0]), 3), round(float(ys[-1]), 3)],
                                 "max_half_width_m": round(float(hw_c.max()), 4),
                                 "rim_z_m": [round(float(rim.min()), 4), round(float(rim.max()), 4)],
                                 "belly_z_m": [round(float(belly.min()), 4), round(float(belly.max()), 4)]}

L = SL.layout(P, chassis_hw)
report["legs"] = {leg: {"yaw_axis": [round(x, 4) for x in L[leg]["Y0"]], "dir_deg": P["hip_az"][int(leg[1]) - 1],
                        "rest_femur_elev_deg": round(math.degrees(L[leg]["e0"]), 2),
                        "rest_knee_rel_deg": round(math.degrees(L[leg]["k0"]), 2),
                        "foot_rest": [round(x, 4) for x in L[leg]["foot_rest"]],
                        "limits_local_deg": {k: [round(math.degrees(a), 2) for a in v] for k, v in SL.limits_local(P, L[leg]).items()}}
                  for leg in SL.LEGS}

# ---------------------------------------------------------------- materials
def mat(name, col, rough, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


MATS = [mat("am_white", (0.78, 0.79, 0.80), 0.38), mat("am_dark", (0.035, 0.038, 0.042), 0.5),
        mat("am_metal", (0.75, 0.76, 0.78), 0.32, 1.0), mat("am_rubber", (0.015, 0.015, 0.015), 0.85)]
WHITE, DARK, METAL, RUBBER = range(4)


# ---------------------------------------------------------------- geometry helpers (world rest coordinates)
def V(a):
    return Vector(a)


def frame_from(axis):
    axis = V(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    x = ref.cross(axis).normalized()
    y = axis.cross(x)
    return x, y, axis


def add_cyl(bm, center, axis, r, h0, h1, mi, segs=32):
    """Closed cylinder along `axis` covering axial offsets [h0, h1] from `center`."""
    x, y, z = frame_from(axis)
    c = V(center)
    rings = []
    for h in (h0, h1):
        rings.append([bm.verts.new(c + z * h + (x * math.cos(2 * math.pi * i / segs) + y * math.sin(2 * math.pi * i / segs)) * r)
                      for i in range(segs)])
    fs = [bm.faces.new((rings[0][i], rings[0][(i + 1) % segs], rings[1][(i + 1) % segs], rings[1][i])) for i in range(segs)]
    fs.append(bm.faces.new(list(reversed(rings[0]))))
    fs.append(bm.faces.new(rings[1]))
    for f in fs:
        f.material_index = mi
    return fs


def add_beam(bm, p0, p1, a, s0, s1, d0, d1, mi, chamfer=0.25):
    """Tapered beam p0->p1 in the axial slab [s0, s1] along `a`; depth d0 -> d1 in the plane normal n = a x dir.
    Octagonal-ish section (chamfered corners) so it reads machined, not boxy."""
    p0, p1, a = V(p0), V(p1), V(a).normalized()
    d = (p1 - p0).normalized()
    n = a.cross(d).normalized()
    w = s1 - s0
    sm = (s0 + s1) / 2

    def ring(p, dep):
        k = chamfer * min(w, dep) / 2
        pts = [(w / 2, dep / 2 - k), (w / 2 - k, dep / 2), (-w / 2 + k, dep / 2), (-w / 2, dep / 2 - k),
               (-w / 2, -dep / 2 + k), (-w / 2 + k, -dep / 2), (w / 2 - k, -dep / 2), (w / 2, -dep / 2 + k)]
        return [bm.verts.new(p + a * (sm + u) + n * v) for u, v in pts]

    r0, r1 = ring(p0, d0), ring(p1, d1)
    N = len(r0)
    fs = [bm.faces.new((r0[i], r0[(i + 1) % N], r1[(i + 1) % N], r1[i])) for i in range(N)]
    fs.append(bm.faces.new(list(reversed(r0))))
    fs.append(bm.faces.new(r1))
    for f in fs:
        f.material_index = mi
    return fs


def add_sphere(bm, c, r, mi):
    res = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r, matrix=Matrix.Translation(V(c)))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mi


def finish(name, bm, smooth_angle=35):
    """bmesh -> object. Hard edges split above `smooth_angle`, everything else smooth (exports cleanly to glTF)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sharp = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(smooth_angle)]
    bmesh.ops.split_edges(bm, edges=sharp)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in MATS:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- chassis (lofted superellipse under the skin)
bm = bmesh.new()
NS, PEXP = 32, 3.2
rings = []
for i, y in enumerate(ys):
    top, bot = rim[i] - 0.004, belly[i]
    zc, B, A = (top + bot) / 2, (top - bot) / 2, max(hw_c[i], 0.01)
    ring = []
    for j in range(NS):
        th = 2 * math.pi * j / NS
        c, s = math.cos(th), math.sin(th)
        ring.append(bm.verts.new((A * math.copysign(abs(c) ** (2 / PEXP), c), y, zc + B * math.copysign(abs(s) ** (2 / PEXP), s))))
    rings.append(ring)
for r0, r1 in zip(rings, rings[1:]):
    for j in range(NS):
        bm.faces.new((r0[j], r0[(j + 1) % NS], r1[(j + 1) % NS], r1[j])).material_index = DARK
for ring, rev in ((rings[0], False), (rings[-1], True)):
    c = bm.verts.new(sum((v.co for v in ring), Vector()) / NS)
    for j in range(NS):
        f = (ring[j], ring[(j + 1) % NS], c) if not rev else (ring[(j + 1) % NS], ring[j], c)
        bm.faces.new(f).material_index = DARK
# hip brackets: upper half of each yaw barrel + a strut into the chassis wall
for leg in SL.LEGS:
    Lg = L[leg]
    Y0 = V(Lg["Y0"])
    s = Lg["side"]
    add_cyl(bm, Y0, (0, 0, 1), P["rY"], P["gap"] + 0.004, 0.032, DARK)
    add_cyl(bm, Y0, (0, 0, 1), P["rY"] * 0.62, 0.032, 0.0345, METAL)
    inner = Vector((s * (chassis_hw(Y0.y) - 0.012), Y0.y, Y0.z + 0.019))
    add_beam(bm, Y0 + Vector((0, 0, 0.019)), inner, (0, 1, 0), -0.012, 0.012, 0.022, 0.026, DARK)
body_ob = finish("chassis", bm, 50)

# ---------------------------------------------------------------- legs
parts = {}
g = P["gap"]
for leg in SL.LEGS:
    Lg = L[leg]
    m = Lg["side"]
    Y0, P1, K, F = V(Lg["Y0"]), V(Lg["P1"]), V(Lg["K"]), V(Lg["foot_rest"])
    a, u = V(Lg["a"]), V(Lg["u"])
    sl = lambda lo, hi: (min(m * lo, m * hi), max(m * lo, m * hi))   # mirrored slab helper
    cox = sl(-g / 2 - P["wC"], -g / 2)
    fem = sl(g / 2, g / 2 + P["wF"])
    tib = sl(-g / 2 - P["wT"], -g / 2)
    out_c, out_f, out_t = -m, m, -m   # outward axial direction of each slab

    # coxa: lower yaw half-barrel, beam (in its slab), hip-pitch half-barrel
    bm = bmesh.new()
    add_cyl(bm, Y0, (0, 0, 1), P["rY"], -0.026, 0.004, DARK)
    add_cyl(bm, Y0, (0, 0, 1), P["rY"] * 0.55, -0.0275, -0.026, METAL)
    add_beam(bm, Y0 + Vector((0, 0, -0.005)), P1 + Vector((0, 0, -0.005)), a, cox[0], cox[1], 0.018, 0.018, DARK)
    add_cyl(bm, P1, a, P["rP"], cox[0], cox[1], DARK)
    add_cyl(bm, P1, a * out_c, P["rP"] * 0.62, P["wC"] + g / 2, P["wC"] + g / 2 + 0.002, METAL)
    parts[f"coxa_{leg}"] = finish(f"coxa_{leg}", bm)

    # femur: pitch half-barrel, tapered white beam with a dark inlay, knee half-barrel
    Fd = (K - P1).normalized()
    bm = bmesh.new()
    add_cyl(bm, P1, a, P["rP"], fem[0], fem[1], METAL)
    add_cyl(bm, P1, a * out_f, P["rP"] * 0.62, P["wF"] + g / 2, P["wF"] + g / 2 + 0.002, METAL)
    add_beam(bm, P1 + Fd * 0.004, K - Fd * 0.004, a, fem[0], fem[1], 0.032, 0.024, WHITE)
    ins = sl(g / 2 + P["wF"], g / 2 + P["wF"] + 0.0012)
    add_beam(bm, P1 + Fd * 0.035, K - Fd * 0.03, a, ins[0], ins[1], 0.013, 0.010, DARK, chamfer=0.5)
    add_cyl(bm, K, a, P["rK"], fem[0], fem[1], WHITE)
    add_cyl(bm, K, a * out_f, P["rK"] * 0.62, P["wF"] + g / 2, P["wF"] + g / 2 + 0.002, METAL)
    parts[f"femur_{leg}"] = finish(f"femur_{leg}", bm)

    # tibia: knee half-barrel, tapered beam, dark ankle collar, rubber ball foot (centre = F = bone tail)
    Fp = F - a * Lg["c_tib"]          # foot centre projected onto the axial-0 plane (beam helper offsets by slab)
    Td = (Fp - K).normalized()
    bm = bmesh.new()
    add_cyl(bm, K, a, P["rK"], tib[0], tib[1], METAL)
    add_cyl(bm, K, a * out_t, P["rK"] * 0.62, P["wT"] + g / 2, P["wT"] + g / 2 + 0.002, METAL)
    add_beam(bm, K + Td * 0.004, Fp - Td * 0.03, a, tib[0], tib[1], 0.025, 0.014, WHITE)
    ins_t = sl(-g / 2 - P["wT"] - 0.0012, -g / 2 - P["wT"])
    add_beam(bm, K + Td * 0.04, Fp - Td * 0.06, a, ins_t[0], ins_t[1], 0.011, 0.007, DARK, chamfer=0.5)
    add_cyl(bm, F, Td, 0.0085, -0.034, -0.008, DARK)
    add_sphere(bm, F, P["foot_r"], RUBBER)
    parts[f"tibia_{leg}"] = finish(f"tibia_{leg}", bm)

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new("spider_rig")
arm = bpy.data.objects.new("spider_rig", arm_data)
sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones


def bone(name, head, tail, parent=None, roll_z=None):
    b = eb.new(name)
    b.head, b.tail = V(head), V(tail)
    if roll_z is not None:
        b.align_roll(V(roll_z))
    else:
        b.roll = 0
    if parent:
        b.parent = eb[parent]
    b.use_connect = False
    return b


bone("root", (0, 0, 0), (0, 0.08, 0))
bone("body", (0, 0, P["hip_z"]), (0, 0.08, P["hip_z"]), "root")
for leg in SL.LEGS:
    Lg = L[leg]
    a, u = V(Lg["a"]), V(Lg["u"])
    f0, t0 = V(Lg["f0"]), V(Lg["t0"])
    bone(f"coxa_{leg}", Lg["Y0"], Lg["P1"], "body", roll_z=(0, 0, 1))
    bone(f"femur_{leg}", V(Lg["P1"]) + a * Lg["c_fem"], V(Lg["K"]) + a * Lg["c_fem"], f"coxa_{leg}", roll_z=a.cross(f0))
    bone(f"tibia_{leg}", V(Lg["K"]) + a * Lg["c_tib"], Lg["foot_rest"], f"femur_{leg}", roll_z=a.cross(t0))
    F = V(Lg["foot_rest"])
    bone(f"ik_{leg}", F, F + Vector((0, 0.04, 0)), "root")
bpy.ops.object.mode_set(mode="OBJECT")

# sanity: bone local X must equal the pitch axis a (femur/tibia) and coxa local Z must be world Z
axis_err = 0.0
for leg in SL.LEGS:
    a = V(L[leg]["a"])
    for bn in (f"femur_{leg}", f"tibia_{leg}"):
        axis_err = max(axis_err, (arm_data.bones[bn].matrix_local.to_3x3().col[0] - a).length)
    axis_err = max(axis_err, (arm_data.bones[f"coxa_{leg}"].matrix_local.to_3x3().col[2] - Vector((0, 0, 1))).length)
report["bone_axis_error"] = axis_err
assert axis_err < 1e-4, axis_err


# rigid parts: mesh data into the bone-tail frame, identity local transform (clean glTF node hierarchy)
def bone_parent(ob, bname):
    b = arm_data.bones[bname]
    B = b.matrix_local @ Matrix.Translation((0, b.length, 0))
    ob.data.transform(B.inverted())
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bname
    ob.matrix_parent_inverse = Matrix.Identity(4)
    ob.matrix_basis = Matrix.Identity(4)


bone_parent(body_ob, "body")
bone_parent(skin, "body")
for name, ob in parts.items():
    bone_parent(ob, name)

# ---------------------------------------------------------------- pose setup: rotation modes, limits, IK
arm["anymachine"] = ""  # filled below
for k, v in (("step_length", P["step_length"]), ("step_height", P["step_height"]), ("body_height", P["hip_z"]),
             ("speed", P["speed"]), ("duty", P["duty"]), ("crouch", 0.0), ("ik_blend", 0.0)):
    arm[k] = v
ui = arm.id_properties_ui("ik_blend")
ui.update(min=0.0, max=1.0, description="0 = baked FK actions, 1 = IK foot targets drive the legs (posing in Blender)")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
lim_rep = {}
for leg in SL.LEGS:
    lim = SL.limits_local(P, L[leg])
    lim_rep[leg] = lim
    for part, ax in (("coxa", "z"), ("femur", "x"), ("tibia", "x")):
        pb = arm.pose.bones[f"{part}_{leg}"]
        c = pb.constraints.new("LIMIT_ROTATION")
        c.owner_space = "LOCAL"
        c.use_limit_x = c.use_limit_y = c.use_limit_z = True
        for a_ in "xyz":
            lo, hi = lim[part] if a_ == ax else (0.0, 0.0)
            setattr(c, f"min_{a_}", lo)
            setattr(c, f"max_{a_}", hi)
        # IK locks + limits mirror the FK joint definition
        for a_ in "xyz":
            setattr(pb, f"lock_ik_{a_}", a_ != ax)
        setattr(pb, f"use_ik_limit_{ax}", True)
        setattr(pb, f"ik_min_{ax}", lim[part][0])
        setattr(pb, f"ik_max_{ax}", lim[part][1])
    ik = arm.pose.bones[f"tibia_{leg}"].constraints.new("IK")
    ik.name = "IK"
    ik.target, ik.subtarget = arm, f"ik_{leg}"
    ik.chain_count = 3
    ik.use_tail = True
    ik.use_stretch = False
    ik.iterations = 200
    # IK runs before the per-bone Limit Rotation of the tibia; keep it first in the stack
    tib = arm.pose.bones[f"tibia_{leg}"]
    tib.constraints.move(len(tib.constraints) - 1, 0)
    d = ik.driver_add("influence").driver
    d.type = "AVERAGE"
    vv = d.variables.new()
    vv.name = "ik"
    vv.targets[0].id = arm
    vv.targets[0].data_path = '["ik_blend"]'

# ---------------------------------------------------------------- bake motions
n_f = SL.frames_per_cycle(P)
_, seq_walk = SB.bake(arm, P, L, "walk", "walk")
SB.bake(arm, P, L, "idle", "idle")
SB.bake(arm, P, L, "crouch", "crouch")
_, seq_demo = SB.bake(arm, P, L, "walk_demo", "walk_demo", n_cycles=4)
SB.rest_pose(arm)
arm.animation_data.action = bpy.data.actions["walk_demo"]
sc.render.fps = P["fps"]
sc.frame_start, sc.frame_end = 1, 4 * n_f + 1


def used_range(seq):
    r = {}
    for _, _, sol in seq:
        for leg, s in sol.items():
            for i, part in enumerate(("coxa", "femur", "tibia")):
                lo, hi = r.get((leg, part), (1e9, -1e9))
                r[(leg, part)] = (min(lo, s["q"][i]), max(hi, s["q"][i]))
    return r


all_seq = seq_demo + SB.states(P, L, "idle") + SB.states(P, L, "crouch")
ur = used_range(all_seq)
within = all(lim_rep[leg][part][0] - 1e-9 <= lo and hi <= lim_rep[leg][part][1] + 1e-9 for (leg, part), (lo, hi) in ur.items())
report["commanded_within_limits"] = within
report["commanded_range_deg"] = {f"{part}_{leg}": [round(math.degrees(lo), 2), round(math.degrees(hi), 2)]
                                  for (leg, part), (lo, hi) in sorted(ur.items())}
report["unreachable_targets"] = sum(not s["reach_ok"] for _, _, sol in all_seq for s in sol.values())
T = n_f / P["fps"]
report["gait"] = {"frames_per_cycle": n_f, "period_s": T, "speed_mps": P["step_length"] / T, "duty": P["duty"],
                  "groups": {"A": sorted(SL.GROUP_A), "B": sorted(set(SL.LEGS) - SL.GROUP_A)},
                  "stance_stroke_m": P["duty"] * P["step_length"]}

# ---------------------------------------------------------------- joint spec (rides along as glTF extras)
spec = {"version": 1, "machine": "robot_spider", "units": "m", "up": "+Z (Blender) / +Y (glTF)", "forward": "-Y (Blender) / +Z (glTF)",
        "chains": [{"name": leg, "root_part": "chassis",
                    "joints": [{"name": f"{p}_{leg}", "type": "hinge", "bone": f"{p}_{leg}", "axis_local": ax,
                                "limits_deg": [round(math.degrees(x), 2) for x in lim_rep[leg][p]]}
                               for p, ax in (("coxa", "z"), ("femur", "x"), ("tibia", "x"))],
                    "end_effector": {"bone": f"tibia_{leg}", "at": "tail", "radius_m": P["foot_r"], "ik_target": f"ik_{leg}"},
                    "group": "A" if leg in SL.GROUP_A else "B"} for leg in SL.LEGS],
        "gait": {"type": "alternating_tetrapod", **report["gait"], "step_length_m": P["step_length"],
                 "step_height_m": P["step_height"], "body_height_m": P["hip_z"], "root_motion": "root bone, -Y"},
        "actions": {"walk": f"1 cycle, {n_f} frames @ {P['fps']} fps, root motion on `root`",
                    "idle": "3 s loop, feet planted", "crouch": "1 s linear: seek t = crouch amount (0..1)"}}
arm["anymachine"] = json.dumps(spec)

# embed the motion code so the .blend can rebake from its custom props
for fn in ("spider_lib.py", "spider_bake.py"):
    t = bpy.data.texts.new(fn)
    t.write(open(os.path.join(HERE, fn)).read())
t = bpy.data.texts.new("spider_rebake.py")
t.write('''# Run in Blender after editing the rig's custom props (step_length, step_height, body_height, speed, duty).
import bpy, json, sys, types
for name in ("spider_lib", "spider_bake"):
    mod = types.ModuleType(name); exec(bpy.data.texts[name + ".py"].as_string(), mod.__dict__); sys.modules[name] = mod
import spider_lib as SL, spider_bake as SB
arm = bpy.data.objects["spider_rig"]
P = json.loads(arm["anymachine_params"]); P.update(step_length=arm["step_length"], step_height=arm["step_height"],
    hip_z=arm["body_height"], speed=arm["speed"], duty=arm["duty"])
hw = json.loads(arm["anymachine_chassis_hw"])
L = SL.layout(P, lambda y: float(__import__("numpy").interp(y, hw["y"], hw["hw"])))
SB.bake(arm, P, L, "walk", "walk"); SB.bake(arm, P, L, "walk_demo", "walk_demo", n_cycles=4)
arm.animation_data.action = bpy.data.actions["walk_demo"]
''')
arm["anymachine_params"] = json.dumps(P)
arm["anymachine_chassis_hw"] = json.dumps({"y": [round(float(y), 4) for y in ys], "hw": [round(float(h), 4) for h in hw_c]})

report["parts"] = {o.name: len(o.data.polygons) for o in [body_ob, skin] + list(parts.values())}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump(report, open(OUT.replace(".blend", "_build.json"), "w"), indent=1)
print("BUILT", OUT, json.dumps({k: report[k] for k in ("measured", "gait", "commanded_within_limits", "unreachable_targets",
                                                       "bone_axis_error")}), flush=True)
