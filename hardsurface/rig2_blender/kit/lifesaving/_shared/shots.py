# shots.py: close-up stills of the lifeboat station for looking at (not the kit's six-view gate, which is review.py).
#   blender -b --factory-startup -t 4 --python shots.py -- <out dir> <prefix> [--clay] [--spp 48] [--res 1600x900] [--only a,b] file.blend [file.blend ...]
# Loads every mesh object of the given .blend files into one scene (they share the station frame), overcast sky, a
# sun, Cycles on the GPU when there is one.  --clay overrides every material with matt grey.
import bpy, sys, os, math
from mathutils import Vector
A = sys.argv[sys.argv.index("--") + 1:]
out, prefix = os.path.abspath(A[0]), A[1]; files = [os.path.abspath(a) for a in A[2:] if a.endswith(".blend")]
clay = "--clay" in A; spp = int(A[A.index("--spp") + 1]) if "--spp" in A else 48
res = A[A.index("--res") + 1].split("x") if "--res" in A else ("1600", "900")
only = A[A.index("--only") + 1].split(",") if "--only" in A else None
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for f in files:
    with bpy.data.libraries.load(f, link=False) as (src, dst): dst.objects = [n for n in src.objects]
    for o in dst.objects:
        if o is not None and o.type == "MESH" and (o.name.startswith("hi_") == ("--hi" in A) or "grate" in o.name): sc.collection.objects.link(o)
        elif o is not None and o.type == "EMPTY": sc.collection.objects.link(o)      # decal projectors (unbaked previews need them)
        elif o is not None: bpy.data.objects.remove(o)
for im in bpy.data.images:                     # baked maps sit beside their .blend
    if im.source == "FILE" and not os.path.exists(bpy.path.abspath(im.filepath)):
        for f in files:
            p = os.path.join(os.path.dirname(f), os.path.basename(im.filepath.replace("\\", "/")))
            if os.path.exists(p): im.filepath = p; im.reload()
sc.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
    for d in prefs.devices: d.use = d.type == "OPTIX"
    sc.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
except Exception as e: print("no OptiX", e)
sc.cycles.samples = spp; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(res[0]), int(res[1]); sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 92
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexGradient"); tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); ramp = nt.nodes.new("ShaderNodeValToRGB")
mp.inputs["Rotation"].default_value = (0, math.radians(-90), 0); nt.links.new(tc.outputs["Generated"], mp.inputs[0]); nt.links.new(mp.outputs[0], sky.inputs[0]); nt.links.new(sky.outputs[0], ramp.inputs[0])
ramp.color_ramp.elements[0].position = 0.42; ramp.color_ramp.elements[0].color = (0.10, 0.12, 0.14, 1); ramp.color_ramp.elements[1].position = 0.62; ramp.color_ramp.elements[1].color = (0.62, 0.66, 0.72, 1)
nt.links.new(ramp.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.9
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.energy = 4.0; sun.data.angle = math.radians(12)
sun.rotation_euler = (Vector((0.55, 0.35, -0.75))).to_track_quat("-Z", "Y").to_euler()
if clay:
    m = bpy.data.materials.new("clay"); m.use_nodes = True; bs = m.node_tree.nodes["Principled BSDF"]; bs.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1); bs.inputs["Roughness"].default_value = 0.6
    for o in sc.objects:
        if o.type == "MESH":
            if any(s.material and s.material.blend_method != "OPAQUE" and "grate" in s.material.name for s in o.material_slots): continue
            for s in o.material_slots: s.material = m
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 500
# station frame: boat along Y (bow +Y) centred near x = 0.55; deck edge x = -2.25 (deck on -X), deck top z = 2.6
SH = {"outboard": ((11.5, 8.5, 5.4), (0.2, 0.0, 3.2), 35), "bow": ((5.2, 9.6, 3.4), (0.4, 2.2, 3.0), 40), "stern": ((4.6, -8.6, 2.2), (0.5, -2.6, 2.6), 40),
      "hatch": ((-2.6, 2.6, 3.6), (0.2, 0.2, 3.3), 30), "deck": ((-5.2, -5.4, 4.3), (0.0, 0.2, 3.9), 26), "below": ((6.0, 5.0, -1.2), (-0.6, 0.0, 2.8), 30),
      "hook": ((2.6, 5.2, 4.6), (0.5, 3.1, 3.7), 50), "winch": ((-0.4, -3.6, 5.2), (-1.7, 0.0, 5.3), 35), "top": ((5.0, 0.5, 9.5), (0.3, 0.0, 3.5), 40),
      "prop": ((2.6, -6.2, 0.9), (0.55, -3.3, 1.6), 55), "foot": ((1.2, -6.0, 1.6), (-2.2, -3.1, 2.3), 40), "tower": ((3.3, -5.4, 5.0), (0.55, -1.9, 4.1), 50)}
for k, (eye, at, lens) in SH.items():
    if only and k not in only: continue
    cam.location = eye; cam.data.lens = lens; cam.rotation_euler = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out, f"{prefix}_{k}.jpg"); bpy.ops.render.render(write_still=True)
