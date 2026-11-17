"""Modelling helpers and the new SVD parts.  Units: centimetres in the pack's mesh space
(muzzle -Y, up +Z, the rifle's right side is -X).  The gun's centre plane is x = XC."""
import math

import bmesh
import bpy
from mathutils import Vector

XC = -0.168      # centre plane of the pack mesh
ZB = -0.705      # bore axis height
GZ = 1.20        # gas tube axis height


# ------------------------------------------------------------------ primitives
def fix(bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def lathe(profile, o, a=(0, 1, 0), seg=20, closed=False, caps=(True, True), phase=0.0):
    """Revolve profile [(t, r)] about the axis through o with direction a."""
    o = Vector(o)
    a = Vector(a).normalized()
    ref = Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))
    u = a.cross(ref).normalized()
    v = u.cross(a)
    bm = bmesh.new()
    rings = []
    for t, r in profile:
        rings.append([bm.verts.new(o + a * t + (u * math.cos(phase + 2 * math.pi * i / seg)
                                                + v * math.sin(phase + 2 * math.pi * i / seg)) * r) for i in range(seg)])
    n = len(rings)
    for k in range(n if closed else n - 1):
        A, B = rings[k], rings[(k + 1) % n]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((A[i], A[j], B[j], B[i]))
    if not closed:
        if caps[0]:
            bm.faces.new(rings[0])
        if caps[1]:
            bm.faces.new(rings[-1])
    return fix(bm)


def ylathe(profile, cz, cx=XC, **kw):
    return lathe(profile, (cx, 0, cz), (0, 1, 0), **kw)


def prism(poly, plane, d0, d1):
    """Extrude a 2D polygon.  plane 'yz' extrudes along x, 'xz' along y, 'xy' along z."""
    bm = bmesh.new()

    def mk(p, d):
        return {"yz": (d, p[0], p[1]), "xz": (p[0], d, p[1]), "xy": (p[0], p[1], d)}[plane]
    A = [bm.verts.new(mk(p, d0)) for p in poly]
    B = [bm.verts.new(mk(p, d1)) for p in poly]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(A)
    bm.faces.new(B[::-1])
    return fix(bm)


def box(x0, x1, y0, y1, z0, z1):
    return prism([(y0, z0), (y1, z0), (y1, z1), (y0, z1)], "yz", x0, x1)


def stadium(yc, zc, length, height, n=5):
    r = height / 2
    h = length / 2 - r
    pts = []
    for i in range(n + 1):
        an = -math.pi / 2 + math.pi * i / n
        pts.append((yc + h + math.cos(an) * r, zc + math.sin(an) * r))
    for i in range(n + 1):
        an = math.pi / 2 + math.pi * i / n
        pts.append((yc - h + math.cos(an) * r, zc + math.sin(an) * r))
    return pts


def loft(sections, caps=(True, True)):
    bm = bmesh.new()
    rings = [[bm.verts.new(p) for p in s] for s in sections]
    n = len(rings[0])
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((A[i], A[j], B[j], B[i]))
    if caps[0]:
        bm.faces.new(rings[0])
    if caps[1]:
        bm.faces.new(rings[-1])
    return fix(bm)


def bev(bm, offset, segs=1, angle=30, faces=None):
    """Bevel the sharp manifold edges."""
    fs = set(faces) if faces is not None else None
    T = math.radians(angle)
    es = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        if fs is not None and not (e.link_faces[0] in fs and e.link_faces[1] in fs):
            continue
        if e.calc_face_angle(0) > T and e.calc_length() > offset * 2.2:
            es.append(e)
    if es:
        bmesh.ops.bevel(bm, geom=es, offset=offset, offset_type="OFFSET", segments=segs, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
    return bm


def join(*bms):
    out = bmesh.new()
    for b in bms:
        m = bpy.data.meshes.new("tmp")
        b.to_mesh(m)
        out.from_mesh(m)
        bpy.data.meshes.remove(m)
    return out


def boolean(a, b, op="DIFFERENCE"):
    col = bpy.context.scene.collection
    obs = []
    for nm, bm in (("ba", a), ("bb", b)):
        m = bpy.data.meshes.new(nm)
        bm.to_mesh(m)
        o = bpy.data.objects.new(nm, m)
        col.objects.link(o)
        obs.append(o)
    mod = obs[0].modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.object = obs[1]
    mod.solver = "EXACT"
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obs[0].evaluated_get(dg))
    out = bmesh.new()
    out.from_mesh(me)
    bpy.data.meshes.remove(me)
    for o in obs:
        m = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(m)
    bmesh.ops.remove_doubles(out, verts=out.verts[:], dist=0.0005)
    return fix(out)


