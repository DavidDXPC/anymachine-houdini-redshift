"""Normalise a generated bag and dump z-slice profiles + ortho front/side/top views (800 px = 0.8 m, so 1 px = 1 mm).
blender -b --factory-startup --python probe.py -- <glb> <rotz> <height> <out_prefix>
Image coords: front view x_px = 400 + x_mm, z_px = 800 - (z_mm - 0)... camera centred at z=0.4 so z_mm = 800 - y_px."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from softlib import *

argv = sys.argv[sys.argv.index("--") + 1:]
glb, rz, H, outp = argv[0], float(argv[1]), float(argv[2]), argv[3]
ob = load_gen(glb, rz, H)
lo, hi = bounds(ob)
print("BOUNDS", tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi))
vs = [v.co for v in ob.data.vertices]
for z0 in [i * 0.02 for i in range(int(hi.z / 0.02) + 1)]:
    sl = [v for v in vs if z0 <= v.z < z0 + 0.02]
    if not sl:
        continue
    c = [v for v in sl if abs(v.x) < 0.03]
    print(f"z {z0:.2f} x[{min(v.x for v in sl):+.3f},{max(v.x for v in sl):+.3f}] y[{min(v.y for v in sl):+.3f},{max(v.y for v in sl):+.3f}]"
          + (f" ctr y[{min(v.y for v in c):+.3f},{max(v.y for v in c):+.3f}]" if c else ""))
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
w = bpy.data.worlds.new("w")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.9, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = 0.8
sc.render.resolution_x = sc.render.resolution_y = 800
for name, loc, rot in (("front", (0, -2, 0.4), (math.pi / 2, 0, 0)), ("side", (2, 0, 0.4), (math.pi / 2, 0, math.pi / 2)),
                       ("top", (0, 0, 3), (0, 0, 0))):
    cam.location, cam.rotation_euler = loc, rot
    sc.render.filepath = f"{outp}_{name}.png"
    bpy.ops.render.render(write_still=True)
print("PROBED")
