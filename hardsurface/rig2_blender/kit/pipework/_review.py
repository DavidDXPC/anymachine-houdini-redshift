# _review.py: the gate.  Opens <dir>/<id>.blend (written by build.py), renders the model from the six directions of
# its turnaround sheet (front, left, back / right, top, three-quarter), flat light, and writes
#   review.jpg         sheet (left) beside render (right)
#   review_render.jpg  the render grid alone, for a closer look
#   review_close.jpg   (if _review.json has "close") the close-up sheet beside the model shot at the same subjects
#   blender -b --factory-startup -t 4 --python _review.py -- <dir> [--shots shots.json out.jpg]
# Before the bake the materials are flat palette colours; after it, the baked set.
import bpy, sys, os, math, json
import numpy as np
from mathutils import Vector, Euler
a = sys.argv[sys.argv.index("--") + 1:]
D = os.path.abspath(a[0]); cfg = json.load(open(os.path.join(D, "_review.json"))); kid = cfg["id"]
HERE = os.path.dirname(os.path.abspath(__file__)); SH = os.path.join(HERE, "..", "sheets")
CW, CH = 816, 684
bpy.ops.wm.open_mainfile(filepath=os.path.join(D, kid + ".blend"))
sc = bpy.context.scene
for o in list(sc.objects):
    if o.type != "MESH" or o.name.startswith("hi_") or o.name.startswith("_bake"): bpy.data.objects.remove(o)
objs = [o for o in sc.objects if o.type == "MESH"]
lay = cfg.get("layout"); tints = cfg.get("tints", {}); tintable = set(cfg.get("tintable", []))
if lay:
    for o in list(objs):
        if o.name in lay: o.location = lay[o.name][:3]
        else: bpy.data.objects.remove(o); objs.remove(o)
for o in objs: o.color = tuple(tints.get(o.name, (1, 1, 1))) + (1,)


def tint_nodes(nt):
    oi = nt.nodes.new("ShaderNodeObjectInfo"); at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "_TINT"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (1, 1, 1, 1)
    nt.links.new(at.outputs["Fac"], mx.inputs[0]); nt.links.new(oi.outputs["Color"], mx.inputs[7])
    return mx.outputs[2]


for m in bpy.data.materials:
    if not m.use_nodes or not m.users: continue
    nt = m.node_tree
    sets = cfg.get("sets") or [kid]          # texture sets: one baked material each
    if cfg.get("baked") and m.name in sets:
        if tints:
            bs = nt.nodes["Principled BSDF"]; src = bs.inputs["Base Color"].links[0].from_socket
            mu = nt.nodes.new("ShaderNodeMix"); mu.data_type = "RGBA"; mu.blend_type = "MULTIPLY"; mu.inputs[0].default_value = 1.0
            nt.links.new(src, mu.inputs[6]); nt.links.new(tint_nodes(nt), mu.inputs[7]); nt.links.new(mu.outputs[2], bs.inputs["Base Color"])
        continue
    pre = next((s for s in sets if m.name.startswith(s + "_")), None)
    if pre is None: continue
    suf = m.name[len(pre) + 1:]
    if suf not in cfg["palette"]: continue
    nt.nodes.clear(); bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bs.outputs[0], out.inputs[0]); col = tuple(cfg["palette"][suf]) + (1,)
    bs.inputs["Base Color"].default_value = col; bs.inputs["Roughness"].default_value = 0.6
    if suf.split("_")[0] in ("steel", "galv"): bs.inputs["Metallic"].default_value = 0.6; bs.inputs["Roughness"].default_value = 0.4
    if suf in tintable and tints:
        oi = nt.nodes.new("ShaderNodeObjectInfo"); mu = nt.nodes.new("ShaderNodeMix"); mu.data_type = "RGBA"; mu.blend_type = "MULTIPLY"
        mu.inputs[0].default_value = 1.0; mu.inputs[6].default_value = col; nt.links.new(oi.outputs["Color"], mu.inputs[7])
        nt.links.new(mu.outputs[2], bs.inputs["Base Color"])

bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
ctr = (mn + mx) / 2; diag = (mx - mn).length
corners = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x, sc.render.resolution_y = CW, CH; sc.render.resolution_percentage = 100
sc.render.threads_mode = "FIXED"; sc.render.threads = 4
try:
    sc.eevee.taa_render_samples = 32; sc.eevee.use_raytracing = False
