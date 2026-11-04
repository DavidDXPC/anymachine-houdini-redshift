"""Demo timeline + jiggle bake + GLB export for a soft-goods rig.

blender -b --python export.py -- --blend out/x/x.blend --glb out/x/x.glb --baked out/x/x_baked.blend

1. Keys the custom props (and a root 'carry bob') into a demo timeline in the .blend (re-saved, controls intact).
2. Evaluates every frame; dangling chains (spec.jiggle.chains) are re-simulated as damped springs that lag the
   evaluated pose, so straps/buckles swing when the pack moves. Pinned (clipped) chains follow exactly.
3. Writes a baked copy: constraints/drivers removed, actions = <ctl>_param (1 s, seek t = param) for every control
   (bones + shape keys, same NLA track name) and `demo` (everything, incl. jiggle). Exports GLB from it.
"""
import bpy, sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
from softlib import *
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
BLEND, GLB, BAKED = [os.path.abspath(opt(k)) for k in ("--blend", "--glb", "--baked")]
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
spec = json.loads(arm["anymachine"])
ctl = {c["param"]: c for c in spec["controls"]}
D = {k: c["default"] for k, c in ctl.items()}

# ------------------------------------------------------------------ demo schedule: (frame, {prop: value}); bob spans
S = spec["demo"]
keys, bobs = S["keys"], S.get("bob", [])
END = max([k[0] for k in keys] + [b for a, b in bobs]) + 8
sc.frame_start, sc.frame_end = 1, END
ad = arm.animation_data or arm.animation_data_create()
drive = bpy.data.actions.new("demo_drive")
ad.action = drive
state = dict(D)
for f, vals in keys:
    state.update(vals)
    for k, v in state.items():
        arm[k] = float(v)
        arm.keyframe_insert(f'["{k}"]', frame=f)
for fc in iter_fcurves(drive):
    for kp in fc.keyframe_points:
        kp.interpolation = "BEZIER"
        kp.easing = "EASE_IN_OUT"
root = arm.pose.bones["root"]
for (a, b) in bobs:  # carry bob: lift, sway and set down
    for f in range(a, b + 1):
        t = (f - a) / (b - a)
        env = math.sin(math.pi * t) ** 0.7
        root.location = (0, 0, 0)
        root.rotation_quaternion = (1, 0, 0, 0)
        arm.data.bones["root"]  # root bone points +Z: local Y = world Z
        lift = 0.10 * env + 0.025 * env * math.sin(2 * math.pi * 2.2 * t * (b - a) / 24)
        sway = math.radians(7) * env * math.sin(2 * math.pi * 1.4 * t * (b - a) / 24)
        root.location = (0.04 * env * math.sin(2 * math.pi * 0.9 * t * (b - a) / 24), lift, 0)  # local: x, y(=up), z
        root.rotation_quaternion = Matrix.Rotation(sway, 4, "Y").to_quaternion()  # about the bone's (vertical) axis -> yaw
        root.rotation_quaternion = (Matrix.Rotation(sway, 3, "Z") @ Matrix.Rotation(sway * 0.6, 3, "X")).to_quaternion()
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_quaternion", frame=f)
    for f in (a - 1, b + 1):
        root.location, root.rotation_quaternion = (0, 0, 0), (1, 0, 0, 0)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_quaternion", frame=f)
for fc in iter_fcurves(drive):
    if "root" in fc.data_path:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
drive.use_fake_user = True
bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)  # .blend: controls + demo timeline (no jiggle)

# ------------------------------------------------------------------ evaluate all frames
bones = [b.name for b in arm.data.bones]
skobs = [o for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys]
frames = list(range(1, END + 1))
EV = []  # per frame: {bone: armature-space matrix}, {obj: {key: value}}, props
for f in frames:
    sc.frame_set(f)
    bpy.context.view_layer.update()
    m = {bn: arm.pose.bones[bn].matrix.copy() for bn in bones}
    skv = {o.name: {kb.name: kb.value for kb in o.data.shape_keys.key_blocks[1:]} for o in skobs}
    EV.append((m, skv, {k: float(arm[k]) for k in D}))

# ------------------------------------------------------------------ jiggle: damped springs lagging the evaluated pose
J = spec.get("jiggle", {})
for ch in J.get("chains", []):
    names = sorted([b for b in bones if b.startswith(ch["prefix"])], key=lambda s: int(s[len(ch["prefix"]):]))
    pin_expr = ch.get("pinned_when")  # python expr over props: chain follows exactly when true-ish (0..1)
    n = len(names)
    tip = lambda M, bn: M @ Vector((0, arm.data.bones[bn].length, 0))
    X = None
    V = None
    k0, c0 = ch.get("k", 60.0), ch.get("c", 5.0)
    for fi, (M, _, props) in enumerate(EV):
        tgt = [M[names[0]].translation.copy()] + [tip(M[bn], bn) for bn in names]
        if X is None:
            X, V = [p.copy() for p in tgt], [Vector() for _ in tgt]
        pin = eval(pin_expr, {}, dict(props, smoothstep=smoothstep)) if pin_expr else 0.0
        dt = 1 / 24 / 8
        for _ in range(8):
            X[0] = tgt[0].copy()
            for i in range(1, n + 1):
                k = k0 / (1 + 0.6 * (i - 1))
                a = (tgt[i] - X[i]) * k - V[i] * c0
                V[i] += a * dt
                X[i] += V[i] * dt
            for _ in range(3):  # keep link lengths
                for i in range(n):
                    L = (tgt[i + 1] - tgt[i]).length
                    d = X[i + 1] - X[i]
                    X[i + 1] = X[i] + d.normalized() * L
        P = [tgt[i].lerp(X[i], 1 - pin) for i in range(n + 1)]
        # re-aim each bone of the chain at its simulated tail (minimal rotation from the evaluated pose)
        for i, bn in enumerate(names):
            Me = M[bn]
            de = (tip(Me, bn) - Me.translation).normalized()
            dn = (P[i + 1] - P[i]).normalized()
            R = de.rotation_difference(dn).to_matrix().to_4x4()
            Mn = R @ Matrix.Translation(-Me.translation) @ Me
            Mn.translation = P[i]
            M[bn] = Mn
        # children of jiggled bones (rigid parts ride along automatically since objects are bone-parented)

