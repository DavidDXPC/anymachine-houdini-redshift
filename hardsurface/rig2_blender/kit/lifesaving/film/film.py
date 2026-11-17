# film.py: the making-of film of the lifeboat station.  Reference sheet -> the generated mesh -> the hand model
# going together piece by piece in clay -> its baked textures sweeping on -> the two side by side.
#   blender -b --factory-startup -t 4 --python film.py -- <out dir> --boat <survival_craft dir> --davit <lifeboat_davit dir>
#       --meshy <lifeboat.blend> --sheet <reference sheet .png> [--f0 1 --f1 588] [--step 1] [--spp 64] [--res 1920x1080]
# Needs <name>_parts.blend in each component folder (build.py -- --parts).  Frames are set from Python, one still per
# frame (no keyframes), so any frame range renders on its own: the farm runs ranges side by side (make_spec.mjs).
import bpy, sys, os, math
from mathutils import Vector, Matrix
A = sys.argv[sys.argv.index("--") + 1:]
arg = lambda n, d=None: A[A.index(n) + 1] if n in A else d
OUT = os.path.abspath(A[0]); BOAT = os.path.abspath(arg("--boat")); DAVIT = os.path.abspath(arg("--davit")); MESHY = os.path.abspath(arg("--meshy")); SHEET = os.path.abspath(arg("--sheet"))
F0, F1, STEP = int(arg("--f0", 1)), int(arg("--f1", 588)), int(arg("--step", 1)); SPP = int(arg("--spp", 64)); RES = arg("--res", "1920x1080").split("x")
# the cut, in frames at 24 a second: A sheet, B generated mesh, C assembly, D textures, E side by side
A1, B1, C1, D1, E1 = 60, 156, 396, 468, 588
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; col = sc.collection


def load(f, keep):
    with bpy.data.libraries.load(f, link=False) as (src, dst): dst.objects = [n for n in src.objects]
    r = []
    for o in dst.objects:
        if o is not None and o.type == "MESH" and keep(o): col.objects.link(o); r.append(o)
        elif o is not None: bpy.data.objects.remove(o)
    for im in bpy.data.images:                     # baked maps sit beside their .blend
        if im.source == "FILE" and not os.path.exists(bpy.path.abspath(im.filepath)):
            p = os.path.join(os.path.dirname(f), os.path.basename(im.filepath.replace("\\", "/")))
            if os.path.exists(p): im.filepath = p; im.reload()
    return r


def emit(name, c, s=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*c, 1); e.inputs[1].default_value = s
    o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(e.outputs[0], o.inputs[0]); return m


# ---------------------------------------------------------------- the three models
clay = bpy.data.materials.new("clay"); clay.use_nodes = True; bs = clay.node_tree.nodes["Principled BSDF"]
bs.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1); bs.inputs["Roughness"].default_value = 0.6
parts = []                                                  # (object, rest position, start frame)
for d, name, t0, span in ((DAVIT, "lifeboat_davit", 0, 150), (BOAT, "survival_craft", 62, 158)):
    ps = sorted(load(os.path.join(d, name + "_parts.blend"), lambda o: "part" in o), key=lambda o: o["part"])
    for i, o in enumerate(ps):
        me = o.data; c = sum((Vector(v) for v in o.bound_box), Vector()) / 8; me.transform(Matrix.Translation(-c)); o.location = c
        for p in me.polygons: p.use_smooth = True
        me.set_sharp_from_angle(angle=math.radians(52)); me.materials.clear(); me.materials.append(clay)
        parts.append((o, c.copy(), B1 + 1 + t0 + span * i / len(ps)))
final = load(os.path.join(BOAT, "survival_craft.blend"), lambda o: not o.name.startswith("hi_")) + \
        load(os.path.join(DAVIT, "lifeboat_davit.blend"), lambda o: not o.name.startswith("hi_"))
