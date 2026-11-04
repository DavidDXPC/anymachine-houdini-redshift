"""Render the rigged quadruped.

blender -b [--python anyscene/builder/blender_gpu.py] --python render.py -- --blend out/quadruped.blend --out DIR
    --cam persp|side|knee|front|top [--action trot_forward] [--frames 1,10 | --anim] [--engine CYCLES|EEVEE]
    [--resx 1280 --resy 720] [--samples 48] [--track] [--name prefix]
--track: camera follows the root at the gait speed (seamless loop; the floor grid shows the motion).
"""
import bpy, sys, os, math, json
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None, c=str: c(argv[argv.index(k) + 1]) if k in argv else d
BLEND, OUT = opt("--blend"), os.path.abspath(opt("--out"))
CAM, ACTION, ENGINE = opt("--cam", "persp"), opt("--action", "trot_forward"), opt("--engine", "CYCLES")
NAME = opt("--name", CAM)
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(BLEND))
sc = bpy.context.scene
arm = bpy.data.objects["quadruped_rig"]
for e in [o for o in bpy.data.objects if o.name.startswith("ik_")]:
    e.hide_render = True
sc.render.resolution_x, sc.render.resolution_y = opt("--resx", 1280, int), opt("--resy", 720, int)
sc.render.engine = "CYCLES" if ENGINE == "CYCLES" else "BLENDER_EEVEE"
if ENGINE == "CYCLES":
    sc.cycles.samples = opt("--samples", 48, int)
    sc.cycles.use_denoising = True
    sc.cycles.device = "GPU"
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"

act = bpy.data.actions[ACTION]
for t in arm.animation_data.nla_tracks:
    t.mute = True
arm.animation_data.action = act
if getattr(arm.animation_data, "action_slot", None) is None and len(getattr(act, "slots", [])):
    arm.animation_data.action_slot = act.slots[0]
n_act = int(act.frame_range[1])
sc.frame_start, sc.frame_end = 1, n_act - (1 if ACTION in ("trot_forward", "trot", "idle") else 0)
p = {k: arm[k] for k in ("step_length", "speed", "fps")}
v = p["speed"]

# studio: ground with a fine grid so the motion and the foot contacts read
w = bpy.data.worlds.new("studio")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.8, 0.83, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.22
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
floor = bpy.context.active_object
fm = bpy.data.materials.new("floor")
fm.use_nodes = True
nt = fm.node_tree
bs = nt.nodes["Principled BSDF"]
bs.inputs["Roughness"].default_value = 0.6
tc = nt.nodes.new("ShaderNodeTexCoord")
mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (1 / 0.12, 1 / 0.12, 1)
bk = nt.nodes.new("ShaderNodeTexChecker")
bk.inputs["Scale"].default_value = 1.0
bk.inputs["Color1"].default_value = (0.42, 0.43, 0.45, 1)
bk.inputs["Color2"].default_value = (0.36, 0.37, 0.39, 1)
nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
nt.links.new(mp.outputs["Vector"], bk.inputs["Vector"])
nt.links.new(bk.outputs["Color"], bs.inputs["Base Color"])
floor.data.materials.append(fm)


def light(name, loc, energy, size, color=(1, 1, 1), parent=None):
    l = bpy.data.lights.new(name, "AREA")
    l.energy, l.size, l.color = energy, size, color
    o = bpy.data.objects.new(name, l)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (-Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if parent:
        o.parent = parent
    return o


rig_ctr = bpy.data.objects.new("rig_ctr", None)  # moves with the root in tracking shots
sc.collection.objects.link(rig_ctr)
for nm, loc, e, s_, c_ in (("key", (-1.6, -1.6, 2.2), 160, 1.6, (1, 0.98, 0.95)), ("fill", (1.8, -0.9, 1.0), 45, 1.6, (0.9, 0.95, 1)),
                           ("rim", (0.6, 1.8, 1.4), 140, 1.0, (1, 1, 1))):
    light(nm, loc, e, s_, c_, rig_ctr)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.parent = rig_ctr
views = {"persp": ((-1.25, -1.35, 0.72), (0, -0.04, 0.2), 50, None), "side": ((-2.0, 0, 0.22), (0, -0.02, 0.21), 50, 0.95),
         "front": ((0, -2, 0.3), (0, 0, 0.2), 50, 0.7), "top": ((0, 0, 2), (0, 0, 0), 50, 0.9),
         "wide": ((-1.7, -1.9, 0.95), (0, -0.06, 0.18), 40, None)}
spec = json.loads(arm["anymachine"])
if CAM == "knee":
    K = spec["legs"]["FL"]["knee"]
    views["knee"] = ((-1.0, K[1] - 0.3, K[2] + 0.2), (K[0], K[1] + 0.01, K[2] + 0.03), 50, 0.36)
loc, tgt, lens, ortho = views[CAM]
cam.location = Vector(tgt) + Vector(loc)
cam.rotation_euler = (-Vector(loc)).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = lens
cam.data.clip_start = 0.01
if ortho:
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
if "--track" in argv:
    # rig_ctr follows the root at the gait speed: keyed linearly over the clip
    rig_ctr.location = (0, 0, 0)
    rig_ctr.keyframe_insert("location", frame=1)
    rig_ctr.location = (0, -v * (n_act - 1) / p["fps"], 0)
    rig_ctr.keyframe_insert("location", frame=n_act)
    import importlib.util
    spec_ = importlib.util.spec_from_file_location("gait", os.path.join(os.path.dirname(os.path.abspath(__file__)), "gait.py"))
    gm = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(gm)
    for fc in gm._fcurves(rig_ctr.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"
elif ACTION == "trot_forward":
    arm.location.y = v * (n_act - 1) / p["fps"] / 2  # cross the frame centre

if "--anim" in argv:
    sc.render.filepath = os.path.join(OUT, f"{NAME}_")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(animation=True)
else:
    for f in [int(x) for x in opt("--frames", "1").split(",")]:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(OUT, f"{NAME}_{ACTION}_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
print("RENDERED", OUT, flush=True)