def remesh(bm, voxel, smooth_it, tris):
    """Voxel-remesh a faceted pack part into one watertight skin, round it off, and reduce it again."""
    m = bpy.data.meshes.new("rm")
    bm.to_mesh(m)
    bm.free()
    o = bpy.data.objects.new("rm", m)
    bpy.context.scene.collection.objects.link(o)
    r = o.modifiers.new("r", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = voxel
    r.adaptivity = 0.0
    sm = o.modifiers.new("s", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = smooth_it
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    n = len(me.polygons) * 2
    o2 = bpy.data.objects.new("rm2", me)
    bpy.context.scene.collection.objects.link(o2)
    d = o2.modifiers.new("d", "DECIMATE")
    d.ratio = min(1.0, tris / max(n, 1))
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(o2.evaluated_get(dg))
    out = bmesh.new()
    out.from_mesh(me2)
    for ob_ in (o, o2):
        bpy.data.objects.remove(ob_, do_unlink=True)
    for mm in (m, me, me2):
        bpy.data.meshes.remove(mm)
    print("SVD remesh %d -> %d faces" % (n, len(out.faces)))
    return out


def xpin(y, z, x0, x1, r, seg=12, c=0.03):
    """Cross pin along X with chamfered ends."""
    L = x1 - x0
    return lathe([(0, r - c), (c, r), (L - c, r), (L, r - c)], (x0, y, z), (1, 0, 0), seg=seg)


# ------------------------------------------------------------------ handguard sections
_KEYS = [
    (-42.5, [(0.60, -2.69), (1.29, -2.35), (1.75, -1.40), (1.06, 1.79), (0.50, 2.60)]),
    (-25.1, [(0.60, -2.64), (1.44, -2.23), (1.97, -1.15), (1.30, 1.83), (0.50, 2.72)]),
    (-17.2, [(0.70, -3.72), (1.74, -3.35), (2.20, -2.10), (1.30, 1.70), (0.50, 2.75)]),
    (-15.4, [(0.70, -3.72), (1.79, -3.40), (2.26, -2.13), (1.30, 1.70), (0.50, 2.75)]),
]


def _chaikin(pts, it=2):
    for _ in range(it):
        out = []
        n = len(pts)
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % n]
            out.append((p[0] * 0.75 + q[0] * 0.25, p[1] * 0.75 + q[1] * 0.25))
            out.append((p[0] * 0.25 + q[0] * 0.75, p[1] * 0.25 + q[1] * 0.75))
        pts = out
    return pts


def hg_section(y, scale=1.0, clip=None, ysec=None, inner=False):
    """Closed handguard cross-section at station y (40 points, world cm)."""
    ys = y if ysec is None else ysec
    ks = _KEYS
    if ys <= ks[0][0]:
        half = ks[0][1]
    elif ys >= ks[-1][0]:
        half = ks[-1][1]
    else:
        for (y0, a), (y1, b) in zip(ks, ks[1:]):
            if y0 <= ys <= y1:
                t = (ys - y0) / (y1 - y0)
                half = [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t) for p, q in zip(a, b)]
                break
    poly = list(half) + [(-p[0], p[1]) for p in reversed(half)]
    poly = _chaikin(poly)
    out = []
    for dx, z in poly:
        if inner:
            dx, z = dx * 0.70, (z + 0.2) * 0.74 - 0.2
        dx, z = dx * scale, (z + 0.3) * scale - 0.3
        if clip is not None:
            z = min(z, clip)
        out.append(Vector((XC + dx, y, z)))
    return out