sweeps = []                                                 # the value node of each baked material: where the textures have got to
for o in final:
    for s in o.material_slots:
        m = s.material
        if m is None or m.get("swept") or "grate" in m.name: continue
        m["swept"] = 1; nt = m.node_tree; out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
        src = out.inputs[0].links[0].from_socket
        N = nt.nodes.new; L = nt.links.new
        geo = N("ShaderNodeNewGeometry"); sep = N("ShaderNodeSeparateXYZ"); L(geo.outputs["Position"], sep.inputs[0])
        thr = N("ShaderNodeValue"); sub = N("ShaderNodeMath"); sub.operation = "SUBTRACT"; L(thr.outputs[0], sub.inputs[0]); L(sep.outputs["Y"], sub.inputs[1])
        fac = N("ShaderNodeMapRange"); fac.inputs[1].default_value = 0.0; fac.inputs[2].default_value = 0.05; L(sub.outputs[0], fac.inputs[0])      # 1 behind the front
        ab = N("ShaderNodeMath"); ab.operation = "ABSOLUTE"; L(sub.outputs[0], ab.inputs[0])
        band = N("ShaderNodeMapRange"); band.inputs[1].default_value = 0.0; band.inputs[2].default_value = 0.07; band.inputs[3].default_value = 6.0; band.inputs[4].default_value = 0.0; L(ab.outputs[0], band.inputs[0])
        cb = N("ShaderNodeBsdfPrincipled"); cb.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1); cb.inputs["Roughness"].default_value = 0.6
        mix = N("ShaderNodeMixShader"); L(fac.outputs[0], mix.inputs[0]); L(cb.outputs[0], mix.inputs[1]); L(src, mix.inputs[2])
        em = N("ShaderNodeEmission"); em.inputs[0].default_value = (1.0, 0.55, 0.18, 1); L(band.outputs[0], em.inputs[1])
        add = N("ShaderNodeAddShader"); L(mix.outputs[0], add.inputs[0]); L(em.outputs[0], add.inputs[1]); L(add.outputs[0], out.inputs[0])
        sweeps.append(thr)
grates = [o for o in final if "grate" in o.name]
new_root = bpy.data.objects.new("new_root", None); col.objects.link(new_root)
for o in final: o.parent = new_root
old_root = bpy.data.objects.new("old_root", None); col.objects.link(old_root); old_root.location = (0, 0, 3.0)
old = load(MESHY, lambda o: True)
for o in old: o.parent = old_root; o.matrix_parent_inverse = Matrix.Translation((0, 0, -3.0))

# ---------------------------------------------------------------- the sheet, the labels, light, camera
SP = Vector((0, 0, -300))
bpy.ops.mesh.primitive_plane_add(size=1, location=SP); sheet = bpy.context.object; sheet.scale = (16, 9, 1)
sm = bpy.data.materials.new("sheet"); sm.use_nodes = True; nt = sm.node_tree; nt.nodes.clear()
ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(SHEET); se = nt.nodes.new("ShaderNodeEmission"); so = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(ti.outputs[0], se.inputs[0]); nt.links.new(se.outputs[0], so.inputs[0]); sheet.data.materials.append(sm)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); col.objects.link(cam); sc.camera = cam; cam.data.clip_end = 800
WH, BK = emit("label", (1, 1, 1), 1.0), emit("plate", (0.012, 0.014, 0.016), 1.0)


def label(s, parent=None):
    cu = bpy.data.curves.new("t", "FONT"); cu.body = s; cu.align_x = "LEFT"; cu.align_y = "BOTTOM"; cu.space_character = 1.08
    t = bpy.data.objects.new("label", cu); col.objects.link(t); cu.materials.append(WH); bpy.context.view_layer.update()
    w, h = t.dimensions.x, t.dimensions.y
    bpy.ops.mesh.primitive_plane_add(size=1); p = bpy.context.object; p.data.materials.append(BK)
    p.parent = t; p.location = (w / 2, h / 2 - 0.03, -0.01); p.scale = (w + 0.7, h + 0.5, 1)
    if parent: t.parent = parent
    return t, p


LAB = {k: label(s, cam) for k, s in (("A", "1   the reference image"), ("B", "2   generated mesh (Meshy)"), ("C", "3   modeled via an agent, piece by piece"), ("D", "baked to one texture set each"))}
E_old = label("generated (Meshy)"); E_new = label("modeled via an agent")
for (t, p), y in ((E_old, -4.7), (E_new, 4.7)):
    t.rotation_euler = (math.radians(90), 0, math.radians(90)); t.scale = (0.62,) * 3; t.location = (2.5, y - t.dimensions.x * 0.31, -1.2)
sc.render.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
    for d in prefs.devices: d.use = d.type == "OPTIX"
    sc.cycles.device = "GPU" if any(d.use for d in prefs.devices) else "CPU"
