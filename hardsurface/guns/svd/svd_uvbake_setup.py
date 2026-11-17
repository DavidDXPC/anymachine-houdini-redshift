# Continuation of svd_build.py (exec'd in its namespace): zones, bake explode, UVs, decal sheets, bake materials.
# Saves work/svd_prebake.blend, ready for svd_bake.py.
import random  # noqa: E402

CFG["sheets"] = [
    # left receiver wall, in front of the scope rail
    dict(name="L", origin=(0, -14, -6), right=(0, 1, 0), up=(0, 0, 1), w=30, h=8, res_w=4096, facing=(1, 0, 0),
         depth=(1.2, 2.0), items=[("text", 1.9, 4.45, 0.30, "2741", "recess"), ("ring", 0.85, 4.45, 0.15, 0.04, "recess")]),
    # rear sight leaf, seen from above: range numbers and lines
    dict(name="T", origin=(XC + 0.5, -13.3, 0), right=(-1, 0, 0), up=(0, -1, 0), w=1.0, h=6.4, res_w=512,
         facing=(0, 0, 1), depth=(2.5, 2.9),
         items=[it for i, s_ in enumerate(("12", "10", "8", "6", "4", "2"))
                for it in (("text", 0.5, 0.75 + i * 0.5, 0.2, s_, "paint"), ("rect", 0.5, 0.98 + i * 0.5, 0.7, 0.025, 0, "recess"))
                if not (2.9 < 0.75 + i * 0.5 < 3.9)]),
]

zone_names = ["stipple", "lathe", "bare"]
cent = np.zeros(len(me.polygons) * 3)
me.polygons.foreach_get("center", cent)
cent = cent.reshape(-1, 3)
r_bore = np.hypot(cent[:, 0] - XC, cent[:, 2] - sp.ZB)
lathe = ((cent[:, 1] < -45.0) & (r_bore < 1.0)).astype(np.float32)          # turned barrel and muzzle sleeve
for zn in zone_names:
    at = me.attributes.new(zn, "FLOAT", "FACE")
    at.data.foreach_set("value", lathe if zn == "lathe" else np.zeros(len(me.polygons), dtype=np.float32))

# explode the animated parts for the bake (see tools/detail_build.py); "opos" keeps the assembled position
nv = len(me.vertices)
co0 = np.zeros(nv * 3, dtype=np.float32)
me.vertices.foreach_get("co", co0)
at = me.attributes.new("opos", "FLOAT_VECTOR", "POINT")
at.data.foreach_set("vector", co0)
co1 = co0.reshape(-1, 3).copy()
for v in me.vertices:
    for ge in v.groups:
        if ge.weight > 0.5:
            co1[v.index, 2] -= 150.0 * (ge.group + 1)
            break
me.vertices.foreach_set("co", co1.ravel())
me.update()

bpy.context.view_layer.objects.active = ob
for o in bpy.context.scene.objects:
    o.select_set(o is ob)
wn = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
wn.keep_sharp = True
wn.weight = 50
wn.mode = "FACE_AREA"
bpy.ops.object.modifier_apply(modifier="WN")

# ------------------------------------------------------------------ UVs
while me.uv_layers:
    me.uv_layers.remove(me.uv_layers[0])
me.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0, correct_aspect=True,
                         scale_to_bounds=False)
bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode="OBJECT")

bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)
random.seed(1)
dirs = []
while len(dirs) < 24:
    d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
    if 0.1 < d.length < 1:
        dirs.append(d.normalized())
vis = []
for f in bm.faces:
    c = f.calc_center_median() + f.normal * 0.01
    free = tot = 0
    for d in dirs:
        if d.dot(f.normal) < 0.15:
            continue
        tot += 1
        if bvh.ray_cast(c, d, 200.0)[0] is None:
            free += 1
    vis.append(free / max(tot, 1))
uvl = bm.loops.layers.uv.active
parent = list(range(len(bm.faces)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for e in bm.edges:
    if len(e.link_faces) != 2:
        continue
    la, lb = e.link_loops[0], e.link_loops[1]
    a0, a1 = la[uvl].uv, la.link_loop_next[uvl].uv
    b0, b1 = lb[uvl].uv, lb.link_loop_next[uvl].uv
    if (a0 - b1).length < 1e-5 and (a1 - b0).length < 1e-5:
        ra, rb = find(la.face.index), find(lb.face.index)
        if ra != rb:
            parent[ra] = rb
isl = {}
for f in bm.faces:
    isl.setdefault(find(f.index), []).append(f)
hidden = 0
for fs in isl.values():
    area = sum(f.calc_area() for f in fs)
    v = sum(vis[f.index] * f.calc_area() for f in fs) / max(area, 1e-9)
    sc_ = 0.3 if v < 0.04 else (0.6 if v < 0.2 else 1.0)
    cen = sum((f.calc_center_median() for f in fs), Vector()) / len(fs)
    if cen.y > -22 and cen.y < 20 and cen.z > -160:      # receiver, sights and bolt sit closest to the eye
        sc_ *= 1.25
    if sc_ < 1:
        hidden += 1
    if sc_ != 1.0:
        loops = [l for f in fs for l in f.loops]
        cu = sum((l[uvl].uv for l in loops), Vector((0, 0))) / len(loops)
        for l in loops:
            l[uvl].uv = cu + (l[uvl].uv - cu) * sc_
print("SVD uv islands %d, shrunk %d" % (len(isl), hidden))
bm.to_mesh(me)
bm.free()
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
try:
    bpy.ops.uv.pack_islands(margin=0.0012, rotate=True, shape_method="CONCAVE", margin_method="FRACTION")
except TypeError:
    bpy.ops.uv.pack_islands(margin=0.0012, rotate=True)
bpy.ops.object.mode_set(mode="OBJECT")
me.calc_loop_triangles()
uv = np.zeros(len(me.loops) * 2)
me.uv_layers[0].data.foreach_get("uv", uv)
uv = uv.reshape(-1, 2)
a_uv = a_3d = 0.0
for t in me.loop_triangles:
    p = [uv[i] for i in t.loops]
    a_uv += abs((p[1][0] - p[0][0]) * (p[2][1] - p[0][1]) - (p[2][0] - p[0][0]) * (p[1][1] - p[0][1])) / 2
    a_3d += t.area
print("SVD tris %d  surface %.0f cm2  uv fill %.2f  texel density %.2f px/mm at %d" %
      (len(me.loop_triangles), a_3d, a_uv, math.sqrt(a_uv * OUT_RES * OUT_RES / (a_3d * 100.0)), OUT_RES))

# ------------------------------------------------------------------ bake materials
dc.use_cycles(16)
sc = bpy.context.scene
sheets = ds.render_sheets(CFG, WORK)
for sh, img in sheets:
    img.pack()
group = ds.build_group(CFG, sheets)
for i, m in enumerate(list(me.materials)):
    cls = m.name[2:]
    me.materials[i] = ds.make_bake_material("BAKE_" + cls, group, ds.CLASS_PARAMS[cls])
for o in list(bpy.data.objects):
    if o.name.startswith(("ba", "bb", "rm")):
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "svd_prebake.blend"), compress=True)
print("SVD PREBAKE SAVED")
