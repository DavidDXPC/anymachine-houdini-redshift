"""Reusable soft-goods rig parts: armature helpers, fill deformer, shoulder straps with strap_length, dangling chains,
buckles. Coordinates are in metres, Z up, bag front faces -Y, back panel at +Y."""
import bpy, bmesh, math
from mathutils import Matrix, Vector, Quaternion
from softlib import *

DOWN = Vector((0, 0, -1))


# ------------------------------------------------------------------ armature
def new_armature(name="rig"):
    ad = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(arm)
    ad.display_type = "STICK"
    return arm


class Bones:
    """Collect bone specs, then build them in one edit-mode pass."""

    def __init__(self, arm):
        self.arm, self.specs = arm, []

    def add(self, name, head, tail, parent=None, up=Vector((0, 0, 1)), connect=False):
        self.specs.append((name, Vector(head), Vector(tail), parent, Vector(up), connect))
        return name

    def chain(self, prefix, pts, parent=None, up=Vector((0, 0, 1)), ups=None):
        names = []
        for i in range(len(pts) - 1):
            names.append(self.add(f"{prefix}{i}", pts[i], pts[i + 1], names[-1] if names else parent,
                                  ups[i] if ups else up, connect=bool(names)))
        return names

    def build(self):
        vl = bpy.context.view_layer
        vl.objects.active = self.arm
        self.arm.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        eb = self.arm.data.edit_bones
        for name, h, t, parent, up, connect in self.specs:
            b = eb.new(name)
            b.head, b.tail = h, t
            d = (t - h).normalized()
            if abs(d.dot(up)) > 0.99:
                up = Vector((0, 1, 0)) if abs(d.y) < 0.9 else Vector((1, 0, 0))
            b.align_roll(up - d * d.dot(up))
            if parent:
                b.parent = eb[parent]
                b.use_connect = connect and (eb[parent].tail - h).length < 1e-6
        bpy.ops.object.mode_set(mode="OBJECT")
        for pb in self.arm.pose.bones:
            pb.rotation_mode = "QUATERNION"


def rest(arm, bn):
    return arm.data.bones[bn].matrix_local.copy()


def aim_matrix(rest_m, head, direction, length_scale=1.0, up_hint=None):
    """Armature-space pose matrix: rest bone rotated so its Y axis points along `direction`, placed at `head`,
    optionally stretched along Y. Minimal rotation from the rest direction keeps twist stable."""
    r3 = rest_m.to_3x3().normalized()
    ry = r3.col[1]
    q = ry.rotation_difference(direction.normalized())
    rot = q.to_matrix() @ r3
    if up_hint is not None:  # extra twist about the new Y so the bone Z follows up_hint
        y = direction.normalized()
        z_now = rot.col[2]
        z_want = (up_hint - y * up_hint.dot(y))
        if z_want.length > 1e-6:
            z_want.normalize()
            ang = math.atan2(y.dot(z_now.cross(z_want)), z_now.dot(z_want))
            rot = Matrix.Rotation(ang, 3, y) @ rot
    M = rot.to_4x4()
    M = M @ Matrix.Diagonal((1, length_scale, 1, 1))
    M.translation = head
    return M


def chain_locals(arm, names, pts, parent_pose=None, stretch=False, ups=None):
    """Pose a bone chain through points pts (len = len(names)+1) in armature space. Returns {bone: local}, and the
    armature-space matrices. parent_pose: armature-space pose matrix of the chain's parent (None = rest)."""
    out, arm_m = {}, {}
    prev = parent_pose
    for i, bn in enumerate(names):
        b = arm.data.bones[bn]
        rl = b.matrix_local
        d = pts[i + 1] - pts[i]
        sc = d.length / b.length if stretch else 1.0
        M = aim_matrix(rl, pts[i], d, sc, ups[i] if ups else None)
        if b.parent:
            P = prev if prev is not None else b.parent.matrix_local
            if i == 0 and parent_pose is None:
                P = b.parent.matrix_local
            L = (P @ (b.parent.matrix_local.inverted() @ rl)).inverted() @ M
        else:
            L = rl.inverted() @ M
        out[bn], arm_m[bn] = L, M
        prev = M
    return out, arm_m


def chain_pts_from_dirs(origin, dirs, lengths):
    pts = [origin.copy()]
    for d, l in zip(dirs, lengths):
        pts.append(pts[-1] + d.normalized() * l)
    return pts


def fit_chain_to_path(origin, path, lengths):
    """Walk along a polyline `path` (starting near origin) and return chain points with the given segment lengths
    (each chain point lands on the path at the next distance from the previous point)."""
    pts = [origin.copy()]
    dense = resample(path, 0.002)
    j = 0
    for l in lengths:
        p = pts[-1]
        while j < len(dense) - 1 and (dense[j] - p).length < l:
            j += 1
        q = dense[j]
        d = q - p
        if d.length < 1e-6:
            d = Vector((0, 0, -1))
        pts.append(p + d.normalized() * l)
    return pts


# ------------------------------------------------------------------ weights
def chain_weights(verts, pts, names, falloff=0.35):
    """Weight vertices to a bone chain by projection onto the chain polyline, blending to the neighbour bone near
    joints (falloff = fraction of segment length used for blending on each side)."""
    W = {n: [0.0] * len(verts) for n in names}
    segs = [(pts[i], pts[i + 1]) for i in range(len(names))]
    for vi, v in enumerate(verts):
        best, bd, bt = 0, 1e9, 0.0
        for si, (a, b) in enumerate(segs):
            ab = b - a
            t = max(0.0, min(1.0, (v - a).dot(ab) / ab.length_squared))
            d = (a + ab * t - v).length
            if d < bd:
                best, bd, bt = si, d, t
        w = {best: 1.0}
        if bt < falloff and best > 0:
            k = 0.5 * (1 - bt / falloff)
            w = {best: 1 - k, best - 1: k}
        elif bt > 1 - falloff and best < len(names) - 1:
            k = 0.5 * (1 - (1 - bt) / falloff)
            w = {best: 1 - k, best + 1: k}
        for si, ww in w.items():
            W[names[si]][vi] = ww
    return W