except Exception as e: print("no OptiX", e)
sc.cycles.samples = SPP; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(RES[0]), int(RES[1]); sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 95
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
sky = nt.nodes.new("ShaderNodeTexGradient"); tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); ramp = nt.nodes.new("ShaderNodeValToRGB")
mp.inputs["Rotation"].default_value = (0, math.radians(-90), 0); nt.links.new(tc.outputs["Generated"], mp.inputs[0]); nt.links.new(mp.outputs[0], sky.inputs[0]); nt.links.new(sky.outputs[0], ramp.inputs[0])
ramp.color_ramp.elements[0].position = 0.42; ramp.color_ramp.elements[0].color = (0.10, 0.12, 0.14, 1); ramp.color_ramp.elements[1].position = 0.62; ramp.color_ramp.elements[1].color = (0.62, 0.66, 0.72, 1)
nt.links.new(ramp.outputs[0], nt.nodes["Background"].inputs[0]); nt.nodes["Background"].inputs[1].default_value = 1.9
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); col.objects.link(sun); sun.data.energy = 4.0; sun.data.angle = math.radians(12)
sun.rotation_euler = (Vector((0.55, 0.35, -0.75))).to_track_quat("-Z", "Y").to_euler()

ease = lambda t: 1 - (1 - max(0.0, min(1.0, t))) ** 3
smooth = lambda t: (lambda u: u * u * (3 - 2 * u))(max(0.0, min(1.0, t)))
show = lambda o, v: setattr(o, "hide_render", not v)


def look(eye, at, lens):
    cam.location = eye; cam.data.lens = lens; cam.rotation_euler = (Vector(at) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()


def frame(f):
    shot = "A" if f <= A1 else "B" if f <= B1 else "C" if f <= C1 else "D" if f <= D1 else "E"
    sc.view_settings.view_transform = "Standard" if shot == "A" else "AgX"; sc.view_settings.look = "None" if shot == "A" else "AgX - Medium High Contrast"
    show(sheet, shot == "A")
    for o in old: show(o, shot in "BE" or (shot == "C" and f < B1 + 14))
    for o, c, t0 in parts:
        t = (f - t0) / 14.0; show(o, shot == "C" and t > 0)
        e = ease(t); o.scale = (max(e, 0.001),) * 3; o.location = c + Vector((0.25, 0, 0.7)) * (1 - e)
    for o in final: show(o, shot in "DE")
    for k, (t, p) in LAB.items(): show(t, k == shot); show(p, k == shot)
    for t, p in (E_old, E_new): show(t, shot == "E"); show(p, shot == "E")
    old_root.location = (0, 0, 3.0); old_root.scale = (1, 1, 1); new_root.location = (0, 0, 0)
    for v in sweeps: v.outputs[0].default_value = 100.0
    if shot == "A":
        u = smooth((f - 1) / (A1 - 1)); look(SP + Vector((0, 0, 22.0 - 1.6 * u)), SP, 50)
        cam.rotation_euler = (0, 0, 0)
    elif shot == "E":
        u = (f - D1 - 1) / (E1 - D1 - 1); old_root.location = (0, -4.7, 3.0); new_root.location = (0, 4.7, 0)
        look((27.5, -1.8 + 3.6 * u, 5.2), (0, 0, 2.5), 50)
    else:
        u = (f - A1 - 1) / (D1 - A1 - 1); az = math.radians(58 - 104 * u); at = Vector((0.0, 0.0, 3.3))
        look(at + Vector((13.5 * math.cos(az), 13.5 * math.sin(az), 2.3)), at, 35)
        if shot == "C": s = 1 - ease((f - B1 - 1) / 12.0); old_root.scale = (max(s, 0.001),) * 3
        if shot == "D":
            for v in sweeps: v.outputs[0].default_value = -4.4 + 9.2 * smooth((f - C1 - 6) / 52.0)
    hw = 18.0 / cam.data.lens; hh = hw * int(RES[1]) / int(RES[0])
    for k, (t, p) in LAB.items(): t.location = (-0.9 * hw, -0.84 * hh, -1.0); t.scale = (0.045 * hw,) * 3


os.makedirs(OUT, exist_ok=True)
for f in ([int(x) for x in arg("--frames").split(",")] if arg("--frames") else range(F0, F1 + 1, STEP)):
    frame(f); sc.frame_set(f); sc.render.filepath = os.path.join(OUT, "f_%04d.jpg" % f); bpy.ops.render.render(write_still=True); print("FRAME", f)