except Exception as e: print(e)
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.72, 0.72, 0.73, 1); bg.inputs[1].default_value = 0.75
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.data.energy = 0.9; sun.data.angle = math.radians(40)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.clip_start = 0.05; cam.data.clip_end = max(200, diag * 8)
sc.render.image_settings.file_format = "PNG"


def shoot(i):
    p = os.path.join(D, f"_rv_{i}.png"); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(p); px = np.array(im.pixels[:], np.float32).reshape(CH, CW, 4); bpy.data.images.remove(im); os.remove(p)
    return px


def light(dirv, top=False):
    ld = (dirv + Vector((0, 0, 0.8)) + dirv.cross(Vector((0, 0, 1))) * 0.5) if not top else Vector((0.3, -0.4, 1))
    sun.rotation_euler = ld.to_track_quat("Z", "Y").to_euler()


def turn(views, tq_dist=2.1):
    cells = []
    for i, (az, el) in enumerate(views):
        azr, elr = math.radians(az), math.radians(el)
        dirv = Vector((math.sin(azr) * math.cos(elr), -math.cos(azr) * math.cos(elr), math.sin(elr)))
        top = el > 89
        cam.rotation_euler = Euler((0, 0, 0)) if top else (-dirv).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update(); R = cam.rotation_euler.to_matrix(); rx, ry = R.col[0], R.col[1]
        if i < 5:
            us = [(c - ctr).dot(rx) for c in corners]; vs = [(c - ctr).dot(ry) for c in corners]
            cam.data.type = "ORTHO"; cam.data.ortho_scale = max(max(us) - min(us), (max(vs) - min(vs)) * CW / CH) * 1.22
            cam.location = ctr + rx * (max(us) + min(us)) / 2 + ry * (max(vs) + min(vs)) / 2 + dirv * (diag * 2)
        else:
            cam.data.type = "PERSP"; cam.data.lens = 60; cam.location = ctr + dirv * (diag * tq_dist)
        light(dirv, top); cells.append(shoot(i))
    return np.concatenate([np.concatenate(cells[3:6], 1), np.concatenate(cells[0:3], 1)], 0)      # rows run bottom-up


def shots(lst):
    cells = []
    for i, s in enumerate(lst):
        eye, tg = Vector(s["eye"]), Vector(s["at"]); dirv = (eye - tg).normalized()
        cam.data.type = "PERSP"; cam.data.lens = s.get("lens", 50); cam.location = eye
        cam.rotation_euler = (-dirv).to_track_quat("-Z", "Y").to_euler(); light(dirv); cells.append(shoot(i))
    while len(cells) % 3: cells.append(np.ones((CH, CW, 4), np.float32) * 0.7)
    rows = [np.concatenate(cells[k:k + 3], 1) for k in range(0, len(cells), 3)]
    return np.concatenate(rows[::-1], 0)


def save(px, name, q=88):
    px = px.copy(); px[..., 3] = 1
    o = bpy.data.images.new(name, px.shape[1], px.shape[0], alpha=False); o.pixels.foreach_set(px.ravel())
    sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = q
    o.save_render(os.path.join(D, name), scene=sc); sc.render.image_settings.file_format = "PNG"; print("wrote", name)


def beside(sheet, grid):
    H = grid.shape[0]
    sh = bpy.data.images.load(sheet); sw, shh = sh.size; sp = np.array(sh.pixels[:], np.float32).reshape(shh, sw, sh.channels)
    if sh.channels == 3: sp = np.concatenate([sp, np.ones((shh, sw, 1), np.float32)], 2)
    tw = int(round(H * sw / shh)); yi = (np.arange(H) * shh / H).astype(int); xi = (np.arange(tw) * sw / tw).astype(int)
    bar = np.ones((H, 12, 4), np.float32) * np.array([0.9, 0.2, 0.1, 1], np.float32)
    return np.concatenate([sp[yi][:, xi], bar, grid], 1)


if "--shots" in a:
    i = a.index("--shots"); save(shots(json.load(open(a[i + 1]))), a[i + 2])
else:
    views = cfg.get("views") or [(0, 0), (-90, 0), (180, 0), (90, 0), (0, 90), (35, 24)]
    g = turn(views, cfg.get("tq_dist", 2.1)); save(g, "review_render.jpg")
    save(beside(os.path.join(SH, cfg.get("sheet", kid) + "_turn.png"), g), "review.jpg")
    if cfg.get("close"):
        g = shots(cfg["close"]["shots"]); save(g, "review_close_render.jpg")
        save(beside(os.path.join(SH, cfg["close"]["sheet"] + ".png"), g), "review_close.jpg")