# ------------------------------------------------------------------ baked copy
for pb in arm.pose.bones:
    for c in list(pb.constraints):
        pb.constraints.remove(c)
for o in skobs:
    k = o.data.shape_keys
    if k.animation_data:
        for d in list(k.animation_data.drivers):
            k.animation_data.drivers.remove(d)
ad.action = None


def local_from_arm(Mall):
    out = {}
    for bn in bones:
        b = arm.data.bones[bn]
        if b.parent:
            out[bn] = (Mall[b.parent.name] @ (b.parent.matrix_local.inverted() @ b.matrix_local)).inverted() @ Mall[bn]
        else:
            out[bn] = b.matrix_local.inverted() @ Mall[bn]
    return out


def add_track(idblock, act, name):
    a = idblock.animation_data or idblock.animation_data_create()
    a.action = None
    t = a.nla_tracks.new()
    t.name = name
    st = t.strips.new(name, int(act.frame_range[0]), act)
    st.name = name


demo = bpy.data.actions.new("demo")
ad.action = demo
for fi, f in enumerate(frames):
    L = local_from_arm(EV[fi][0])
    for bn in bones:
        pb = arm.pose.bones[bn]
        loc, rot, s = L[bn].decompose()
        pb.location, pb.rotation_quaternion, pb.scale = loc, rot, s
        for path in ("location", "rotation_quaternion", "scale"):
            pb.keyframe_insert(path, frame=f)
linearize(demo)
ad.action = None
add_track(arm, demo, "demo")
for c in ctl:  # the per-control param actions already exist (built by control_action)
    if f"{c}_param" in bpy.data.actions:
        add_track(arm, bpy.data.actions[f"{c}_param"], f"{c}_param")
for o in skobs:
    key = o.data.shape_keys
    kad = key.animation_data or key.animation_data_create()
    act = bpy.data.actions.new(f"{o.name}_demo_keys")
    kad.action = act
    for fi, f in enumerate(frames):
        for kn, v in EV[fi][1][o.name].items():
            key.key_blocks[kn].value = v
            key.key_blocks[kn].keyframe_insert("value", frame=f)
    linearize(act)
    kad.action = None
    add_track(key, act, "demo")
    # per-control shape-key param actions: sample the driver expressions recorded in the spec
    for c, cs in ctl.items():
        sks = [s.split(":")[1] for s in cs.get("shape_keys", []) if s.split(":")[0] == o.name]
        if not sks:
            continue
        act = bpy.data.actions.new(f"{o.name}_{c}_keys")
        kad.action = act
        for k in range(PARAM_FRAMES + 1):
            p = k / PARAM_FRAMES
            for kn in sks:
                key.key_blocks[kn].value = eval(cs["shape_key_expr"][kn], {"min": min, "max": max, "abs": abs, "p": p})
                key.key_blocks[kn].keyframe_insert("value", frame=1 + k)
        linearize(act)
        kad.action = None
        add_track(key, act, f"{c}_param")
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
for o in skobs:
    for kb in o.data.shape_keys.key_blocks[1:]:
        kb.value = 0.0
# rig-node extras: the joint spec (glTF consumers read it from the armature node)
arm["anymachine"] = json.dumps({k: v for k, v in spec.items() if k not in ("check", "demo")})
for k in D:
    arm[k] = float(D[k])
for o in bpy.data.objects:
    if o.type == "MESH":
        o.data.name = o.name
for img in bpy.data.images:  # textures <= 2K
    if img.size[0] > 2048:
        f_ = 2048 / max(img.size)
        img.scale(int(img.size[0] * f_), int(img.size[1] * f_))
        img.pack()
bpy.ops.wm.save_as_mainfile(filepath=BAKED, compress=True)
for o in bpy.data.objects:
    o.select_set(o == arm or o.parent == arm)
for o in bpy.data.objects:  # bevel modifiers on rigid parts are applied by export_apply
    pass
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
                          export_animations=True, export_animation_mode="NLA_TRACKS", export_extras=True,
                          export_force_sampling=True, export_morph=True, export_morph_animation=True,
                          export_image_format="JPEG", export_jpeg_quality=88)
print("EXPORTED", GLB, os.path.getsize(GLB) // 1024, "KB", "frames", END, flush=True)