# ------------------------------------------------------------------ the parts.  each returns [(bmesh, class, group)]
def barrel():
    prof = [(-76.2, 0.76), (-70.5, 0.78), (-53.3, 0.80), (-25.0, 0.80), (-23.0, 1.13), (-20.0, 1.13), (-19.2, 1.25),
            (-18.9, 1.35), (-16.1, 1.35), (-16.0, 1.45), (-12.45, 1.45)]
    return [(ylathe(prof, ZB, seg=20), "steel_blued", None)]


def flash_hider():
    outer = [(-82.75, 0.60), (-82.55, 0.74), (-81.95, 0.78), (-81.80, 0.90), (-81.45, 0.90), (-81.30, 0.78),
             (-76.25, 0.78), (-76.05, 0.95), (-75.0, 0.95), (-74.75, 0.88)]
    inner = [(-74.75, 0.47), (-82.75, 0.47)]
    body = ylathe(outer + inner, ZB, seg=20, closed=True)
    cut = []
    for k in range(5):
        an = math.radians(90 + 72 * k)
        c = prism(stadium(-78.75, 0.0, 4.3, 0.30, n=3), "yz", 0.2, 1.3)      # along +x, rotate into place
        bmesh.ops.rotate(c, verts=c.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(-an, 3, "Y"))
        bmesh.ops.translate(c, verts=c.verts, vec=(XC, 0, ZB))
        cut.append(c)
    body = boolean(body, join(*cut))
    return [(body, "steel_park", None)]


def front_sight():
    out = []
    sleeve = ylathe([(-74.75, 0.84), (-74.6, 0.93), (-73.2, 0.93), (-73.1, 0.88), (-72.9, 0.88), (-72.8, 0.93),
                     (-70.65, 0.93), (-70.5, 0.84)], ZB, seg=20)
    out.append((sleeve, "steel_park", None))
    tower = prism([(-74.0, -0.45), (-70.8, -0.45), (-71.25, 0.85), (-71.38, 2.42), (-73.38, 2.42), (-73.5, 0.85)],
                  "yz", XC - 0.52, XC + 0.52)
    tower = boolean(tower, prism([(-72.95, 0.62), (-71.85, 0.62), (-71.95, 1.75), (-72.85, 1.75)], "yz", XC - 2, XC + 2))
    bev(tower, 0.06)
    out.append((tower, "steel_park", None))
    hz = 3.235
    hood = ylathe([(-73.38, 0.80), (-73.30, 0.845), (-71.50, 0.845), (-71.42, 0.80), (-71.42, 0.70), (-73.38, 0.70)],
                  hz, seg=24, closed=True)
    hood = boolean(hood, lathe([(0.3, 0.22), (1.2, 0.22)], (XC, -72.4, hz), (0, 0, 1), seg=12))
    out.append((hood, "steel_park", None))
    out.append((bev(box(XC - 0.46, XC + 0.46, -73.0, -71.8, 2.25, 2.56), 0.04), "steel_park", None))
    post = lathe([(2.50, 0.24), (2.68, 0.24), (2.72, 0.20), (2.84, 0.20), (2.88, 0.10), (3.33, 0.085), (3.39, 0.06)],
                 (XC, -72.4, 0), (0, 0, 1), seg=10)
    out.append((post, "steel_milled", None))
    lug = join(box(XC - 0.22, XC + 0.22, -72.1, -70.6, -2.2, -1.4), box(XC - 0.42, XC + 0.42, -72.1, -70.6, -2.58, -2.2))
    out.append((bev(lug, 0.05), "steel_park", None))
    for y in (-73.75, -71.0):
        out.append((xpin(y, -0.05, XC - 0.57, XC + 0.57, 0.13), "steel_milled", None))
    return out


