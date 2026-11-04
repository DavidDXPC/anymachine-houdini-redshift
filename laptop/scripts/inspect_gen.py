"""Import a generated GLB, bake transforms, report bbox + a coarse height profile along Y, render 3 eevee views."""
import bpy, sys, math, os
from mathutils import Matrix, Vector
argv = sys.argv[sys.argv.index("--") + 1:]
glb, out, gen = argv[0], argv[1], argv[2]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if gen.startswith("tripo"):
    for o in bpy.context.scene.objects:
        o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.data.transform(mw); o.matrix_world = Matrix.Identity(4)
for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
    bpy.data.objects.remove(o)
print("MESHES", [(o.name, len(o.data.vertices), len(o.data.polygons), [m.name for m in o.data.materials]) for o in meshes])
vs = [v.co for o in meshes for v in o.data.vertices]
lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
print("BBOX lo", tuple(round(x, 4) for x in lo), "hi", tuple(round(x, 4) for x in hi), "size", tuple(round(x, 4) for x in hi - lo))
# render ortho views
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 800, 600
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
c = (lo + hi) / 2; R = (hi - lo).length
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = R * 1.1
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.energy = 3
sun.rotation_euler = (0.6, 0.2, 0.5)
views = {"front_negY": (0, -1, 0), "side_posX": (1, 0, 0), "top": (0, 0, 1), "persp": (0.7, -1, 0.6), "front_posX": (-1, 0, 0), "back_posY": (0, 1, 0)}
for name, d in views.items():
    d = Vector(d).normalized()
    cam.location = c + d * R * 2
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)
