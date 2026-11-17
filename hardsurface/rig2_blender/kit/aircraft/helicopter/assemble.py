# assemble.py: joins the three baked part files from the farm (part_heli_body / _mech / _interior .blend, each with its
# own UVs and baked material) into helicopter.blend and helicopter.glb.  No baking, no rendering: seconds.
#   blender -b --factory-startup --python assemble.py
import bpy, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
st = json.load(open(os.path.join(HERE, "stats.json")))
for s in ("heli_body", "heli_mech", "heli_interior"):
    p = os.path.join(HERE, f"part_{s}.blend")
    with bpy.data.libraries.load(p, link=False) as (src, dst): dst.objects = list(src.objects)
    for o in dst.objects: bpy.context.scene.collection.objects.link(o)
    st["sets"][s] = json.load(open(os.path.join(HERE, f"stats_{s}.json")))
for im in bpy.data.images:
    q = os.path.join(HERE, os.path.basename(im.filepath.replace("\\", "/")))
    if im.filepath and os.path.exists(q): im.filepath = "//" + os.path.basename(q); im.reload()
objs = [o for o in bpy.data.objects if o.type == "MESH"]
tri = lambda o: (o.data.calc_loop_triangles(), len(o.data.loop_triangles))[1]
st["objects"] = {o.name: tri(o) for o in objs}; st["tris"] = sum(st["objects"].values()); st["tris_glass"] = st["objects"].get("heli_glass", 0); st["tris_baked"] = st["tris"] - st["tris_glass"]
json.dump(st, open(os.path.join(HERE, "stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "helicopter.blend"))
bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "helicopter.glb"), export_format="GLB", use_selection=True, export_tangents=True, export_apply=True, export_yup=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "helicopter.blend"))
print("assembled", st["objects"])