def gas_system():
    out = []
    out.append((ylathe([(-53.3, 0.84), (-53.15, 0.95), (-49.9, 0.95), (-49.75, 0.84)], ZB, seg=20), "steel_park", None))
    blk = prism([(-53.15, -0.3), (-52.7, 0.35), (-51.5, 1.25), (-50.75, 1.98), (-49.8, 1.98), (-49.8, -0.3)],
                "yz", XC - 0.64, XC + 0.64)
    out.append((bev(blk, 0.08), "steel_park", None))
    cham = ylathe([(-50.3, 0.62), (-50.15, 0.76), (-47.35, 0.76), (-47.25, 0.68), (-47.0, 0.68), (-46.9, 0.88),
                   (-46.75, 0.92), (-46.1, 0.92), (-45.95, 0.86), (-45.9, 0.60), (-44.2, 0.60)], GZ, seg=18)
    out.append((cham, "steel_blued", None))
    # regulator: knurled ring with a setting lug
    for k in range(9):
        an = 2 * math.pi * k / 9
        t = box(-0.07, 0.07, -46.7, -46.15, 0.88, 0.99)
        bmesh.ops.rotate(t, verts=t.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(an, 3, "Y"))
        bmesh.ops.translate(t, verts=t.verts, vec=(XC, 0, GZ))
        out.append((t, "steel_blued", None))
    out.append((bev(box(XC - 0.17, XC + 0.17, -51.1, -49.5, 1.9, 2.12), 0.04), "steel_milled", None))   # latch
    out.append((ylathe([(-44.3, 0.50), (-14.2, 0.50)], GZ, seg=10, caps=(False, False)), "steel_blued", None))
    for y in (-52.3, -50.6):
        out.append((xpin(y, ZB, XC - 0.99, XC + 0.99, 0.12), "steel_milled", None))
    out.append((xpin(-50.4, GZ + 0.3, XC - 0.69, XC + 0.69, 0.12), "steel_milled", None))
    return out


VENTS = [(-39.9, 0.60), (-34.45, 0.60), (-29.0, 0.60), (-37.2, -0.82), (-31.7, -0.82), (-26.3, -0.82)]


def handguard():
    out = []
    st = [(-42.84, 0.93, None), (-42.55, 1.0, None), (-39.0, 1.0, None), (-35.0, 1.0, None), (-31.0, 1.0, None),
          (-27.0, 1.0, None), (-25.1, 1.0, None), (-22.5, 1.0, None), (-20.3, 1.0, None), (-20.12, 1.0, 2.08),
          (-17.2, 1.0, 2.08), (-15.4, 1.0, 2.08)]
    bm = bmesh.new()
    O = [[bm.verts.new(p) for p in hg_section(y, s, clip=c)] for y, s, c in st]
    I = [[bm.verts.new(p) for p in hg_section(y, 1.0, clip=(c - 0.42) if c else None, inner=True)] for y, s, c in st]
    n = len(O[0])
    for k in range(len(st) - 1):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((O[k][i], O[k][j], O[k + 1][j], O[k + 1][i]))
            bm.faces.new((I[k][j], I[k][i], I[k + 1][i], I[k + 1][j]))
    for k in (0, len(st) - 1):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((O[k][i], O[k][j], I[k][j], I[k][i]))
    fix(bm)
    cut = join(*[prism(stadium(y, z, 3.0, 0.80), "yz", XC - 4, XC + 4) for y, z in VENTS])
    bm = boolean(bm, cut)
    # soften the vent rims: bevel the sharp edges that lie on a vent outline
    es = []
    for e in bm.edges:
        if len(e.link_faces) != 2 or e.calc_face_angle(0) < math.radians(50):
            continue
        m = (e.verts[0].co + e.verts[1].co) / 2
        if any(abs(m.y - y) < 1.56 and abs(m.z - z) < 0.46 for y, z in VENTS) and abs(m.x - XC) > 1.2:
            es.append(e)
    if es:
        bmesh.ops.bevel(bm, geom=es, offset=0.06, offset_type="OFFSET", segments=2, profile=0.5, affect="EDGES",
                        clamp_overlap=True)
    out.append((bm, "wood", None))
    # steel cap at the front with its collar and spring latch
    cap = loft([hg_section(-44.33, 0.88, ysec=-42.5), hg_section(-44.2, 0.965, ysec=-42.5),
                hg_section(-42.86, 0.965, ysec=-42.5)])
    out.append((cap, "steel_blued", None))
    out.append((ylathe([(-45.0, 0.86), (-44.9, 0.98), (-44.3, 0.98)], ZB, seg=20), "steel_blued", None))
    out.append((bev(box(XC - 0.45, XC + 0.45, -44.6, -42.2, -3.0, -2.55), 0.06), "steel_park", None))
    # ferrule at the rear
    fer = loft([hg_section(-15.42, 1.0, clip=1.86, ysec=-15.4), hg_section(-15.30, 1.035, clip=1.92, ysec=-15.4),
                hg_section(-14.08, 1.035, clip=1.92, ysec=-15.4), hg_section(-13.99, 1.0, clip=1.86, ysec=-15.4)])
    out.append((fer, "steel_blued", None))
    return out


