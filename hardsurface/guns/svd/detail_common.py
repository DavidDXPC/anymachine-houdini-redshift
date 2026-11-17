"""Shared helpers for the detail_* scripts (import, studio, cameras, renders)."""
import math
import os

import bpy
from mathutils import Matrix, Vector

BLENDER_DIR = os.path.dirname(bpy.app.binary_path)
HDRI_DIR = os.path.join(BLENDER_DIR, "%d.%d" % bpy.app.version[:2], "datafiles", "studiolights", "world")

# Unreal constants (base grey, metallic, roughness) keyed by lowercase substring, first hit wins.
FLAT = [
    ("translucent", (0.080, 0.0, 0.35)),
    ("follower", (0.077, 0.0, 0.5)),
    ("polymer_mag", (0.021, 0.7, 0.4)),
    ("polymer", (0.046, 0.6, 0.5)),
    ("milled", (0.157, 0.9, 0.3)),
    ("finish", (0.047, 0.8, 0.3)),
]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path, flat=True):
    """Load fbx / glb / blend. Returns list of new objects."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=path)
        return list(bpy.data.objects)
    before = set(bpy.data.objects)
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path, use_anim=False)
        if flat:
            flat_materials()
    else:
        bpy.ops.import_scene.gltf(filepath=path)
        for o in list(bpy.data.objects):          # importer's bone-shape helper meshes
            if o not in before and o.type == "MESH" and o.name.startswith("Icosphere"):
                bpy.data.objects.remove(o, do_unlink=True)
    return [o for o in bpy.data.objects if o not in before]


def flat_materials(table=None):
    for mat in bpy.data.materials:
        n = mat.name.lower()
        val = (0.05, 0.8, 0.3)
        for key, v in (table or FLAT):
            if key in n:
                val = v
                break
        mat.use_nodes = True
        b = mat.node_tree.nodes.get("Principled BSDF")
        if not b:
            continue
        for inp in b.inputs:
            for link in list(inp.links):
                mat.node_tree.links.remove(link)
        g = val[0]
        b.inputs["Base Color"].default_value = (g, g, g, 1) if not isinstance(g, tuple) else (*g, 1)
        b.inputs["Metallic"].default_value = val[1]
        b.inputs["Roughness"].default_value = val[2]


def mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.get("studio")]


def world_bounds(objs=None):
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in (objs or mesh_objects()):
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        for v in me.vertices:
            c = mw @ v.co
            for i in range(3):
                mn[i] = min(mn[i], c[i])
                mx[i] = max(mx[i], c[i])
        ev.to_mesh_clear()
    return mn, mx


def use_cycles(samples=64):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                if any(d.type == kind for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = d.type == kind
                    sc.cycles.device = "GPU"
                    break
            except Exception:
                continue
    except Exception as e:  # noqa
        print("cycles gpu setup failed", e)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass


def studio(hdri="studio.exr", strength=1.0, bg=0.16, floor_z=None, rot=0.0):
    """HDRI lighting with a flat grey camera background, key/rim lights, optional floor."""
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(HDRI_DIR, hdri))
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, rot)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    b1 = nt.nodes.new("ShaderNodeBackground")
    b1.inputs[1].default_value = strength
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = 0.25
    nt.links.new(env.outputs[0], hs.inputs["Color"])
    nt.links.new(hs.outputs[0], b1.inputs[0])
    b2 = nt.nodes.new("ShaderNodeBackground")
    b2.inputs[0].default_value = (bg, bg, bg * 1.05, 1)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(b1.outputs[0], mix.inputs[1])
    nt.links.new(b2.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    sc.world = w
    mn, mx = world_bounds()
    c = (mn + mx) / 2
    size = (mx - mn).length

    def area(name, loc, energy, sz, col=(1, 1, 1)):
        l = bpy.data.lights.new(name, "AREA")
        l.energy = energy
        l.size = sz
        l.color = col
        o = bpy.data.objects.new(name, l)
        o.location = loc
        o.rotation_euler = (c - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        o["studio"] = 1
        sc.collection.objects.link(o)
        return o

    e = size * size * 9
    area("Key", c + Vector((size * 0.9, -size * 0.5, size * 1.0)), e * 1.6, size * 0.8, (1.0, 0.97, 0.93))
    area("Fill", c + Vector((-size * 1.0, -size * 0.3, size * 0.4)), e * 0.6, size * 1.2, (0.9, 0.95, 1.0))
    area("Rim", c + Vector((-size * 0.2, size * 0.9, size * 0.9)), e * 1.2, size * 0.5)
    if floor_z is not None:
        bpy.ops.mesh.primitive_plane_add(size=size * 40, location=(c.x, c.y, floor_z))
        fl = bpy.context.object
        fl["studio"] = 1
        m = bpy.data.materials.new("Floor")
        m.use_nodes = True
        bs = m.node_tree.nodes["Principled BSDF"]
        bs.inputs["Base Color"].default_value = (bg * 1.3, bg * 1.3, bg * 1.35, 1)
        bs.inputs["Roughness"].default_value = 0.9
        fl.data.materials.append(m)
    return c, size


def add_camera(name, loc, target, ortho=None, lens=50, up="Y"):
    cd = bpy.data.cameras.new(name)
    cd.clip_start = 0.005
    cd.clip_end = 100
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", up).to_euler()
    o["studio"] = 1
    bpy.context.scene.collection.objects.link(o)
    return o


def standard_cameras(aspect=16 / 9):
    """side_r / side_l / threeq / top / fp cameras for a gun whose muzzle points to -Y, up +Z."""
    mn, mx = world_bounds()
    c = (mn + mx) / 2
    L = mx.y - mn.y
    H = mx.z - mn.z
    span = max(L * 1.08, H * 1.15 * aspect)
    cams = {}
    cams["side_l"] = add_camera("side_l", (c.x + 3, c.y, c.z), c, ortho=span)   # gun's left, muzzle to screen-left
    cams["side_r"] = add_camera("side_r", (c.x - 3, c.y, c.z), c, ortho=span)   # gun's right
    top = add_camera("top", (c.x, c.y, c.z + 3), c, ortho=span)
    top.rotation_euler = (0, 0, math.radians(90))                              # muzzle to screen-left
    cams["top"] = top
    d = L * 1.25 if L > 0.5 else max(L, H * 1.3) * 2.6
    cams["threeq"] = add_camera("threeq", (c.x + d * 0.62, mn.y - d * 0.42 + L * 0.5, c.z + d * 0.33), c, lens=70)
    cams["threeq_r"] = add_camera("threeq_r", (c.x - d * 0.62, mn.y - d * 0.42 + L * 0.5, c.z + d * 0.33), c, lens=70)
    # shooter's eye: behind the rear, up-left of the bore, looking down range
    eye = Vector((c.x + 0.07, c.y + L * 0.36 + max(0.0, 0.3 - L), mx.z + 0.05))
    tgt = eye + Vector((-0.03, -1.0, -0.06))
    cams["fp"] = add_camera("fp", eye, tgt, lens=22)
    cams["close_top"] = add_camera("close_top", (c.x + 0.13, c.y + L * 0.27, mx.z + 0.11),
                                   (c.x, c.y - L * 0.03, mx.z - 0.03), lens=50)
    cams["close_grip"] = add_camera("close_grip", (c.x - 0.30, c.y + L * 0.02, c.z + 0.02),
                                    (c.x, c.y + L * 0.14, c.z + H * 0.1), lens=60)
    return cams


def render_still(cam, path, res=(1600, 900)):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def turntable(frames_dir, n=96, res=(1280, 720), elev=18, dist_k=1.35, lens=60):
    """Rotate every root object about the vertical axis through the bounds centre."""
    sc = bpy.context.scene
    mn, mx = world_bounds()
    c = (mn + mx) / 2
    size = max(mx.y - mn.y, mx.x - mn.x, (mx.z - mn.z) * 1.6)
    piv = bpy.data.objects.new("TT", None)
    piv.location = c
    piv["studio"] = 1
    sc.collection.objects.link(piv)
    bpy.context.view_layer.update()
    for o in list(sc.objects):
        if o.parent is None and not o.get("studio"):
            mw = o.matrix_world.copy()
            o.parent = piv
            o.matrix_world = mw
    d = size * dist_k * (lens / 36.0) * 0.62
    el = math.radians(elev)
    cam = add_camera("ttcam", c + Vector((d * math.cos(el), 0, d * math.sin(el))), c, lens=lens)
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"
    os.makedirs(frames_dir, exist_ok=True)
    for i in range(n):
        piv.rotation_euler = (0, 0, 2 * math.pi * i / n)
        sc.render.filepath = os.path.join(frames_dir, "f_%04d.png" % i)
        bpy.ops.render.render(write_still=True)
