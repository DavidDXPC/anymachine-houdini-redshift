"""Shared helpers for the AnyMachine soft-goods (backpack) experiment. Blender 5.0, headless."""
import bpy, bmesh, math, json, os
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree

FPS = 24
PARAM_FRAMES = 24  # a control's glTF action runs 1 s: seek t = param (frame 1 + 24*param)


def load_gen(glb, rotz_deg, height):
    """Import a generated GLB, bake transforms, join, turn so the front faces -Y, scale to `height`, centre x/y, floor z=0."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.context.view_layer.update()
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)
    vl = bpy.context.view_layer
    for o in meshes:
        o.select_set(True)
    vl.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = vl.objects.active
    me = ob.data
    me.transform(Matrix.Rotation(math.radians(rotz_deg), 4, "Z"))
    lo, hi = bounds(ob)
    s = height / (hi.z - lo.z)
    me.transform(Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))
    me.update()
    ob.name = "gen"
    return ob


def bounds(ob, world=False):
    vs = [(ob.matrix_world @ v.co) if world else v.co for v in ob.data.vertices]
    return (Vector([min(v[i] for v in vs) for i in range(3)]), Vector([max(v[i] for v in vs) for i in range(3)]))


def fix_gen_material(ob, rough=0.85, metal=0.0):
    """Generator metallic/roughness maps are not trusted on fabric (exp 1): unlink them, set constants."""
    for m in ob.data.materials:
        if not m or not m.use_nodes:
            continue
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf:
            continue
        for name, val in (("Metallic", metal), ("Roughness", rough)):
            sock = bsdf.inputs[name]
            for l in list(sock.links):
                m.node_tree.links.remove(l)
            sock.default_value = val
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.35


def mat(name, rgb, rough=0.8, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*rgb, 1)
    return m


def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def tris_world(obs, dg=None):
    dg = dg or bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in obs:
        oe = o.evaluated_get(dg)
        m = oe.to_mesh()
        mw = oe.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in m.vertices]
        m.calc_loop_triangles()
        polys += [tuple(off + i for i in t.vertices) for t in m.loop_triangles]
        oe.to_mesh_clear()
    return verts, polys


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def new_mesh_obj(name, verts, faces, mats=(), smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = smooth
    return ob


def rrect_profile(width, thick, seg=3, rfrac=0.9):
    hw, ht = width / 2, thick / 2
    r = min(ht, hw) * rfrac
    prof = []
    for cx, cy, a0 in ((hw - r, ht - r, 0), (-hw + r, ht - r, 90), (-hw + r, -ht + r, 180), (hw - r, -ht + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            prof.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return prof


def sweep(path_pts, ups, prof, caps=True, widths=None):
    """Sweep a 2D profile (side, up) along path_pts with an 'up' vector per point. widths: optional per-point scale of
    the side axis. Returns verts, faces, idx (path index per vertex)."""
    verts, faces, idx = [], [], []
    n, P = len(path_pts), len(prof)
    for i, p in enumerate(path_pts):
        t = (path_pts[min(i + 1, n - 1)] - path_pts[max(i - 1, 0)]).normalized()
        u = ups[i] - t * ups[i].dot(t)
        u.normalize()
        s = t.cross(u)
        ws = widths[i] if widths else 1.0
        for (a, b) in prof:
            verts.append(p + s * a * ws + u * b)
            idx.append(i)
    for i in range(n - 1):
        for k in range(P):
            a, b = i * P + k, i * P + (k + 1) % P
            faces.append((a, b, b + P, a + P))
    if caps:
        faces.append(tuple(range(P))[::-1])
        faces.append(tuple((n - 1) * P + k for k in range(P)))
    return verts, faces, idx


def resample(pts, step):
    """Resample a polyline at a fixed arclength step."""
    out = [pts[0].copy()]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = (b - a).length
        d = step - acc
        while d <= seg:
            out.append(a.lerp(b, d / seg))
            d += step
        acc = seg - (d - step)
    if (out[-1] - pts[-1]).length > step * 0.3:
        out.append(pts[-1].copy())
    return out


def skin(ob, arm, groups):
    """groups: {bone_name: [weight per vertex]}; adds vertex groups + armature modifier (normalised later by Blender)."""
    for bn, ws in groups.items():
        vg = ob.vertex_groups.get(bn) or ob.vertex_groups.new(name=bn)
        for i, w in enumerate(ws):
            if w > 1e-4:
                vg.add([i], float(w), "REPLACE")
    if not any(m.type == "ARMATURE" for m in ob.modifiers):
        md = ob.modifiers.new("rig", "ARMATURE")
        md.object = arm
    ob.parent = arm


def rigid_to_bone(ob, arm, bone):
    """Bone-parent a rigid part (buckle, slider) without skinning; keep its world transform."""
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw


def iter_fcurves(act):
    """Blender 5 slotted actions: fcurves live in layers/strips/channelbags."""
    if getattr(act, "layers", None):
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        yield fc
    else:
        for fc in act.fcurves:
            yield fc


def linearize(act):
    for fc in iter_fcurves(act):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"


def mat_local_from_armature_space(arm, bn, M_arm, parent_arm_mat=None):
    """Basis matrix that puts bone bn at armature-space matrix M_arm, given its parent's armature-space pose matrix."""
    b = arm.data.bones[bn]
    if b.parent:
        Pp = parent_arm_mat
        rest_rel = b.parent.matrix_local.inverted() @ b.matrix_local
        return (Pp @ rest_rel).inverted() @ M_arm
    return b.matrix_local.inverted() @ M_arm