# ------------------------------------------------------------------ meshes
def strap_object(name, pts, ups, width, thick, material, seg=2, widths=None):
    prof = rrect_profile(width, thick, seg=seg)
    v, f, idx = sweep(pts, ups, prof, caps=True, widths=widths)
    ob = new_mesh_obj(name, v, f, [material])
    return ob, idx


def buckle_male(name, at, fwd, up, w=0.040, l=0.045, t=0.010, material=None):
    """Side-release buckle tongue: a tapered prong block. fwd = direction of the tongue (toward the female)."""
    side = fwd.cross(up).normalized()
    up = side.cross(fwd).normalized()
    verts, faces = [], []
    secs = [(0.0, w / 2, t / 2), (l * 0.35, w / 2, t / 2), (l * 0.75, w * 0.42, t * 0.42), (l, w * 0.25, t * 0.3)]
    for (s, hw, ht) in secs:
        c = at + fwd * s
        for (a, b) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append(c + side * a * hw + up * b * ht)
    for i in range(len(secs) - 1):
        for k in range(4):
            a, b = i * 4 + k, i * 4 + (k + 1) % 4
            faces.append((a, b, b + 4, a + 4))
    faces += [(3, 2, 1, 0), tuple(len(verts) - 4 + k for k in range(4))]
    ob = new_mesh_obj(name, verts, faces, [material], smooth=False)
    bev = ob.modifiers.new("bev", "BEVEL")
    bev.width, bev.segments = t * 0.12, 2
    return ob


def buckle_female(name, at, fwd, up, w=0.044, l=0.040, t=0.013, material=None):
    """Female buckle housing: a box with a slot, opening toward -fwd (where the tongue enters)."""
    side = fwd.cross(up).normalized()
    up = side.cross(fwd).normalized()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = at + fwd * (v.co.y + 0.5) * l + side * v.co.x * w + up * v.co.z * t
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(material)
    bev = ob.modifiers.new("bev", "BEVEL")
    bev.width, bev.segments = t * 0.2, 2
    return ob


def ladder_lock(name, at, fwd, up, w=0.042, l=0.024, t=0.006, material=None):
    return buckle_female(name, at, fwd, up, w, l, t, material)


def apply_mods(ob):
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        if m.type != "ARMATURE":
            bpy.ops.object.modifier_apply(modifier=m.name)


def join_objects(obs, name):
    vl = bpy.context.view_layer
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    vl.objects.active = obs[0]
    bpy.ops.object.join()
    obs[0].name = name
    return obs[0]


def weights_from_nearest(target, source, groups):
    """Copy vertex-group weights for `groups` from the nearest source vertex (source = skinned body)."""
    from mathutils.kdtree import KDTree
    sv = source.data.vertices
    kd = KDTree(len(sv))
    for i, v in enumerate(sv):
        kd.insert(v.co, i)
    kd.balance()
    gidx = {g: source.vertex_groups[g].index for g in groups if g in source.vertex_groups}
    out = {g: [0.0] * len(target.data.vertices) for g in gidx}
    mw = target.matrix_world
    for vi, v in enumerate(target.data.vertices):
        co, si, _ = kd.find(mw @ v.co)
        for g in sv[si].groups:
            for name, gi in gidx.items():
                if g.group == gi:
                    out[name][vi] = g.weight
    return out


# ------------------------------------------------------------------ dangling chain sim (jiggle)
def simulate_dangle(anchor_frames, seg_len, n, gravity=9.81, damping=0.06, fps=24, substeps=8, stiff_dir=None, stiffness=0.0):
    """Verlet chain hanging from a moving anchor. anchor_frames: list of (anchor_point, anchor_dir) per frame in world
    space; anchor_dir is the chain's preferred direction at the anchor (used for a light bending stiffness on the
    first link). Returns per frame a list of n+1 points (point 0 = anchor)."""
    dt = 1.0 / fps / substeps
    p0, d0 = anchor_frames[0]
    pts = [p0 + d0.normalized() * seg_len * i for i in range(n + 1)]
    prev = [p.copy() for p in pts]
    out = []
    g = Vector((0, 0, -gravity))
    for f, (ap, ad) in enumerate(anchor_frames):
        if f > 0:
            apr, adr = anchor_frames[f - 1]
        for s in range(substeps):
            t = (s + 1) / substeps
            a_now = apr.lerp(ap, t) if f > 0 else ap
            d_now = adr.lerp(ad, t) if f > 0 else ad
            pts[0] = a_now
            for i in range(1, n + 1):
                v = (pts[i] - prev[i]) * (1 - damping)
                prev[i] = pts[i].copy()
                acc = g.copy()
                if stiffness > 0:  # pull each link toward the anchor direction (fabric/webbing has some stiffness)
                    want = pts[i - 1] + d_now.normalized() * seg_len
                    acc += (want - pts[i]) * stiffness * (1.0 / (i))
                pts[i] = pts[i] + v + acc * dt * dt
            for _ in range(6):
                for i in range(n):
                    a, b = pts[i], pts[i + 1]
                    d = b - a
                    L = d.length or 1e-9
                    corr = d * ((L - seg_len) / L)
                    if i == 0:
                        pts[i + 1] = b - corr
                    else:
                        pts[i] = a + corr * 0.5
                        pts[i + 1] = b - corr * 0.5
        out.append([p.copy() for p in pts])
    return out
