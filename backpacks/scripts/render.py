"""Render a rigged bag: control stills (Cycles, from the controls .blend) or the demo animation (from the baked .blend).

stills: blender -b --python blender_gpu.py --python render.py -- --blend x.blend --out dir --stills [--samples 64]
anim:   blender -b --python render.py -- --blend x_baked.blend --out dir --anim [--engine EEVEE] [--res 960 540]
"""
import bpy, sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
from softlib import set_controls
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None, c=str: c(argv[argv.index(k) + 1]) if k in argv else d
BLEND, OUT = os.path.abspath(opt("--blend")), os.path.abspath(opt("--out"))
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
spec = json.loads(arm["anymachine"])
ANIM = "--anim" in argv
ENGINE = opt("--engine", "EEVEE" if ANIM else "CYCLES")
sc.render.resolution_x = opt("--resx", 960 if ANIM else 1280, int)
sc.render.resolution_y = opt("--resy", 540 if ANIM else 720, int)
if ENGINE == "CYCLES":
    sc.render.engine = "CYCLES"
    sc.cycles.samples = opt("--samples", 64, int)
    sc.cycles.use_denoising = True
    sc.cycles.device = "GPU"
else:
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.taa_render_samples = 24
        sc.eevee.use_shadows = True
    except Exception:
        pass
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
w = bpy.data.worlds.new("studio")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.8, 0.83, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.22
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
floor = bpy.context.active_object
fm = bpy.data.materials.new("floor")
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.43, 0.45, 1)
fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
floor.data.materials.append(fm)


def light(name, loc, energy, size, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA")
    l.energy, l.size, l.color = energy, size, color
    o = bpy.data.objects.new(name, l)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.3)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


light("key", (-1.2, -1.4, 1.8), 150, 1.2)
light("fill", (1.6, -0.9, 0.8), 45, 1.2, (0.9, 0.95, 1))
light("rim", (0.6, 1.6, 1.4), 120, 0.8)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50
H = spec.get("height", 0.6)


def aim(az, el=0.32, dist=None, tz=None):
    a = math.radians(az)
    d = Vector((math.sin(a), -math.cos(a), el)).normalized()
    t = Vector((0, 0, tz if tz is not None else H * 0.47))
    cam.location = t + d * (dist or H * 2.9)
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


if ANIM:
    ad = arm.animation_data
    for o in [arm] + [o.data.shape_keys for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys]:
        if o and o.animation_data:
            for t in o.animation_data.nla_tracks:
                t.mute = t.name != "demo"
    aim(-38, el=0.30, dist=H * 3.5, tz=H * 0.58)
    sc.render.filepath = os.path.join(OUT, "f_")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(animation=True)
else:
    if arm.animation_data:
        arm.animation_data.action = None
    D = {c["param"]: c["default"] for c in spec["controls"]}
    views = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in opt("--views", "").split(",") if kv}
    set_controls(arm, D)
    aim(-38)
    sc.render.filepath = os.path.join(OUT, "hero_threequarter.png")
    bpy.ops.render.render(write_still=True)
    for c in spec["controls"]:
        for v in (0, 1):
            set_controls(arm, dict(D, **{c["param"]: v}))
            aim(views.get(c["param"], -38))
            sc.render.filepath = os.path.join(OUT, f"{c['param']}_{v}.png")
            bpy.ops.render.render(write_still=True)
print("RENDERED", OUT, flush=True)