def control_action(arm, name, bones, pose_fn, nsamp=PARAM_FRAMES):
    """Bake a control into a linear action `<name>_param`: frame 1 + k for param k/nsamp.
    pose_fn(p) -> {bone: local basis Matrix}; bones not returned keep identity."""
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions.new(f"{name}_param")
    act.use_fake_user = True
    ad.action = act
    for k in range(nsamp + 1):
        p = k / nsamp
        poses = pose_fn(p)
        for bn in bones:
            pb = arm.pose.bones[bn]
            pb.rotation_mode = "QUATERNION"
            M = poses.get(bn, Matrix.Identity(4))
            loc, rot, sca = M.decompose()
            pb.location, pb.rotation_quaternion, pb.scale = loc, rot, sca
            fr = 1 + PARAM_FRAMES * k / nsamp
            pb.keyframe_insert("location", frame=fr)
            pb.keyframe_insert("rotation_quaternion", frame=fr)
            pb.keyframe_insert("scale", frame=fr)
    linearize(act)
    ad.action = None
    for bn in bones:
        pb = arm.pose.bones[bn]
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    return act


def add_driver_var(d, arm, name, var="p"):
    v = d.variables.new()
    v.name = var
    v.targets[0].id_type = "OBJECT"
    v.targets[0].id = arm
    v.targets[0].data_path = f'["{name}"]'


def wire_control(arm, name, act, bones, default):
    """.blend control: custom prop `name` (0..1, clamped) -> Action constraint (eval time) on each bone it keys."""
    arm[name] = float(default)
    ui = arm.id_properties_ui(name)
    ui.update(min=-1.0, max=2.0, soft_min=0.0, soft_max=1.0, default=float(default))
    for bn in bones:
        pb = arm.pose.bones[bn]
        c = pb.constraints.new("ACTION")
        c.name = f"ctl_{name}"
        c.action = act
        if hasattr(c, "action_slot") and len(act.slots):
            c.action_slot = act.slots[0]
        c.use_eval_time = True
        c.frame_start, c.frame_end = 1, 1 + PARAM_FRAMES
        c.mix_mode = "BEFORE_FULL"
        d = c.driver_add("eval_time").driver
        d.type = "SCRIPTED"
        add_driver_var(d, arm, name)
        d.expression = "min(max(p, 0.0), 1.0)"


def drive_shape_key(kb, arm, name, expr):
    d = kb.driver_add("value").driver
    d.type = "SCRIPTED"
    add_driver_var(d, arm, name)
    d.expression = expr


def set_controls(arm, vals):
    for k, v in vals.items():
        arm[k] = float(v)
    arm.update_tag()
    for o in bpy.data.objects:
        if o.data and getattr(o.data, "shape_keys", None):
            o.data.shape_keys.update_tag() if hasattr(o.data.shape_keys, "update_tag") else None
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def save(path):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path), compress=True)


def base_color_image(ob):
    for m in ob.data.materials:
        if m and m.use_nodes:
            bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf and bsdf.inputs["Base Color"].links:
                n = bsdf.inputs["Base Color"].links[0].from_node
                while n.type != "TEX_IMAGE" and n.inputs and any(i.links for i in n.inputs):
                    n = next(i.links[0].from_node for i in n.inputs if i.links)
                if n.type == "TEX_IMAGE":
                    return n.image
    return None


def tex_sampler(ob, res=1024):
    """Returns f(uv) -> (r, g, b) in sRGB 0..1 from a downscaled copy of the base-colour texture."""
    import numpy as np
    img = base_color_image(ob)
    cp = img.copy()
    cp.scale(res, res)
    a = np.empty(res * res * 4, np.float32)
    cp.pixels.foreach_get(a)
    a = a.reshape(res, res, 4)
    bpy.data.images.remove(cp)

    def f(uv):
        x = int(min(res - 1, max(0, (uv[0] % 1.0) * res)))
        y = int(min(res - 1, max(0, (uv[1] % 1.0) * res)))
        return tuple(float(c) for c in a[y, x, :3])
    return f


def face_uv_center(me, poly, uvl=None):
    uvl = uvl or me.uv_layers.active
    us = [uvl.data[li].uv for li in poly.loop_indices]
    return (sum(u[0] for u in us) / len(us), sum(u[1] for u in us) / len(us))
