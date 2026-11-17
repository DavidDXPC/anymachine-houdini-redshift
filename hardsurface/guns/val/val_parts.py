"""Hard-surface primitives for the VAL rebuild.  Everything is built in a local frame (+Z = the part's axis or
its outward direction) and placed with a 4x4 matrix.  Units are the mesh's own: centimetres.

An Emitter appends geometry to a bmesh, puts every new vertex 100% in one vertex group (or none = neutral_bone)
and tags every new face with a material class and optional bake zones (stipple / lathe / bare)."""
import math

import bmesh
from mathutils import Matrix, Vector

AX = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}


def frame(pos, axis="+z", roll=0.0):
    z = Vector(AX[axis] if isinstance(axis, str) else axis).normalized()
    ref = Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((0, 1, 0))
    x = ref.cross(z).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    return Matrix.Translation(Vector(pos)) @ m @ Matrix.Rotation(math.radians(roll), 4, "Z")


class Emitter:
    def __init__(self, bm, ob, classes):
        self.bm = bm
        self.dl = bm.verts.layers.deform.verify()
        self.gindex = {g.name: g.index for g in ob.vertex_groups}
        self.classes = classes                      # class name -> material slot
        self.zl = {z: (bm.faces.layers.float.get(z) or bm.faces.layers.float.new(z)) for z in ("stipple", "lathe", "bare")}
        self.new_layer = bm.faces.layers.int.get("isnew") or bm.faces.layers.int.new("isnew")
        self.count = 0
        self.tris = {}

    def add(self, geo, M, cls, group=None, zone=None, flip=False, tag=None):
        vs, fs = geo
        bv = [self.bm.verts.new(M @ Vector(v)) for v in vs]
        if group:
            gi = self.gindex[group]
            for v in bv:
                v[self.dl][gi] = 1.0
        new = []
        for f in fs:
            if len(set(f)) < 3:
                continue
            try:
                nf = self.bm.faces.new([bv[i] for i in f])
            except ValueError:
                continue
            nf.material_index = self.classes[cls]
            nf[self.new_layer] = 1
            if zone:
                for z in ([zone] if isinstance(zone, str) else zone):
                    nf[self.zl[z]] = 1.0
            new.append(nf)
        bmesh.ops.recalc_face_normals(self.bm, faces=new)
        c = sum((v.co for v in bv), Vector()) / len(bv)
        s = sum(f.normal.dot(f.calc_center_median() - c) * f.calc_area() for f in new)
        if (s < 0) != flip:
            bmesh.ops.reverse_faces(self.bm, faces=new)
        self.count += 1
        n = sum(len(f.verts) - 2 for f in new)
        self.tris[tag or cls] = self.tris.get(tag or cls, 0) + n
        return new