def rear_sight():
    out = []
    base = prism([(-20.0, 0.62), (-13.95, 0.62), (-13.95, 1.95), (-15.0, 2.26), (-19.1, 2.26), (-20.0, 1.9)],
                 "yz", XC - 0.78, XC + 0.78)
    out.append((bev(base, 0.07), "steel_blued", None))
    for s in (-1, 1):
        ear = prism([(-19.95, 2.2), (-18.6, 2.2), (-18.75, 2.72), (-19.1, 2.86), (-19.6, 2.86), (-19.95, 2.6)], "yz",
                    XC + s * 0.52, XC + s * 0.78)
        out.append((bev(ear, 0.04), "steel_blued", None))
    out.append((xpin(-19.28, 2.52, XC - 0.86, XC + 0.86, 0.15), "steel_milled", None))
    leaf = prism([(-19.55, 2.36), (-13.36, 2.56), (-13.36, 2.80), (-19.55, 2.68)], "yz", XC - 0.42, XC + 0.42)
    out.append((bev(leaf, 0.03), "steel_blued", None))
    notch = box(XC - 0.56, XC + 0.56, -13.36, -13.07, 2.50, 2.99)
    notch = boolean(notch, box(XC - 0.085, XC + 0.085, -14, -13, 2.85, 3.2))
    out.append((bev(notch, 0.03), "steel_blued", None))
    sl = box(XC - 0.62, XC + 0.62, -16.95, -16.3, 2.36, 2.92)
    out.append((bev(sl, 0.05), "steel_park", None))
    for s in (-1, 1):
        out.append((lathe([(0, 0.19), (0.16, 0.19), (0.2, 0.15)], (XC + s * 0.62, -16.62, 2.62), (s, 0, 0), seg=10),
                    "steel_milled", None))
    # leaf spring under the leaf
    out.append((box(XC - 0.3, XC + 0.3, -18.6, -14.4, 2.26, 2.34), "steel_milled", None))
    return out


def scope_rail():
    x0 = XC + 1.70
    prof = [(x0, -3.38), (x0 + 0.32, -3.38), (x0 + 0.60, -3.62), (x0 + 0.60, -2.02), (x0 + 0.32, -2.26), (x0, -2.26)]
    rail = prism(prof, "xz", -9.7, 9.5)
    cut = join(*[prism(stadium(yc, -2.82, L, 0.62, n=3), "yz", x0 + 0.44, x0 + 2) for yc, L in ((-5.9, 5.2), (0.6, 5.2), (6.4, 3.6))])
    rail = boolean(rail, cut)
    out = [(rail, "steel_park", None)]
    for y in (-9.1, -2.65, 3.8, 8.9):
        out.append((lathe([(0, 0.2), (0.05, 0.19), (0.085, 0.12), (0.1, 0.04)], (x0 + 0.60, y, -2.82), (1, 0, 0), seg=10,
                          caps=(False, True)), "steel_milled", None))
    return out


def all_parts():
    out = []
    for fn in (barrel, flash_hider, front_sight, gas_system, handguard, rear_sight, scope_rail):
        ps = fn()
        print("SVD part", fn.__name__, sum(len(p[0].faces) for p in ps), "faces")
        out += ps
    return out
