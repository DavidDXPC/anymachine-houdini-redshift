"""Quick Eevee look at a rigged bag in several control states.
blender -b --python peek.py -- <blend> <out_prefix> "fill=0,lid_open=1" "lid_open=0.5" ... [--views 30,90,200] [--res 420]"""
import bpy, sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
from softlib import set_controls
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
blend, outp = argv[0], argv[1]
views = [30, 90, 200]
res = 420
states = []
i = 2
while i < len(argv):
    if argv[i] == "--views":
        views = [int(x) for x in argv[i + 1].split(",")]
        i += 2
    elif argv[i] == "--res":
        res = int(argv[i + 1])
        i += 2
    else:
        states.append(argv[i])
        i += 1
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if arm.animation_data:
    arm.animation_data.action = None
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = sc.render.resolution_y = res
w = bpy.data.worlds.new("w")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.77, 0.8, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.5
sc.collection.objects.link(sun)
sun.rotation_euler = (0.8, 0.2, -0.6)
bpy.ops.mesh.primitive_plane_add(size=4)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50
H = 0.6
for si, st in enumerate(states):
    vals = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in st.split(",") if kv}
    set_controls(arm, vals)
    for az in views:
        a = math.radians(az)
        d = Vector((math.sin(a), -math.cos(a), 0.45)).normalized()
        cam.location = Vector((0, 0, H * 0.48)) + d * 1.25
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = f"{outp}_s{si}_{az:03d}.png"
        bpy.ops.render.render(write_still=True)
print("PEEKED", flush=True)
