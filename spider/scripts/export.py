"""Export the rigged spider to GLB: plain FK actions `walk`, `idle`, `crouch` (+ joint spec in the rig's extras).

blender -b --factory-startup --python export.py -- --blend out/spider.blend --out out/spider.glb
Constraints and drivers are .blend conveniences (limits, IK posing); the actions are already baked, so they are removed
before export and every channel is sampled as plain keys.
"""
import bpy, sys, os

argv = sys.argv[sys.argv.index("--") + 1:]
blend, out = os.path.abspath(argv[argv.index("--blend") + 1]), os.path.abspath(argv[argv.index("--out") + 1])
bpy.ops.wm.open_mainfile(filepath=blend)
arm = bpy.data.objects["spider_rig"]
for pb in arm.pose.bones:
    for c in list(pb.constraints):
        pb.constraints.remove(c)
    pb.location = (0, 0, 0)
    pb.rotation_euler = (0, 0, 0)
ad = arm.animation_data
for d in list(ad.drivers):
    ad.drivers.remove(d)
ad.action = None
for t in list(ad.nla_tracks):
    if t.name in ("walk", "idle", "crouch"):
        t.mute = False
    else:
        ad.nla_tracks.remove(t)
# textures <= 2K
for img in bpy.data.images:
    if img.size[0] > 2048 or img.size[1] > 2048:
        f_ = 2048 / max(img.size)
        img.scale(int(img.size[0] * f_), int(img.size[1] * f_))
        img.pack()
keep = {"spider_rig", "chassis", "shell"} | {o.name for o in bpy.data.objects if o.name.split("_")[0] in ("coxa", "femur", "tibia")}
for o in bpy.data.objects:
    o.select_set(o.name in keep)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
                          export_animations=True, export_animation_mode="NLA_TRACKS", export_extras=True,
                          export_force_sampling=True, export_def_bones=False, export_optimize_animation_size=False)
print("EXPORTED", out, os.path.getsize(out) // 1024, "KB", flush=True)
