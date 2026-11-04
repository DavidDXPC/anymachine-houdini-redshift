"""Try a face-classification cut on a normalised generated bag and render the pieces (debug).
blender -b --factory-startup --python cuttest.py -- <glb> <rotz> <height> <out_prefix> <predicate python expr in c (centroid)>"""
import bpy, bmesh, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from softlib import *
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
glb, rz, H, outp, expr = argv[0], float(argv[1]), float(argv[2]), argv[3], argv[4]
ob = load_gen(glb, rz, H)
me = ob.data
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
bm.to_mesh(me); bm.free(); bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
samp = tex_sampler(ob)
uvl = bm.loops.layers.uv.active
def fcol(f):
    us = [l[uvl].uv for l in f.loops]
    return samp((sum(u[0] for u in us) / len(us), sum(u[1] for u in us) / len(us)))
sel = [f for f in bm.faces if eval(expr, {"c": f.calc_center_median(), "col": fcol(f), "abs": abs, "math": math, "max": max})]
selset = set(sel)
print("SELECTED", len(sel), "of", len(bm.faces))
# connected components of the selected set and of the rest
def comps(faces):
    fs = set(faces); out = []
    while fs:
        st = [fs.pop()]; comp = [st[0]]
        while st:
            f = st.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in fs:
                        fs.remove(g); st.append(g); comp.append(g)
        out.append(comp)
    return sorted(out, key=len, reverse=True)
for name, fl in (("sel", sel), ("rest", [f for f in bm.faces if f not in selset])):
    cs = comps(fl)
    print(name, "components", len(cs))
    for c in cs[:12]:
        pts = [v.co for f in c for v in f.verts]
        lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
        print("  ", len(c), tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi))
selidx = {f.index for f in sel}
bm.free()
# render: selected in red overlay via material index trick
red = mat("sel_red", (0.9, 0.05, 0.05), 0.5)
me.materials.append(red)
ri = len(me.materials) - 1
for p in me.polygons:
    if p.index in selidx:
        p.material_index = ri
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4; sc.collection.objects.link(sun); sun.rotation_euler = (0.7, 0.2, -0.5)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
sc.render.resolution_x = sc.render.resolution_y = 500
for az in (30, 120, 210):
    a = math.radians(az); d = Vector((math.sin(a), -math.cos(a), 0.5)).normalized()
    cam.location = Vector((0, -0.05, H / 2)) + d * 1.5; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{outp}_{az:03d}.png"; bpy.ops.render.render(write_still=True)
print("DONE")
