"""How deep is the generated microwave's cavity? Ray-cast from in front of the opening straight in (Tripo frame, front +X)."""
import bpy, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=argv[0])
for o in bpy.context.scene.objects:
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
vs = [o.matrix_world @ v.co for v in o.data.vertices]
bvh = BVHTree.FromPolygons(vs, [p.vertices[:] for p in o.data.polygons])
lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
depth = hi.x - lo.x
print("BODY depth(x) %.3f width(y) %.3f height(z) %.3f" % (depth, hi.y - lo.y, hi.z - lo.z))
for fy in (0.3, 0.45, 0.6):
    for fz in (0.3, 0.5, 0.7):
        p = Vector((hi.x + 0.1, lo.y + fy * (hi.y - lo.y), lo.z + fz * (hi.z - lo.z)))
        h = bvh.ray_cast(p, Vector((-1, 0, 0)))
        print(f"ray y={fy} z={fz}: hit depth into body = {(hi.x - h[0].x) / depth:.2f} of body depth" if h[0] else "miss")