# ------------------------------------------------------------------ generators (verts, faces)
def lathe(profile, seg=24, cap_top=False, cap_bottom=False, flute=None):
    """profile: [(r, z)] bottom -> top.  flute=(depth, i0, i1): alternate segments of rings i0..i1 sink by depth."""
    vs, fs = [], []
    for k, (r, z) in enumerate(profile):
        for i in range(seg):
            a = 2 * math.pi * i / seg
            rr = r
            if flute and flute[1] <= k <= flute[2] and (i % 2):
                rr = r - flute[0]
            vs.append((math.cos(a) * rr, math.sin(a) * rr, z))
    for k in range(len(profile) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            fs.append((k * seg + i, k * seg + j, (k + 1) * seg + j, (k + 1) * seg + i))
    if cap_top:
        fs.append(tuple((len(profile) - 1) * seg + i for i in range(seg)))
    if cap_bottom:
        fs.append(tuple(reversed(range(seg))))
    return vs, fs


def merge(*geos):
    vs, fs = [], []
    for g in geos:
        o = len(vs)
        vs += list(g[0])
        fs += [tuple(i + o for i in f) for f in g[1]]
    return vs, fs


def xform(geo, M):
    return [tuple(M @ Vector(v)) for v in geo[0]], geo[1]


def box(sx, sy, sz, c=None, cseg=1):
    """Block with base on z=0, all twelve edges chamfered (top) / the four verticals chamfered."""
    c = min(sx, sy, sz) * 0.12 if c is None else c
    hx, hy = sx / 2, sy / 2

    def loop(ix, iy, z):
        # octagon-ish loop: rectangle with corners cut by c
        return [(-hx + ix + c, -hy + iy, z), (hx - ix - c, -hy + iy, z), (hx - ix, -hy + iy + c, z), (hx - ix, hy - iy - c, z),
                (hx - ix - c, hy - iy, z), (-hx + ix + c, hy - iy, z), (-hx + ix, hy - iy - c, z), (-hx + ix, -hy + iy + c, z)]
    rings = [loop(0, 0, 0), loop(0, 0, sz - c), loop(c, c, sz)]
    vs = [p for r in rings for p in r]
    fs = []
    for k in range(2):
        for i in range(8):
            j = (i + 1) % 8
            fs.append((k * 8 + i, k * 8 + j, k * 8 + 8 + j, k * 8 + 8 + i))
    fs.append(tuple(16 + i for i in range(8)))
    return vs, fs


def pin_head(r, h, seg=16, dimple=True):
    """Chamfered pin end with a shallow centre dimple."""
    c = min(h * 0.45, r * 0.16)
    p = [(r, 0), (r, h - c), (r - c, h)]
    if dimple:
        p += [(r * 0.42, h), (r * 0.30, h - c * 0.9), (0.0001, h - c * 0.9)]
        return lathe(p, seg)
    return lathe(p, seg, cap_top=True)


def rivet(r, h, seg=16):
    p = [(r * 1.0, 0), (r * 0.97, h * 0.3), (r * 0.82, h * 0.62), (r * 0.56, h * 0.87), (r * 0.25, h * 0.98), (0.0001, h)]
    return lathe(p, seg)


def hex_bolt(r, h, washer=True, seg=6):
    """Hex head (across corners 2r) with chamfer, on an optional round washer."""
    parts = []
    z0 = 0.0
    if washer:
        parts.append(lathe([(r * 1.28, 0), (r * 1.28, h * 0.18), (r * 1.2, h * 0.24)], 20, cap_top=True))
        z0 = h * 0.22
    parts.append(lathe([(r, z0), (r, h * 0.82), (r * 0.84, h), (r * 0.5, h * 1.02)], seg, cap_top=True))
    return merge(*parts)


def socket_screw(r, h, seg=18):
    """Cap screw: cylindrical head with a hexagonal socket."""
    c = r * 0.14
    head = lathe([(r, 0), (r, h - c), (r - c, h), (r * 0.62, h)], seg)
    # socket: six-sided well; a ring of faces joins the round rim to the hexagon
    rim = [(math.cos(2 * math.pi * i / seg) * r * 0.62, math.sin(2 * math.pi * i / seg) * r * 0.62, h) for i in range(seg)]
    hexa = [(math.cos(2 * math.pi * i / 6) * r * 0.5, math.sin(2 * math.pi * i / 6) * r * 0.5, h) for i in range(6)]
    hexb = [(x, y, h * 0.35) for x, y, _ in hexa]
    vs = rim + hexa + hexb
    fs = stitch(list(range(seg)), list(range(seg, seg + 6)), vs)
    for i in range(6):
        j = (i + 1) % 6
        fs.append((seg + i, seg + j, seg + 6 + j, seg + 6 + i))
    fs.append(tuple(seg + 6 + i for i in range(6)))
    return merge(head, (vs, fs))


def slot_screw(r, h, seg=20, slot_w=None, slot_d=None, dome=0.0):
    """Screw head with a real slot cut across it (slot runs along local X)."""
    w = (slot_w or r * 0.22) / 2
    d = slot_d or h * 0.5
    c = min(h * 0.3, r * 0.14)
    side = lathe([(r, 0), (r, h - c), (r - c, h)], seg)
    R = r - c
    a0 = math.asin(w / R)
    n = seg // 2

    def arc(a_from, a_to, z):
        return [(math.cos(a_from + (a_to - a_from) * i / n) * R, math.sin(a_from + (a_to - a_from) * i / n) * R, z) for i in range(n + 1)]
    up = arc(a0, math.pi - a0, h)                       # +Y half top (D shape)
    dn = arc(math.pi + a0, 2 * math.pi - a0, h)
    if dome:
        up = [(x, y, z + dome * (1 - (x * x + y * y) / (R * R))) for x, y, z in up]
        dn = [(x, y, z + dome * (1 - (x * x + y * y) / (R * R))) for x, y, z in dn]
    vs = up + dn
    fs = [tuple(range(n + 1)), tuple(range(n + 1, 2 * n + 2))]
    # slot: floor and two walls and the two open ends closed by the side wall chamfer ring
    x0 = math.cos(a0) * R
    fl = [(x0, w, h - d), (-x0, w, h - d), (-x0, -w, h - d), (x0, -w, h - d)]
    o = len(vs)
    vs += fl
    fs.append((o, o + 1, o + 2, o + 3))
    fs.append((0, n, o + 1, o))                         # wall under the +Y half's chord
    fs.append((n + 1, 2 * n + 1, o + 3, o + 2))
    # end fillers between the slot ends and the chamfer ring (small quads)
    fs.append((n, n + 1, o + 2, o + 1))
    fs.append((2 * n + 1, 0, o, o + 3))
    return merge(side, (vs, fs))


def cross_screw(r, h, seg=20):
    """Pan head with a cross recess modelled as two crossing slots."""
    head = lathe([(r, 0), (r, h * 0.45), (r * 0.9, h * 0.78), (r * 0.62, h * 0.97), (r * 0.5, h)], seg)
    # recess: a plus-shaped well.  12-gon plus outline stitched to the round rim.
    a, b = r * 0.46, r * 0.11
    plus = [(a, b), (b, b), (b, a), (-b, a), (-b, b), (-a, b), (-a, -b), (-b, -b), (-b, -a), (b, -a), (b, -b), (a, -b)]
    rim = [(math.cos(2 * math.pi * i / seg) * r * 0.5, math.sin(2 * math.pi * i / seg) * r * 0.5, h) for i in range(seg)]
    top = [(x, y, h) for x, y in plus]
    bot = [(x * 0.8, y * 0.8, h * 0.45) for x, y in plus]
    vs = rim + top + bot
    fs = stitch(list(range(seg)), list(range(seg, seg + 12)), vs)
    for i in range(12):
        j = (i + 1) % 12
        fs.append((seg + i, seg + j, seg + 12 + j, seg + 12 + i))
    fs.append(tuple(seg + 12 + i for i in range(12)))
    return merge(head, (vs, fs))


def stitch(outer, inner, vs, centre=None):
    """Triangles filling the band between two loops (index lists, same winding) by walking their angles."""
    pts = [Vector(vs[i]) for i in inner]
    c = Vector(centre) if centre is not None else sum(pts, Vector()) / len(pts)
    # plane basis from the inner loop
    nrm = Vector()
    for i in range(len(pts)):
        nrm += (pts[i] - c).cross(pts[(i + 1) % len(pts)] - c)
    nrm.normalize()
    u = (pts[0] - c).normalized()
    v = nrm.cross(u)

    def ang(i):
        d = Vector(vs[i]) - c
        return math.atan2(d.dot(v), d.dot(u)) % (2 * math.pi)
    oa = sorted(outer, key=ang)
    ia = sorted(inner, key=ang)
    A = [ang(i) for i in oa] + [ang(oa[0]) + 2 * math.pi]
    B = [ang(i) for i in ia] + [ang(ia[0]) + 2 * math.pi]
    oa.append(oa[0])
    ia.append(ia[0])
    fs = []
    i = j = 0
    while i < len(oa) - 1 or j < len(ia) - 1:
        if j >= len(ia) - 1 or (i < len(oa) - 1 and A[i + 1] <= B[j + 1]):
            fs.append((oa[i], oa[i + 1], ia[j]))
            i += 1
        else:
            fs.append((oa[i], ia[j + 1], ia[j]))
            j += 1
    return fs


def holed_patch(outer_pts, centre, normal, r, depth, n=10, floor=True, rim=0.0):
    """A patch bounded by outer_pts with one round hole (well) of radius r sunk along -normal."""
    nrm = Vector(normal).normalized()
    c = Vector(centre)
    ref = Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else Vector((0, 1, 0))
    u = ref.cross(nrm).normalized()
    v = nrm.cross(u)
    vs = [tuple(p) for p in outer_pts]
    no = len(vs)
    top = [c + (u * math.cos(2 * math.pi * i / n) + v * math.sin(2 * math.pi * i / n)) * r for i in range(n)]
    vs += [tuple(p) for p in top]
    fs = stitch(list(range(no)), list(range(no, no + n)), vs, centre=c)
    lo = no
    if rim:                    # small chamfer at the mouth
        ch = [c + (p - c) * (1 - rim / r) - nrm * rim for p in top]
        vs += [tuple(p) for p in ch]
        for i in range(n):
            j = (i + 1) % n
            fs.append((no + i, no + j, no + n + j, no + n + i))
        lo = no + n
        top = ch
    bot = [p - nrm * depth for p in top]
    o = len(vs)
    vs += [tuple(p) for p in bot]
    for i in range(n):
        j = (i + 1) % n
        fs.append((lo + i, lo + j, o + j, o + i))
    if floor:
        fs.append(tuple(o + i for i in range(n)))
    return vs, fs


def tube_band(z0, z1, r, seg, holes=(), hole_r=0.2, depth=0.5, span=2, n=10, phase=0):
    """Cylinder wall between z0 and z1; `holes` = number of round wells spaced evenly (each takes `span` segments)."""
    def P(i, z):
        a = 2 * math.pi * (i + phase) / seg
        return Vector((math.cos(a) * r, math.sin(a) * r, z))
    hole_at = {}
    if holes:
        step = seg // holes
        for k in range(holes):
            hole_at[k * step] = True
    geos = []
    i = 0
    while i < seg:
        if i in hole_at:
            outer = [P(i + k, z0) for k in range(span + 1)] + [P(i + span - k, z1) for k in range(span + 1)]
            am = 2 * math.pi * (i + phase + span / 2) / seg
            nrm = Vector((math.cos(am), math.sin(am), 0))
            cen = (P(i, z0) + P(i + span, z0) + P(i, z1) + P(i + span, z1)) / 4
            geos.append(holed_patch(outer, cen, nrm, hole_r, depth, n=n, rim=hole_r * 0.15))
            i += span
        else:
            geos.append(([tuple(P(i, z0)), tuple(P(i + 1, z0)), tuple(P(i + 1, z1)), tuple(P(i, z1))], [(0, 1, 2, 3)]))
            i += 1
    return merge(*geos)


def disc_holes(r_in, r_out, z, seg, holes, hole_r, hole_rad, depth, n=10, phase=0.0):
    """Flat annulus (normal +Z) with `holes` round wells on the circle of radius hole_rad."""
    geos = []
    per = seg // holes
    for k in range(holes):
        a0 = 2 * math.pi * (k * per) / seg + phase
        pts = []
        for i in range(per + 1):
            a = a0 + 2 * math.pi * i / seg
            pts.append(Vector((math.cos(a) * r_out, math.sin(a) * r_out, z)))
        for i in range(per, -1, -1):
            a = a0 + 2 * math.pi * i / seg
            pts.append(Vector((math.cos(a) * r_in, math.sin(a) * r_in, z)))
        am = a0 + math.pi / holes
        cen = Vector((math.cos(am) * hole_rad, math.sin(am) * hole_rad, z))
        geos.append(holed_patch(pts, cen, (0, 0, 1), hole_r, depth, n=n, rim=hole_r * 0.12))
    return merge(*geos)


def pipe(points, r, seg=8, closed=False, cap=True):
    """Round wire along a polyline (points in local space)."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    vs, fs = [], []
    prev_u = None
    for i, p in enumerate(pts):
        if closed:
            t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        else:
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev_u is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            u = ref.cross(t).normalized()
        else:
            u = (prev_u - t * prev_u.dot(t)).normalized()
        prev_u = u
        w = t.cross(u)
        # mitre: widen at corners so the wire keeps its thickness
        for k in range(seg):
            a = 2 * math.pi * k / seg
            vs.append(tuple(p + (u * math.cos(a) + w * math.sin(a)) * r))
    rings = n if closed else n - 1
    for i in range(rings):
        i2 = (i + 1) % n
        for k in range(seg):
            k2 = (k + 1) % seg
            fs.append((i * seg + k, i2 * seg + k, i2 * seg + k2, i * seg + k2))
    if cap and not closed:
        fs.append(tuple(reversed(range(seg))))
        fs.append(tuple((n - 1) * seg + k for k in range(seg)))
    return vs, fs


def arc_pts(c, r, a0, a1, n, plane="xz"):
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        if plane == "xz":
            out.append((c[0] + math.cos(a) * r, c[1], c[2] + math.sin(a) * r))
        elif plane == "yz":
            out.append((c[0], c[1] + math.cos(a) * r, c[2] + math.sin(a) * r))
        else:
            out.append((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r, c[2]))
    return out


def extrude_poly(poly, h, c=0.0):
    """Extrude a convex 2D polygon (x, y) from z=0 to z=h, top edge chamfered by c."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    vs = [(x, y, 0) for x, y in poly] + [(x, y, h - c) for x, y in poly]
    fs = []
    for i in range(n):
        j = (i + 1) % n
        fs.append((i, j, n + j, n + i))
    if c > 0:
        k = 1 - c / max(1e-6, max(math.hypot(x - cx, y - cy) for x, y in poly))
        vs += [(cx + (x - cx) * k, cy + (y - cy) * k, h) for x, y in poly]
        for i in range(n):
            j = (i + 1) % n
            fs.append((n + i, n + j, 2 * n + j, 2 * n + i))
        fs.append(tuple(2 * n + i for i in range(n)))
    else:
        fs.append(tuple(n + i for i in range(n)))
    fs.append(tuple(reversed(range(n))))
    return vs, fs
