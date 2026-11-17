"""Small hard-surface parts appended to a weapon bmesh (units = mesh local units, cm for the pack's guns).

part spec (dict): kind, pos (x,y,z), axis ('+x','-x','+y','-y','+z','-z' or a vector), slot (material index),
group (vertex group name or None), plus per-kind sizes.  Local frame: +Z is the outward axis.
  rivet  r, h            domed head
  pin    r, h [, seg]    chamfered cylinder (pin head, button, screw head)
  hex    r, h            hex bolt head with chamfer
  ring   r, t [, arc, roll]   wire loop (sling loop); stands on its edge, opening along local X
  box    size (sx,sy,sz) [, chamfer, roll]   chamfered block, base on the surface
  tube   r, r_in, h      hollow cylinder (socket, cup)
"""
import math

import bmesh
from mathutils import Matrix, Vector

AX = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}


def _frame(axis, roll=0.0):
    z = Vector(AX[axis] if isinstance(axis, str) else axis).normalized()
    ref = Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((0, 1, 0))
    x = ref.cross(z).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    return m @ Matrix.Rotation(math.radians(roll), 4, "Z")


def _lathe(profile, seg, cap_top=True, cap_bottom=False):
    """profile: list of (r, z) bottom->top.  Returns verts, faces."""
    vs, fs = [], []
    for r, z in profile:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append((math.cos(a) * r, math.sin(a) * r, z))
    for k in range(len(profile) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            fs.append((k * seg + i, k * seg + j, (k + 1) * seg + j, (k + 1) * seg + i))
    if cap_top:
        fs.append(tuple((len(profile) - 1) * seg + i for i in range(seg)))
    if cap_bottom:
        fs.append(tuple(reversed(range(seg))))
    return vs, fs


def _make(p):
    k = p["kind"]
    if k == "rivet":
        r, h = p["r"], p["h"]
        return _lathe([(r, 0), (r * 0.92, h * 0.45), (r * 0.6, h * 0.9), (r * 0.25, h)], p.get("seg", 10))
    if k == "pin":
        r, h = p["r"], p["h"]
        c = min(h * 0.4, r * 0.18)
        return _lathe([(r, 0), (r, h - c), (r - c, h)], p.get("seg", 12))
    if k == "hex":
        r, h = p["r"], p["h"]
        return _lathe([(r, 0), (r, h * 0.75), (r * 0.86, h)], 6)
    if k == "tube":
        r, ri, h = p["r"], p["r_in"], p["h"]
        c = min(h * 0.3, (r - ri) * 0.3)
        return _lathe([(r, 0), (r, h - c), (r - c, h), (ri, h), (ri, h * 0.15)], p.get("seg", 14), cap_top=True)
    if k == "box":
        sx, sy, sz = p["size"]
        c = p.get("chamfer", min(sx, sy, sz) * 0.15)
        vs = []
        for z, inset in ((0, 0), (sz - c, 0), (sz, c)):
            for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                vs.append((x * (sx / 2 - inset), y * (sy / 2 - inset), z))
        fs = []
        for kk in range(2):
            for i in range(4):
                j = (i + 1) % 4
                fs.append((kk * 4 + i, kk * 4 + j, kk * 4 + 4 + j, kk * 4 + 4 + i))
        fs.append((8, 9, 10, 11))
        return vs, fs
    if k == "ring":
        R, t = p["r"], p["t"]
        arc = math.radians(p.get("arc", 360))
        n_major = p.get("seg", 14)
        n_minor = 6
        closed = arc >= 2 * math.pi - 1e-4
        steps = n_major if closed else n_major + 1
        vs, fs = [], []
        a0 = math.pi / 2 - arc / 2
        for i in range(steps):
            a = a0 + arc * i / n_major
            cx, cz = math.cos(a) * R, math.sin(a) * R
            for j in range(n_minor):
                b = 2 * math.pi * j / n_minor
                rr = R + math.cos(b) * t
                vs.append((math.cos(a) * rr, math.sin(b) * t, math.sin(a) * rr + (R if not closed else R)))
        for i in range(steps - (0 if closed else 1)):
            i2 = (i + 1) % steps
            for j in range(n_minor):
                j2 = (j + 1) % n_minor
                fs.append((i * n_minor + j, i2 * n_minor + j, i2 * n_minor + j2, i * n_minor + j2))
        return vs, fs
    raise ValueError(k)


def add_parts(bm, dl, gindex, parts):
    from mathutils.bvhtree import BVHTree
    count = 0
    bvh = BVHTree.FromBMesh(bm) if any(p.get("snap") for p in parts) else None
    bm.faces.ensure_lookup_table()
    gname = {v: k for k, v in gindex.items()}
    orig_faces = list(bm.faces)
    for p in parts:
        vs, fs = _make(p)
        pos = Vector(p["pos"])
        g = p.get("group")
        if p.get("snap"):
            ax = Vector(AX[p["axis"]] if isinstance(p["axis"], str) else p["axis"]).normalized()
            start = pos - ax * pos.dot(ax) + ax * 40.0
            hit, nrm, fidx, dist = bvh.ray_cast(start, -ax, 80.0)
            if hit is None:
                print("DETAIL part snap missed", p["kind"], p["pos"])
                continue
            pos = hit + ax * (p.get("lift", 0.0) - p.get("sink", 0.01))
            if g is None:      # ride along with whatever it sits on
                for k, w in orig_faces[fidx].verts[0][dl].items():
                    if w > 0.5:
                        g = gname[k]
            print("DETAIL part", p["kind"], "at", [round(v, 2) for v in pos], "group", g)
        m = Matrix.Translation(pos) @ _frame(p.get("axis", "+z"), p.get("roll", 0.0))
        bv = [bm.verts.new(m @ Vector(v)) for v in vs]
        if g:
            for v in bv:
                v[dl][gindex[g]] = 1.0
        new_faces = []
        for f in fs:
            try:
                nf = bm.faces.new([bv[i] for i in f])
            except ValueError:
                continue
            nf.material_index = p.get("slot", 0)
            new_faces.append(nf)
        bmesh.ops.recalc_face_normals(bm, faces=new_faces)
        # make sure the shell faces outward: centroid test
        c = sum((v.co for v in bv), Vector()) / len(bv)
        s = sum(f.normal.dot(f.calc_center_median() - c) for f in new_faces)
        if s < 0:
            bmesh.ops.reverse_faces(bm, faces=new_faces)
        bmesh.ops.triangulate(bm, faces=new_faces)
        count += 1
    bm.verts.index_update()
    return count
