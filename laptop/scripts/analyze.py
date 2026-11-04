"""Orient + scale a generated laptop to 0.32 m wide, then measure base slab, lid line and hinge from the YZ profile."""
import bpy, sys, math, json
from mathutils import Matrix, Vector
argv = sys.argv[sys.argv.index("--") + 1:]
glb, gen = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if gen.startswith("tripo"):
    for o in bpy.context.scene.objects:
        o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
vs = []
for o in meshes:
    vs += [o.matrix_world @ v.co for v in o.data.vertices]
if gen.startswith("tripo"):
    R = Matrix.Rotation(math.radians(-90), 3, "Z"); vs = [R @ v for v in vs]
lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
s = 0.32 / (hi.x - lo.x)
vs = [Vector(((v.x - (lo.x + hi.x) / 2) * s, (v.y - (lo.y + hi.y) / 2) * s, (v.z - lo.z) * s)) for v in vs]
lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
print("SCALED size", [round(x, 4) for x in hi - lo], "scale", round(s, 4))
# profile: for y bins, min/max z (central 60% of width only)
nb = 40
for b in range(nb):
    y0 = lo.y + (hi.y - lo.y) * b / nb; y1 = lo.y + (hi.y - lo.y) * (b + 1) / nb
    zs = [v.z for v in vs if y0 <= v.y < y1 and abs(v.x) < 0.1]
    if zs:
        print(f"Y {y0:+.4f} zmin {min(zs):.4f} zmax {max(zs):.4f} n {len(zs)}")
