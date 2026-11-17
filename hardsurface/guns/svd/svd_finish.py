"""Final stage: prebake blend + baked PNGs -> svd_detailed.blend and svd_detailed.glb (gun rig + mesh, one material).

  blender --background models/svd/work/svd_prebake.blend --python svd_finish.py
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detail_shader as ds  # noqa: E402

MDIR = os.path.join(os.environ.get("GAME_ROOT", "."), "models", "svd")
TEXD = os.path.join(MDIR, "textures")
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
# back to the assembled gun
co = np.zeros(len(me.vertices) * 3, dtype=np.float32)
me.attributes["opos"].data.foreach_get("vector", co)
me.vertices.foreach_set("co", co)
for nm in ("opos", "stipple", "lathe", "bare"):
    me.attributes.remove(me.attributes[nm])
imgs = {}
for p, cs in (("base", "sRGB"), ("orm", "Non-Color"), ("normal", "Non-Color")):
    im = bpy.data.images.load(os.path.join(TEXD, "svd_%s.png" % p))
    im.colorspace_settings.name = cs
    im.pack()
    imgs[p] = im
final = ds.make_final_material("M_svd", imgs)
old = list(me.materials)
me.materials.clear()
me.materials.append(final)
for p in me.polygons:
    p.material_index = 0
me.update()
for m in old:
    if m.users == 0:
        bpy.data.materials.remove(m)
for im in list(bpy.data.images):
    if im.users == 0:
        bpy.data.images.remove(im)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(MDIR, "svd_detailed.blend"), compress=True)
glb = os.path.join(MDIR, "svd_detailed.glb")
for o in bpy.context.scene.objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_yup=True, export_skins=True,
                          export_animations=False, export_apply=False, export_image_format="WEBP",
                          export_image_quality=82, export_tangents=False, export_materials="EXPORT")
me.calc_loop_triangles()
print("SVD RESULT tris=%d glb_bytes=%d" % (len(me.loop_triangles), os.path.getsize(glb)))
