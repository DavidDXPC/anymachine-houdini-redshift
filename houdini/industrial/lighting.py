import math
from . import builder as hs
from .geometry import Vector as V, Matrix, Mesh
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
IDS = ["wellglass", "tube_light", "flood", "obstruction_light", "helideck_lights", "escape_route", "beacon", "work_light"]
T = Matrix.Translation
def R(deg, axis): return Matrix.Rotation(math.radians(deg), 4, axis)
# lit materials: wear key -> final material name, emission colour (linear RGB), strength, look when off (tint, rough)
LIT = {
    "wellglass":        dict(mat="wellglass__lit",              rgb=(1.0, 0.74, 0.46), strength=6.0,  off=(0.40, 0.44, 0.41), rough=0.22),
    "tube_light":       dict(mat="tube_light__lit",             rgb=(0.80, 0.90, 1.0), strength=5.0,  off=(0.80, 0.82, 0.80), rough=0.25),
    "flood":            dict(mat="flood__lit",                  rgb=(1.0, 0.52, 0.14), strength=12.0, off=(0.55, 0.56, 0.54), rough=0.15),
    "obstruction":      dict(mat="obstruction_light__lit",      rgb=(1.0, 0.03, 0.015), strength=8.0, off=(0.20, 0.012, 0.010), rough=0.2),
    "heli_green":       dict(mat="helideck_lights__lit",        rgb=(0.04, 1.0, 0.32), strength=6.0,  off=(0.03, 0.30, 0.13), rough=0.2),
    "heli_yellow":      dict(mat="helideck_lights__lit_yellow", rgb=(1.0, 0.78, 0.04), strength=8.0,  off=(0.80, 0.60, 0.05), rough=0.25, tex=True),
    "heli_flood":       dict(mat="helideck_lights__lit_flood",  rgb=(1.0, 0.93, 0.80), strength=8.0,  off=(0.62, 0.63, 0.60), rough=0.2),
    "escape_sign":      dict(mat="escape_route__lit",           rgb=(0.10, 1.0, 0.40), strength=4.0,  off=(0.03, 0.45, 0.20), rough=0.3, tex=True),
    "escape_strip":     dict(mat="escape_route__lit_strip",     rgb=(0.50, 1.0, 0.40), strength=1.2,  off=(0.66, 0.72, 0.40), rough=0.45),
    "beacon":           dict(mat="beacon__lit",                 rgb=(1.0, 0.46, 0.02), strength=8.0,  off=(0.60, 0.24, 0.02), rough=0.2),
    "work":             dict(mat="work_light__lit",             rgb=(1.0, 0.90, 0.74), strength=12.0, off=(0.60, 0.61, 0.58), rough=0.15),
    "work_hand":        dict(mat="work_light__lit_hand",        rgb=(1.0, 0.82, 0.58), strength=5.0,  off=(0.42, 0.45, 0.42), rough=0.22),
}
# flat colours for the --nobake geometry preview
FLAT = dict(grey=(0.55, 0.57, 0.58), dgrey=(0.13, 0.14, 0.15), galv=(0.5, 0.52, 0.53), brass=(0.6, 0.42, 0.15), black=(0.02, 0.02, 0.02),
            yellow=(0.7, 0.5, 0.05), stainless=(0.65, 0.66, 0.66), white=(0.85, 0.85, 0.82), refl=(0.8, 0.8, 0.8), dark=(0.03, 0.03, 0.03),
            plate=(0.6, 0.6, 0.58), red=(0.5, 0.05, 0.04), green=(0.03, 0.3, 0.14), pole=(0.5, 0.52, 0.53), led=(0.85, 0.7, 0.2), orange=(0.8, 0.3, 0.05))


