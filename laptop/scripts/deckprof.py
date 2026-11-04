import bpy, sys, math
from mathutils import Matrix, Vector
argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=argv[0])
for o in bpy.context.scene.objects:
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
me = o.data; me.transform(Matrix.Rotation(math.radians(-90), 4, "Z") @ o.matrix_world)
vs = [v.co for v in me.vertices]
lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
s = 0.32 / (hi.x - lo.x)
me.transform(Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))
bins = {}
for p in me.polygons:
    c = p.center
    if p.normal.z > 0.9 and abs(c.x) < 0.14 and c.z < 0.02:
        bins.setdefault(int((c.y + 0.1416) / 0.01), []).append((c.z, p.area))
for b in sorted(bins):
    l = sorted(bins[b]); tot = sum(a for _, a in l); acc = 0
    qs = []
    for q in (0.1, 0.5, 0.9):
        acc = 0
        for z, a in l:
            acc += a
            if acc >= q * tot: qs.append(z); break
    print(f"y {-0.1416 + b * 0.01:+.3f} up-face z q10/50/90 " + " ".join(f"{z*1000:.1f}" for z in qs) + f" area {tot*1e4:.1f}cm2")
# also side wall check: faces with |normal.x|>0.9 near x edges
side = [p for p in me.polygons if abs(p.normal.x) > 0.9 and abs(p.center.x) > 0.155]
print("side wall faces", len(side), "area cm2", sum(p.area for p in side) * 1e4)
