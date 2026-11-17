"""VAL final stage: prebake blend + baked textures -> val_detailed.blend, val_detailed.glb (one material, 2K webp).

  blender --background --python val_finish.py
"""
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import detail_shader as ds  # noqa: E402

MDIR = os.path.dirname(HERE)
bpy.ops.wm.open_mainfile(filepath=os.path.join(MDIR, "work", "val_prebake.blend"))
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
co = np.zeros(len(me.vertices) * 3, dtype=np.float32)
me.attributes["opos"].data.foreach_get("vector", co)
me.vertices.foreach_set("co", co)
imgs = {}
for p, cs in (("base", "sRGB"), ("orm", "Non-Color"), ("normal", "Non-Color")):
    im = bpy.data.images.load(os.path.join(MDIR, "textures", "val_%s.png" % p))
    im.colorspace_settings.name = cs
    im.pack()
    imgs[p] = im
old = list(me.materials)
final = ds.make_final_material("M_val", imgs)
me.materials.clear()
me.materials.append(final)
for p in me.polygons:
    p.material_index = 0
for m in old:
    bpy.data.materials.remove(m)
for n in ("opos", "stipple", "lathe", "bare"):
    if n in me.attributes:
        me.attributes.remove(me.attributes[n])
for coll in (bpy.data.materials, bpy.data.images, bpy.data.node_groups):
    for x in list(coll):
        if x.users == 0:
            coll.remove(x)
me.update()
blend = os.path.join(MDIR, "val_detailed.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
glb = os.path.join(MDIR, "val_detailed.glb")
for o in bpy.context.scene.objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_yup=True, export_skins=True,
                          export_animations=False, export_apply=False, export_image_format="WEBP",
                          export_image_quality=int(os.environ.get("VAL_WEBP_Q", "86")), export_tangents=False,
                          export_materials="EXPORT")
me.calc_loop_triangles()
print("VAL RESULT tris=%d glb_bytes=%d" % (len(me.loop_triangles), os.path.getsize(glb)))
