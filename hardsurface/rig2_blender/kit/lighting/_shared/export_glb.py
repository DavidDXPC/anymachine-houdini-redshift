# export_glb.py: writes <id>/<id>.glb from each collected <id>/<id>.blend (the farm job skips the GLBs, see BAKE.md).
# Objects sit side by side in the .blend; each is exported at its own origin.
#   blender -b --factory-startup -t 4 --python export_glb.py [-- id ...]
import bpy, sys, os
A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FAM = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
IDS = ["wellglass", "tube_light", "flood", "obstruction_light", "helideck_lights", "escape_route", "beacon", "work_light"]
for fid in (A or IDS):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(FAM, fid, fid + ".blend"))
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    missing = [im.name for im in bpy.data.images if im.name.startswith("lighting_") and not os.path.exists(bpy.path.abspath(im.filepath))]
    if missing: raise SystemExit(f"{fid}: textures not found: {missing}")
    bpy.ops.object.select_all(action="DESELECT")
    loc = {o.name: tuple(o.location) for o in objs}
    for o in objs: o.location = (0, 0, 0); o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(FAM, fid, fid + ".glb"), export_format="GLB", use_selection=True, export_tangents=True, export_apply=True, export_yup=True)
    for o in objs: o.location = loc[o.name]
    n = len(bpy.data.images); bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)     # leftovers of the bake (tiles, decals)
    if len(bpy.data.images) < n: bpy.ops.wm.save_mainfile()
    print("exported", fid, [o.name for o in objs], "images", [im.name for im in bpy.data.images])
