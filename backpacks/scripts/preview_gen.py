"""Import a generated GLB as-is, report bounds/tris/materials, render 4 views (azimuth 0/90/180/270 around Z) in Eevee.
blender -b --factory-startup --python preview_gen.py -- <glb> <out_prefix> [--reset-rot]"""
import bpy, sys, os, math
from mathutils import Vector, Matrix
argv = sys.argv[sys.argv.index("--") + 1:]
glb, outp = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
for o in bpy.context.scene.objects:
    print("OBJ", o.name, o.type, tuple(round(x, 3) for x in o.rotation_quaternion) if o.rotation_mode == "QUATERNION" else tuple(o.rotation_euler), tuple(o.scale))
if "--reset-rot" in argv:
    for o in bpy.context.scene.objects:
        o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ v.co for o in ms for v in o.data.vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
print("BOUNDS", tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi), "tris", sum(len(o.data.polygons) for o in ms))
for o in ms:
    print("MATS", o.name, [(m.name, [n.image.name + f" {n.image.size[0]}" for n in m.node_tree.nodes if n.type == "TEX_IMAGE"]) for m in o.data.materials])
c = (lo + hi) / 2; R = (hi - lo).length * 1.3
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x, sc.render.resolution_y = 480, 480
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.8, 0.8, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 3; sc.collection.objects.link(sun); sun.rotation_euler = (0.6, 0.3, 0.4)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
for az in (0, 90, 180, 270):
    a = math.radians(az)
    d = Vector((math.sin(a), -math.cos(a), 0.35)).normalized()  # az 0 = camera at -Y looking +Y
    cam.location = c + d * R; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{outp}_{az:03d}.png"; bpy.ops.render.render(write_still=True)
print("PREVIEWED")
