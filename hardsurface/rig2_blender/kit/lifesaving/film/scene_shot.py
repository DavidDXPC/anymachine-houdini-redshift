# scene_shot.py: the closing shot of the making-of film, the lifeboat station where it lives on the rig.
# Runs inside a built rig2 scene (read only: nothing is saved).  A slow drift past the first station.
#   blender -b <rig2_<set>_packed.blend> --python scene/farm/gpu.py --python scene_shot.py -- <out dir> [--f0 1 --f1 96] [--spp 128] [--res 1920x1080] [--frames a,b]
import bpy, sys, os
from mathutils import Vector
A = sys.argv[sys.argv.index("--") + 1:]
arg = lambda n, d=None: A[A.index(n) + 1] if n in A else d
OUT = os.path.abspath(A[0]); F0, F1 = int(arg("--f0", 1)), int(arg("--f1", 96)); N = 96; RES = arg("--res", "1920x1080").split("x")
sc = bpy.context.scene
boats = sorted((o for o in sc.objects if o.name.startswith("survival_craft")), key=lambda o: -o.matrix_world.translation.y)
print("BOATS", [(o.name, [round(v, 2) for v in o.matrix_world.translation]) for o in boats])
P = boats[0].matrix_world.translation.copy()                     # the station nearest the camera's side (old prop origin)
for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)   # markers switch cameras
cam = bpy.data.objects.new("cam_film", bpy.data.cameras.new("cam_film")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 6000; cam.data.lens = 35
sc.cycles.samples = int(arg("--spp", 128)); sc.render.resolution_x, sc.render.resolution_y = int(RES[0]), int(RES[1]); sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 95
E0, E1, AT = P + Vector((-14.5, 13.0, 4.0)), P + Vector((-11.5, 6.5, 6.2)), P + Vector((-0.6, 0.0, 3.2))
smooth = lambda u: u * u * (3 - 2 * u)
os.makedirs(OUT, exist_ok=True)
for f in ([int(x) for x in arg("--frames").split(",")] if arg("--frames") else range(F0, F1 + 1)):
    u = smooth((f - 1) / (N - 1)); eye = E0.lerp(E1, u); cam.location = eye
    cam.rotation_euler = (AT - eye).to_track_quat("-Z", "Y").to_euler()
    sc.frame_set(100 + f); sc.camera = cam
    sc.render.filepath = os.path.join(OUT, "s_%04d.jpg" % f); bpy.ops.render.render(write_still=True); print("FRAME", f, flush=True)
