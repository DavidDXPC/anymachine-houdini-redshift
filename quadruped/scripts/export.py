"""Export the quadruped to GLB: rigid parts on bones + linear actions trot, trot_forward, idle, sit, stand.

blender -b --factory-startup --python export.py -- --blend out/quadruped.blend --out out/quadruped.glb
Actions are already baked to per-frame LINEAR FK keys (no drivers, no IK needed by consumers). The IK constraints
and the `ik` driver are .blend-only and are muted for the export. The joint spec (`anymachine`) and the gait
parameters ride along as glTF extras on the rig node.
"""
import bpy, sys, os

argv = sys.argv[sys.argv.index("--") + 1:]
blend, out = os.path.abspath(argv[argv.index("--blend") + 1]), os.path.abspath(argv[argv.index("--out") + 1])
bpy.ops.wm.open_mainfile(filepath=blend)
arm = bpy.data.objects["quadruped_rig"]
for pb in arm.pose.bones:
    for c in pb.constraints:
        if c.type == "IK":
            c.driver_remove("influence")
            c.mute = True
ad = arm.animation_data
ad.action = None
for t in ad.nla_tracks:
    t.mute = False
for img in bpy.data.images:  # textures <= 2K
    if img.size[0] > 2048:
        f_ = 2048 / max(img.size)
        img.scale(int(img.size[0] * f_), int(img.size[1] * f_))
        img.pack()
for o in bpy.data.objects:
    o.select_set(o.name == "quadruped_rig" or (o.type == "MESH" and "group" in o.keys()))
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
                          export_animations=True, export_animation_mode="NLA_TRACKS", export_extras=True,
                          export_force_sampling=True, export_frame_step=1)
print("EXPORTED", out, os.path.getsize(out) // 1024, "KB", flush=True)
