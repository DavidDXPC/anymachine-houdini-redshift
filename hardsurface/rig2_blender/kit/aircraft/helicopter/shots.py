# shots.py: review stills of a helicopter .blend, clay or textured.
#   blender -b <file.blend> --python shots.py -- <out_dir> <prefix> [clay|tex] [wb|eevee|cycles] [hi] [view names ...]
# clay: one grey material (Workbench with cavity shading locally, or Cycles).  tex: the file's own materials under an
# overcast sky.  hi: show the bake source objects (hi_*: every part and bake-only detail) instead of the game meshes.
# render.py calls run() for the farm set (Cycles on the worker's GPU).
import bpy, sys, os, math
from mathutils import Vector
VIEWS = {  # name: (eye, look-at, lens mm, ortho scale or None)
    "side_left": ((-1.2, 22, 2.3), (-1.2, 0, 2.1), 50, None), "side_right": ((-1.2, -22, 2.3), (-1.2, 0, 2.1), 50, None),
    "front": ((21, 0, 2.3), (0, 0, 2.1), 50, None), "rear": ((-23, 0, 2.6), (0, 0, 2.1), 50, None),
    "top": ((-1.2, 0, 30), (-1.2, 0, 0), 50, 14.6),
    "q_front_left": ((11.5, 9.5, 5.2), (-0.8, 0, 1.9), 50, None), "q_rear_right": ((-13.5, -9.0, 5.6), (-1.2, 0, 2.0), 50, None),
    "eye_front_left": ((7.2, 4.6, 1.65), (0.6, 0, 1.75), 28, None), "eye_side": ((1.2, 6.5, 1.65), (0.8, 0, 1.6), 28, None),
    "eye_rear_right": ((-8.2, -4.2, 1.65), (-2.5, 0, 2.2), 28, None), "eye_cabin": ((0.6, 3.0, 1.65), (0.5, 0, 1.45), 30, None),
    "c_rotor": ((2.3, 1.9, 4.5), (0, 0, 3.55), 55, None), "c_tail": ((-7.6, -3.4, 3.6), (-7.0, 0, 3.2), 55, None),
    "c_gear": ((-0.2, 3.9, 0.7), (-0.75, 1.4, 0.5), 50, None), "c_nose": ((5.6, 2.2, 1.3), (3.3, 0, 0.9), 50, None),
    "c_cowl": ((2.6, 3.4, 4.0), (0.2, 0.3, 2.8), 50, None), "c_cockpit": ((4.4, 1.5, 1.75), (2.6, 0.1, 1.45), 40, None),
    "c_door": ((0.8, 4.2, 1.6), (0.6, 1.0, 1.4), 50, None), "c_exhaust": ((-4.2, 2.2, 4.2), (-1.9, 0.2, 2.9), 55, None),
    "c_secured": ((2.4, 5.6, 1.1), (0.4, 2.2, 0.5), 40, None),
}


def run(out, pre, look="clay", engine="wb", hi=False, want=(), res=(1600, 900), spp=96):
    sc = bpy.context.scene
    for o in sc.objects: o.hide_render = o.type != "MESH" or (o.name.startswith("hi_") != hi and o.name != "heli_glass") or o.name.startswith("_")
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 90
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.62, 0.66, 0.70, 1)
    clay = None
    if look == "clay":
        for o in sc.objects:
            if o.name == "heli_glass": o.hide_render = True
    if engine == "wb":
        sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.62, 0.62, 0.62)
        sh.show_cavity = True; sh.cavity_type = "BOTH"; sh.cavity_ridge_factor = 1.0; sh.cavity_valley_factor = 1.6; sh.curvature_ridge_factor = 1.2; sh.curvature_valley_factor = 1.6
        sh.show_shadows = False; sh.show_object_outline = False; sc.display.render_aa = "8"
    else:
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.angle = math.radians(28)
        sun.rotation_euler = (math.radians(52), 0, math.radians(38)); sun.data.energy = 2.0; bg.inputs[1].default_value = 1.0
        if engine == "eevee":
            sc.render.engine = "BLENDER_EEVEE"
            try: sc.eevee.taa_render_samples = 32; sc.eevee.use_raytracing = True
            except Exception as e: print(e)
        else:
            sc.render.engine = "CYCLES"; sc.cycles.samples = spp; sc.cycles.use_denoising = True; sc.cycles.device = os.environ.get("RIG2_BAKE_DEVICE", "CPU")
            sc.cycles.use_adaptive_sampling = True
        if look == "clay":
            clay = bpy.data.materials.new("clay"); clay.use_nodes = True; b = clay.node_tree.nodes["Principled BSDF"]
            b.inputs["Base Color"].default_value = (0.42, 0.42, 0.42, 1); b.inputs["Roughness"].default_value = 0.6; bg.inputs[1].default_value = 0.55; sun.data.energy = 3.2
            bev = clay.node_tree.nodes.new("ShaderNodeBevel"); bev.inputs["Radius"].default_value = 0.004; clay.node_tree.links.new(bev.outputs[0], b.inputs["Normal"])
            sc.view_layers[0].material_override = clay
    # the deck: dark green, with the touchdown circle so the scale reads
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.002)); g = bpy.context.object; g.name = "_deck"; g.hide_render = False
    gm = bpy.data.materials.new("deck"); gm.use_nodes = True; nt = gm.node_tree; b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.85
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    def M(op, a, c):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = op
        for i, v in enumerate((a, c)):
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    dx = M("ADD", sep.outputs[0], 0.5); r = M("SQRT", M("ADD", M("MULTIPLY", dx, dx), M("MULTIPLY", sep.outputs[1], sep.outputs[1])), 0)
    ring = M("MULTIPLY", M("GREATER_THAN", r, 4.05), M("LESS_THAN", r, 4.6))
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; nt.links.new(ring, mix.inputs[0]); mix.inputs[6].default_value = (0.045, 0.13, 0.085, 1); mix.inputs[7].default_value = (0.62, 0.42, 0.03, 1)
    nt.links.new(mix.outputs[2], b.inputs["Base Color"]); g.data.materials.append(gm)
    gdiff = (0.4, 0.4, 0.4, 1)
    if look == "clay" and engine == "wb": gm.diffuse_color = gdiff
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 300
    os.makedirs(out, exist_ok=True)
    for name, (eye, la, lens, ortho) in VIEWS.items():
        if want and name not in want: continue
        eye, la = Vector(eye), Vector(la); cam.location = eye; cam.rotation_euler = (la - eye).to_track_quat("-Z", "Y").to_euler()
        cam.data.type = "ORTHO" if ortho else "PERSP"; cam.data.lens = lens
        if ortho: cam.data.ortho_scale = ortho
        sc.render.filepath = os.path.join(out, f"{pre}_{name}.jpg"); bpy.ops.render.render(write_still=True)
    print("shots done", pre, look, engine)


if __name__ == "__main__" and "--" in sys.argv and os.path.basename(sys.argv[sys.argv.index("--python") + 1] if "--python" in sys.argv else "") == "shots.py":
    a = sys.argv[sys.argv.index("--") + 1:]; flags = ("clay", "tex", "wb", "eevee", "cycles", "hi")
    run(os.path.abspath(a[0]), a[1], "tex" if "tex" in a else "clay", "eevee" if "eevee" in a else "cycles" if "cycles" in a else "wb", "hi" in a, [v for v in a[2:] if v not in flags])
