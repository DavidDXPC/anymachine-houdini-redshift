"""Render the rigged spider.

blender -b [--python anyscene/builder/blender_gpu.py] --python render.py -- --blend out/spider.blend --out out/stills \
    --cam persp|side|front|joint|top|walk [--action walk_demo|idle|crouch|none] [--frames 1,13] [--anim] \
    [--engine CYCLES|EEVEE] [--samples 64] [--resx 1600 --resy 900] [--tag name]
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]


def opt(k, d=None, cast=str):
    return cast(argv[argv.index(k) + 1]) if k in argv else d


OUT = os.path.abspath(opt("--out"))
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(opt("--blend")))
sc = bpy.context.scene
arm = bpy.data.objects["spider_rig"]
CAM = opt("--cam", "persp")
ENGINE = opt("--engine", "CYCLES")
TAG = opt("--tag", CAM)
act = opt("--action", "walk_demo")
arm.animation_data.action = None if act == "none" else bpy.data.actions[act]
for t in arm.animation_data.nla_tracks:
    t.mute = True
if act != "none":
    sc.frame_start, sc.frame_end = [int(x) for x in bpy.data.actions[act].frame_range]

sc.render.resolution_x, sc.render.resolution_y = opt("--resx", 1600, int), opt("--resy", 900, int)
sc.render.engine = "CYCLES" if ENGINE == "CYCLES" else "BLENDER_EEVEE"
if ENGINE == "CYCLES":
    sc.cycles.samples = opt("--samples", 64, int)
    sc.cycles.use_denoising = True
    sc.cycles.device = "GPU"
else:
    sc.eevee.taa_render_samples = opt("--samples", 32, int)
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = opt("--exposure", -0.8, float)

w = bpy.data.worlds.new("studio")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.82, 0.85, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, -0.2, 0))
floor = bpy.context.active_object
fm = bpy.data.materials.new("floor")
fm.use_nodes = True
nt = fm.node_tree
b = nt.nodes["Principled BSDF"]
b.inputs["Roughness"].default_value = 0.6
# faint 10 cm grid so travel and foot planting are readable
tc = nt.nodes.new("ShaderNodeTexCoord")
mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (10, 10, 10)
ck = nt.nodes.new("ShaderNodeTexChecker")
ck.inputs["Color1"].default_value = (0.22, 0.225, 0.235, 1)
ck.inputs["Color2"].default_value = (0.19, 0.195, 0.205, 1)
ck.inputs["Scale"].default_value = 1.0
nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
floor.data.materials.append(fm)


def light(name, loc, energy, size, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA")
    l.energy, l.size, l.color = energy, size, color
    o = bpy.data.objects.new(name, l)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, -0.2, 0.1)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


light("key", (-1.3, -1.6, 1.8), 150, 1.4)
light("fill", (1.7, -0.6, 0.9), 45, 1.4, (0.9, 0.95, 1))
light("rim", (0.6, 1.6, 1.3), 110, 1.0)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam


def aim(tgt, off, lens=50, ortho=None):
    tgt = Vector(tgt)
    cam.location = tgt + Vector(off)
    cam.rotation_euler = (-Vector(off)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    cam.data.clip_start = 0.01


def root_y():
    return arm.pose.bones["root"].location.y


def set_cam():
    y = root_y()
    if CAM == "persp":
        aim((0, y, 0.08), (-0.95, -1.05, 0.75), 50)
    elif CAM == "side":
        aim((0, y, 0.12), (1.6, 0, 0.22), ortho=0.95)
    elif CAM == "front":
        aim((0, y, 0.10), (0, -1.6, 0.25), ortho=0.95)
    elif CAM == "top":
        aim((0, y, 0.0), (0, -0.0001, 1.6), ortho=0.95)
    elif CAM == "walk":  # static three-quarter; the robot walks across (root travels -Y)
        aim((0, -0.26, 0.08), (1.25, -0.38, 0.62), 40)
    elif CAM == "joint":  # look along the R2 hip-pitch / knee axes
        pb = arm.pose.bones["femur_R2"]
        k = arm.matrix_world @ pb.tail
        h = arm.matrix_world @ pb.head
        ax = (arm.matrix_world.to_3x3() @ pb.matrix.to_3x3()).col[0].normalized()
        mid = (h + k) / 2 + Vector((0, 0, -0.01))
        aim(mid, ax * 0.50 + Vector((0.0, 0, 0.20)), 45)


if "--anim" in argv:
    sc.frame_set(sc.frame_start)
    set_cam()
    sc.render.filepath = os.path.join(OUT, "f_")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(animation=True)
else:
    for f in [int(x) for x in opt("--frames", "1").split(",")]:
        sc.frame_set(f)
        set_cam()
        sc.render.filepath = os.path.join(OUT, f"{TAG}_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
print("RENDERED", OUT, flush=True)
