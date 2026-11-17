# make_station.py: one file to open and look at, the boat and the davit together (appended from their own .blend files).
#   blender -b --factory-startup --python make_station.py     -> ../station_view.blend
import bpy, os
HERE = os.path.dirname(os.path.abspath(__file__)); FAM = os.path.join(HERE, "..")
bpy.ops.wm.read_factory_settings(use_empty=True)
for d, n in (("survival_craft", "survival_craft"), ("lifeboat_davit", "lifeboat_davit")):
    f = os.path.join(FAM, d, n + ".blend")
    with bpy.data.libraries.load(f, link=False) as (src, dst): dst.objects = [x for x in src.objects]
    for o in dst.objects:
        if o is not None and o.type == "MESH" and not o.name.startswith("hi_"): bpy.context.scene.collection.objects.link(o)
        elif o is not None: bpy.data.objects.remove(o)
    for im in bpy.data.images:
        if im.source == "FILE" and not os.path.exists(bpy.path.abspath(im.filepath)):
            p = os.path.join(FAM, d, os.path.basename(im.filepath.replace("\\", "/")))
            if os.path.exists(p): im.filepath = p
out = os.path.join(FAM, "station_view.blend"); bpy.ops.wm.save_as_mainfile(filepath=out)
bpy.ops.file.make_paths_relative(); bpy.ops.wm.save_mainfile(); print("SAVED", out)