class Fam:
    def __init__(s, name="lighting"):
        s.b = hs.Build(name); s.parts = {}; s.x = 0.0; s.objects = {}; s.base = Matrix.Identity(4)

    # ---------------------------------------------------------------- parts and objects
    def part(s, name, half):
        s.x += half + 0.3
        s.b.tag = len(s.parts) + 1; s.base = T((s.x, 0, 0)); s.b.xf = s.base.copy()
        s.parts[name] = dict(tag=s.b.tag, base=s.base.copy()); s.x += half + 0.3
        return s.b

    def xf(s, M=None):
        s.b.xf = (s.base @ M) if M is not None else s.base.copy()

    def obj(s, fid, name, inst, **meta):
        s.objects[name] = dict(id=fid, inst=[(p, (m if m is not None else Matrix.Identity(4))) for p, m in inst], meta=meta)

    def decal(s, img, c, n, up, w, h=None, kind="label", mats=("grey",), depth=0.012, strength=1.0):
        M = s.b.xf; rot = M.to_3x3()
        s.b.decal(img, M @ V(c), rot @ V(n), rot @ V(up), w, h, kind=kind, mats=mats, depth=depth, strength=strength)

    # ---------------------------------------------------------------- geometry helpers
    def tube(s, name, pts, r, n=5, mat="galv", bend=0.0, seg=2, caps=(False, False), detail=False, phase=0.5):
        """A round bar or pipe along a polyline, corners rounded to radius 'bend' with 'seg' steps (from cabinets/kit.py)."""
        b = s.b; P = [V(p) for p in pts]; path = [P[0]]
        for i in range(1, len(P) - 1):
            a, c, d = P[i - 1], P[i], P[i + 1]
            u = (a - c).normalized(); w = (d - c).normalized(); ang = u.angle(w)
            if bend <= 0 or ang > math.pi - 1e-3:
                path.append(c); continue
            t = min(bend / math.tan(ang / 2), (a - c).length * (0.49 if i > 1 else 0.98), (d - c).length * (0.49 if i < len(P) - 2 else 0.98))
            rr = t * math.tan(ang / 2); ctr = c + (u + w).normalized() * (rr / math.sin(ang / 2))
            v0 = c + u * t - ctr; v1 = c + w * t - ctr; sweep = v0.angle(v1); axis = v0.cross(v1).normalized()
            for k in range(seg + 1): path.append(ctr + Matrix.Rotation(sweep * k / seg, 3, axis) @ v0)
        path.append(P[-1])
        tans = [(path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized() for i in range(len(path))]
        t0 = tans[0]; ex = t0.cross(V(Z)).normalized() if abs(t0.z) < 0.9 else V(X)
        bm = Mesh(); rings = []
        for i, (p, t) in enumerate(zip(path, tans)):
            if i > 0: ex = (tans[i - 1].rotation_difference(t) @ ex).normalized()
            ey = t.cross(ex)
            rings.append([bm.verts.new(p + (ex * math.cos(2 * math.pi * (k + phase) / n) + ey * math.sin(2 * math.pi * (k + phase) / n)) * r) for k in range(n)])
        for a, c in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n; bm.faces.new((a[i], a[j], c[j], c[i]))
        if caps[0]: bm.faces.new(list(reversed(rings[0])))
        if caps[1]: bm.faces.new(rings[-1])

        return b._obj(bm, name, mat, detail)

    def gland(s, p, n, r=0.013, L=0.03, cable=0.0, cr=None, mat="brass"):
        """Cable gland: hex body on a face at p, pointing along n; 'cable' = length of cable stub leaving it."""
        b = s.b; p, n = V(p), V(n).normalized()
        b.cyl("gland", p, p + n * L, r, n=6, mat=mat, caps=(False, True), r1=r * 0.7)
        b.cyl("d_glandnut", p - n * 0.001, p + n * L * 0.45, r * 1.12, n=6, mat=mat, caps=(False, True), detail=True)
        if cable > 0: b.cyl("cable", p + n * L, p + n * (L + cable), cr or r * 0.5, n=5, mat="black", caps=(False, True))

    def bolt(s, p, n, r=0.006, h=0.004, mat="stainless", hexa=True):
        s.b.bolt(p, n, r=r, h=h, mat=mat, hexa=hexa)

    def facet_ribs(s, at, lo, hi, n=8, per=3, rr=0.003, mat="grey", phase=0.5):
        """Bake-only ribs lying exactly on the facets of an n-sided lathe surface, between profile points lo and hi (r, z)."""
        at = V(at)
        for i in range(n):
            a0, a1 = 2 * math.pi * (i + phase) / n, 2 * math.pi * (i + 1 + phase) / n
            for j in range(per):
                f = (j + 0.5) / per; c = math.cos(a0) * (1 - f) + math.cos(a1) * f; sn = math.sin(a0) * (1 - f) + math.sin(a1) * f
                s.b.cyl("d_rib", at + V((c * lo[0], sn * lo[0], lo[1])), at + V((c * hi[0], sn * hi[0], hi[1])), rr, n=5, mat=mat, detail=True, caps=(False, False))

    def saddle(s, p, along, n, r=0.012, mat="galv"):
        """Bake-only conduit saddle clip at p on a surface with normal n, conduit running 'along'."""
        b = s.b; p, a, n = V(p), V(along).normalized(), V(n).normalized(); side = a.cross(n)
        b.cyl("d_saddle", p - a * 0.008 + n * r, p + a * 0.008 + n * r, r + 0.003, n=10, mat=mat, detail=True)
        for sg in (-1, 1): b.bolt(p + side * sg * (r + 0.012), n, r=0.005, h=0.003, mat=mat)


    def plate(s, c, n, up, w=0.05, h=0.03, mats=("grey",), img="decal_plate_a.png"):
        """Maker's plate: a bake-only thin plate with the plate decal on it, two rivets."""
        b = s.b; c, n, up = V(c), V(n).normalized(), V(up).normalized(); r = up.cross(n)
        s.decal(img, c + n * 0.001, n, up, w, h, kind="label", mats=mats, depth=0.01)
        M = b.xf
        for sg in (-1, 1): b.rivet(c + r * sg * (w / 2 - 0.004) + n * 0.0002, n, r=0.0022, mat="stainless")
