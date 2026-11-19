import numpy as np
import math
from contextlib import contextmanager
from . import builder as hs, structural as lm
from .geometry import Vector, Matrix, Mesh
V = Vector
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
I4 = Matrix.Identity(4); MIR = Matrix.Scale(-1, 4, (0, 1, 0))

# ------------------------------------------------------------------ transforms
@contextmanager
def at(m, *builds):
    """Parts built inside are placed by matrix m (composed with any outer placement)."""
    old = [getattr(b, "xf", None) for b in builds]
    for b, o in zip(builds, old): b.xf = (o if o is not None else I4) @ m
    try: yield
    finally:
        for b, o in zip(builds, old): b.xf = o


def both(*builds):
    """for sg in both(B, M): ...  runs the body twice; the second pass is mirrored to the right-hand side (-Y)."""
    yield 1
    marks = [(len(b.lo), len(b.hi)) for b in builds]; old = [getattr(b, "xf", None) for b in builds]
    for b, o in zip(builds, old): b.xf = (o if o is not None else I4) @ MIR
    yield -1
    for b, (nl, nh), o in zip(builds, marks, old):
        for ob in b.lo[nl:] + b.hi[nh:]: ob.flip_normals()
        b.xf = o


def rot(axis, deg): return Matrix.Rotation(math.radians(deg), 4, axis)
def tr(*p): return Matrix.Translation(V(p[0]) if len(p) == 1 else V(p))


def frame(o, ex, ez):
    """Matrix placing local X on ex and local Z on ez (made square), origin o."""
    ex = V(ex).normalized(); ez = V(ez); ez = (ez - ex * ez.dot(ex)).normalized(); ey = ez.cross(ex)
    m = Matrix.Identity(4)
    for i, c in enumerate((ex, ey, ez)):
        for k in range(3): m[k][i] = c[k]
    for k in range(3): m[k][3] = V(o)[k]
    return m


def fz(o, n, hint=(1, 0, 0)):
    """Matrix with local Z exactly on n and local X as near to 'hint' as it can be, origin o (parts on a surface)."""
    ez = V(n).normalized(); ex = V(hint); ex = (ex - ez * ex.dot(ez)).normalized(); ey = ez.cross(ex)
    m = Matrix.Identity(4)
    for i, c in enumerate((ex, ey, ez)):
        for k in range(3): m[k][i] = c[k]
    for k in range(3): m[k][3] = V(o)[k]
    return m


# ------------------------------------------------------------------ interpolation
def pchip(xs, ys, x):
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    if xs[0] > xs[-1]: xs, ys = xs[::-1], ys[::-1]
    h = np.diff(xs); d = np.diff(ys) / h; m = np.zeros_like(ys); m[0], m[-1] = d[0], d[-1]
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]; m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    x = min(max(x, xs[0]), xs[-1]); i = int(min(max(np.searchsorted(xs, x) - 1, 0), len(xs) - 2))
    t = (x - xs[i]) / h[i]; t2, t3 = t * t, t * t * t
    return float((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])


# ------------------------------------------------------------------ generic surfaces
def ringloft(b, name, rings, mat, caps=(True, True), detail=False):
    """Closed rings of equal count lofted in order; normals made outward.  All quads (caps re-quadded)."""
    bm = Mesh(); R = [[bm.verts.new(V(p)) for p in r] for r in rings]; n = len(R[0])
    for a, c in zip(R, R[1:]):
        for k in range(n):
            j = (k + 1) % n; bm.faces.new((a[k], a[j], c[j], c[k]))
    if caps[0]: bm.faces.new(list(reversed(R[0])))
    if caps[1]: bm.faces.new(R[-1])
    bm.orient_outward()

    return b._obj(bm, name, mat, detail)


def gridsurf(b, name, grid, mat, inside, detail=False):
    """An open quad grid; faces are turned to look away from the point 'inside'."""
    bm = Mesh(); G = [[bm.verts.new(V(p)) for p in r] for r in grid]
    for a, c in zip(G, G[1:]):
        for k in range(len(a) - 1): bm.faces.new((a[k], a[k + 1], c[k + 1], c[k]))
    f = bm.faces[len(bm.faces) // 2]
    if f.normal.dot(f.calc_center_median() - V(inside)) < 0:
        for q in bm.faces: q.normal_flip()
    return b._obj(bm, name, mat, detail)


AF = [(0.0, 0.0), (0.05, 0.6), (0.28, 1.0), (0.64, 0.74), (1.0, 0.06)]
def wing(b, name, secs, mat, caps=(True, True), detail=False):
    """An aerofoil surface through sections [(leading edge, trailing edge, thickness, thickness direction)]."""
    rings = []
    for le, te, th, nrm in secs:
        le, te, nrm = V(le), V(te), V(nrm).normalized(); c = te - le
        up = [le + c * f + nrm * (th / 2 * g) for f, g in AF]; lo = [le + c * f - nrm * (th / 2 * g) for f, g in AF[1:]]
        rings.append(up + list(reversed(lo)))
    return ringloft(b, name, rings, mat, caps, detail)


def spun(b, name, c, axis, profile, n=14, mat="paint", detail=False, sx=1.0, e1=None):
    """Profile [(radius, distance along the axis)] spun about any axis through c.  sx stretches it along e1 (ovals)."""
    axis = V(axis).normalized(); q = Z.rotation_difference(axis).to_matrix().to_4x4()
    if e1 is not None: q = frame((0, 0, 0), e1, axis)
    with at(tr(c) @ q @ Matrix.Diagonal((sx, 1, 1, 1)), b):
        return b.lathe(name, profile, n=n, mat=mat, detail=detail)


def pipe(b, name, p0, p1, r, wall=0.006, n=14, mat="steel", inner="dark"):
    """An open-ended tube with a visible bore: outside and rim on mat, the bore on 'inner'."""
    p0, p1 = V(p0), V(p1); L = (p1 - p0).length
    spun(b, name, p0, p1 - p0, [(r, 0), (r, L), (r - wall, L)], n=n, mat=mat)
    spun(b, name + "_bore", p0, p1 - p0, [(r - wall, L), (r - wall, L * 0.25), (0, L * 0.25)], n=n, mat=inner)


def rod(b, name, p0, p1, r, mat="steel", n=6, ends=0.0, caps=(True, True)):
    """A link rod, optionally with rod-end eyes (short fat cylinders across the ends)."""
    b.cyl(name, V(p0), V(p1), r, n=n, mat=mat, caps=caps)
    if ends:
        ax = (V(p1) - V(p0)).normalized(); s = ax.orthogonal().normalized()
        for p in (V(p0), V(p1)): b.cyl(name + "_eye", p - s * ends * 0.6, p + s * ends * 0.6, ends, n=8, mat=mat)


def path(b, name, pts, w, t, side, mat, n=4):
    """A strap (n=4, flat) or rope (n=6, round) along a polyline."""
    return lm.sweep(b, name, pts, [(t, w)] * len(pts), side, n=n, mat=mat)


def sag(p0, p1, drop, k=7):
    p0, p1 = V(p0), V(p1)
    return [p0 + (p1 - p0) * (i / k) - Z * (drop * 4 * (i / k) * (1 - i / k)) for i in range(k + 1)]


def rivets(b, pn, r=0.005, mat="white"):
    """Bake-only dome rivets at [(point, normal)], one object."""
    if not pn: return
    bm = Mesh()
    for p, n in pn:
        n = V(n).normalized(); ex = n.orthogonal().normalized(); ey = n.cross(ex)
        base = [bm.verts.new(V(p) - n * 0.0008 + (ex * math.cos(k * math.pi / 3) + ey * math.sin(k * math.pi / 3)) * r) for k in range(6)]
        top = bm.verts.new(V(p) + n * r * 0.45)
        for k in range(6): bm.faces.new((base[k], base[(k + 1) % 6], top))
    return b._obj(bm, "d_rivets", mat, True)


def line_pts(p0, p1, step):
    p0, p1 = V(p0), V(p1); k = max(1, round((p1 - p0).length / step))
    return [p0 + (p1 - p0) * ((i + 0.5) / k) for i in range(k)]


# ------------------------------------------------------------------ fuselage: lofted skin with openings
#        belt x   belly  top    half-w  n-bot n-top shear (top leans aft when negative)
KEYS = [(4.30, 1.00, 1.24, 0.10, 2.0, 2.0, 0.0),
        (4.22, 0.87, 1.36, 0.31, 2.0, 2.0, 0.0),
        (4.05, 0.74, 1.47, 0.53, 2.2, 2.1, 0.0),
        (3.85, 0.66, 1.53, 0.70, 2.4, 2.2, -0.03),
        (3.62, 0.61, 1.57, 0.84, 2.7, 2.3, -0.10),
        (3.50, 0.59, 1.60, 0.90, 2.8, 2.4, -0.16),
        (3.28, 0.57, 1.84, 0.98, 3.0, 2.5, -0.30),
        (3.05, 0.55, 2.06, 1.05, 3.3, 2.7, -0.40),
        (2.82, 0.55, 2.24, 1.09, 3.6, 2.9, -0.44),
        (2.60, 0.55, 2.36, 1.12, 3.8, 3.2, -0.44),
        (2.44, 0.55, 2.41, 1.12, 3.9, 3.4, -0.42),
        (1.64, 0.55, 2.45, 1.12, 4.0, 3.6, 0.0),
        (-1.60, 0.55, 2.45, 1.12, 4.0, 3.6, 0.0),
        (-2.20, 0.61, 2.43, 1.05, 3.6, 3.4, 0.0),
        (-2.80, 0.84, 2.40, 0.85, 3.0, 3.0, 0.0),
        (-3.40, 1.16, 2.36, 0.58, 2.5, 2.5, 0.0),
        (-4.00, 1.47, 2.33, 0.39, 2.1, 2.1, 0.0),
        (-4.60, 1.65, 2.33, 0.31, 2.0, 2.0, 0.0),
        (-6.80, 1.99, 2.47, 0.20, 2.0, 2.0, 0.0)]
ST = [4.30, 4.22, 4.05, 3.85, 3.62, 3.50, 3.28, 3.05, 2.82, 2.60, 2.44, 2.428, 2.36, 2.28, 1.80, 1.72, 1.64, 1.628,
      1.55, 1.538, 1.42, 1.34, 0.72, 0.64, 0.46, 0.38, -0.24, -0.32, -0.45, -0.462, -0.70, -0.77, -1.13, -1.20,
      -1.60, -1.90, -2.20, -2.50, -2.80, -3.10, -3.40, -3.70, -4.00, -4.50, -5.00, -5.50, -6.00, -6.40, -6.80]
ROWS = [("y", 0.0, 0), ("y", 0.45, 0), ("y", 0.80, 0), ("z", 0.70), ("z", 0.775), ("z", 0.787), ("z", 1.02), ("z", 1.30), ("z", 1.37),
        ("z", 1.93), ("z", 2.00), ("z", 2.12), ("z", 2.132), ("y", 1.0, 1), ("y", 0.8, 1), ("y", 0.5, 1), ("y", 0.25, 1), ("post",), ("y", 0.0, 1)]
RN = dict(sill=4, floor=5, belt=6, wb=7, wt=10, top=11, post=17)       # row indices by name
WIN = [(2.36, 1.72), (1.42, 0.64), (0.46, -0.32), (-0.70, -1.20)]      # side windows (belt x of front and rear edge)
DOORS = [(2.44, 1.64), (1.55, -0.45)]                                  # door outlines: gap starts at these stations
LINER = (3.62, -1.60)                                                  # the lined cabin


class Fus:
    def __init__(s):
        s.K = np.array(KEYS); s.si = lambda x: min(range(len(ST)), key=lambda i: abs(ST[i] - x))
        zb, zt, w, nb, nt, k = s.par(0.0); zm, h = (zb + zt) / 2, (zt - zb) / 2; s.th = []
        for r in ROWS:
            if r[0] == "y":
                if r[1] == 0: s.th.append(math.pi if r[2] else 0.0); continue
                t = math.asin((r[1] / w) ** ((nt if r[2] else nb) / 2)); s.th.append(math.pi - t if r[2] else t)
            elif r[0] == "z":
                u = (r[1] - zm) / h; c = abs(u) ** ((nt if u > 0 else nb) / 2); s.th.append(math.pi - math.acos(c) if u > 0 else math.acos(c))
            else: s.th.append(None)
        assert all(a < b for a, b in zip([t for t in s.th if t is not None], [t for t in s.th if t is not None][1:])), s.th

    def par(s, x): return [pchip(s.K[:, 0], s.K[:, c], x) for c in range(1, 7)]

    def pt(s, x, th):
        zb, zt, w, nb, nt, k = s.par(x); zm, h = (zb + zt) / 2, (zt - zb) / 2; c, sn = math.cos(th), max(0.0, math.sin(th))
        e = 2 / (nb if c > 0 else nt); z = zm - h * (1 if c > 0 else -1) * abs(c) ** e
        return V((x + k * (z - 1.3), w * sn ** e, z))

    def row_th(s, x, j):
        if s.th[j] is not None: return s.th[j]
        zb, zt, w, nb, nt, k = s.par(x); t = math.pi - math.asin(min(0.9, 0.045 / w) ** (nt / 2))
        return t if t > s.th[j - 1] + 0.02 else (s.th[j - 1] + math.pi) / 2


    def th_z(s, x, z):
        """Ring angle at station x where the skin is at height z."""
        zb, zt, w, nb, nt, k = s.par(x); zm, h = (zb + zt) / 2, (zt - zb) / 2; u = max(-1, min(1, (z - zm) / h))
        c = abs(u) ** ((nt if u > 0 else nb) / 2); return math.pi - math.acos(c) if u > 0 else math.acos(c)

    def pn(s, x, th, sg=1):
        """Point and outward normal on the skin (sg -1: right-hand side)."""
        p = s.pt(x, th); a = s.pt(x - 2e-3, th) - s.pt(x + 2e-3, th); c = s.pt(x, min(math.pi, th + 2e-3)) - s.pt(x, max(0, th - 2e-3))
        n = a.cross(c).normalized()
        return (p, n) if sg > 0 else (V((p.x, -p.y, p.z)), V((n.x, -n.y, n.z)))

    def side(s, x, z, sg=1): return s.pn(x, s.th_z(x, z), sg)
    def top(s, x): return s.pt(x, math.pi)

    def kind(s, i, j):
        si = s.si
        if si(3.50) <= i < si(2.60) and RN["wb"] <= j < RN["post"]:                                   # windscreen pane, sill rising to the nose
            lo = RN["wb"] + (2 if i < si(3.28) else 1 if i < si(3.05) else 0)
            return "hole" if j >= lo else "c00" if j == lo - 1 else "skin"
        if si(3.62) <= i < si(3.05) and RN["floor"] <= j < RN["belt"]: return "hole"                 # chin window
        for a, c in WIN:
            ia, ic = si(a), si(c)
            if ia <= i < ic and RN["wb"] <= j < RN["wt"]:
                e = (i == ia, i == ic - 1, j == RN["wb"], j == RN["wt"] - 1)
                if (e[0] or e[1]) and (e[2] or e[3]): return "c" + ("0" if e[0] else "1") + ("0" if e[2] else "1")
                return "hole"
        for a, c in DOORS:
            ia, ic = si(a), si(c)
            if (i in (ia, ic) and RN["sill"] <= j <= RN["top"]) or (j in (RN["sill"], RN["top"]) and ia <= i <= ic): return "gap"
        return "skin"

    def build(s, B, I, mat="white", gap=0.012, liner=0.04):
        """Outer skin, door-gap grooves and window reveals on B; cabin liner, floor and bulkheads on I.
        Returns the glass polygons (lists of points) for the window object."""
        NS, M = len(ST), len(ROWS) - 1
        P = [[s.pt(x, s.row_th(x, j)) for j in range(M + 1)] for x in ST]
        N = [[None] * (M + 1) for _ in ST]
        for i in range(NS):
            for j in range(M + 1):
                a = P[min(i + 1, NS - 1)][j] - P[max(i - 1, 0)][j]; c = P[i][min(j + 1, M)] - P[i][max(j - 1, 0)]
                n = a.cross(c); N[i][j] = n.normalized() if n.length > 1e-9 else V((1, 0, 0))
            N[i][0] = V((N[i][0].x, 0, N[i][0].z)).normalized(); N[i][M] = V((N[i][M].x, 0, N[i][M].z)).normalized()
        s.P, s.N = P, N
        Q = [[P[i][j] - N[i][j] * gap for j in range(M + 1)] for i in range(NS)]
        L = [[P[i][j] - N[i][j] * liner for j in range(M + 1)] for i in range(NS)]
        GL = [[P[i][j] - N[i][j] * 0.014 for j in range(M + 1)] for i in range(NS)]
        iL0, iL1, jf = s.si(LINER[0]), s.si(LINER[1]), RN["floor"]
        bs, bg, br, bl = Mesh(), Mesh(), Mesh(), Mesh(); glass = []
        def mk(bm, cache, arr, tag):
            def v(i, j, sg):
                key = (tag, i, j, sg if 0 < j < M else 1)
                if key not in cache:
                    p = arr[i][j]; cache[key] = bm.verts.new((p.x, p.y * sg if 0 < j < M else 0.0, p.z))
                return cache[key]
            return v
        cs, cg, cr, cl = {}, {}, {}, {}
        vP, vQ, vQP = mk(bs, cs, P, "P"), mk(bg, cg, Q, "Q"), mk(bg, cg, P, "P")
        vRP, vRL, vL = mk(br, cr, P, "P"), mk(br, cr, L, "L"), mk(bl, cl, L, "L")
        def face(bm, vs, sg):
            vs = [v for k, v in enumerate(vs) if v not in vs[:k]]
            if len(vs) >= 3:
                try: bm.faces.new(vs if sg > 0 else list(reversed(vs)))
                except ValueError: pass
        def kd(i, j): return s.kind(i, j) if 0 <= i < NS - 1 and 0 <= j < M else "skin"
        TRI = {"c00": ((0, 1, 3), (1, 2, 3)), "c01": ((0, 2, 3), (0, 1, 2)), "c10": ((0, 1, 2), (0, 2, 3)), "c11": ((1, 2, 3), (0, 1, 3))}
        for sg in (1, -1):
            for i in range(NS - 1):
                for j in range(M):
                    k = kd(i, j); q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]; nb = [(i, j - 1), (i + 1, j), (i, j + 1), (i - 1, j)]
                    lined = iL0 <= i < iL1 and j >= jf
                    holes = []
                    if k == "skin":
                        face(bs, [vP(*p, sg) for p in q], sg)
                        if lined: face(bl, [vL(*p, sg) for p in q], -sg)
                    elif k == "gap":
                        face(bg, [vQ(*p, sg) for p in q], sg)
                        for e in range(4):
                            if kd(*nb[e]) != "gap":
                                a, c = q[e], q[(e + 1) % 4]; face(bg, [vQP(*a, sg), vQP(*c, sg), vQ(*c, sg), vQ(*a, sg)], sg)
                        if lined: face(bl, [vL(*p, sg) for p in q], -sg)
                    elif k == "hole": holes.append(q)
                    else:
                        t_skin, t_hole = TRI[k]
                        face(bs, [vP(*q[t], sg) for t in t_skin], sg)
                        if lined: face(bl, [vL(*q[t], sg) for t in t_skin], -sg)
                        holes.append([q[t] for t in t_hole])
                        a, c = [q[t] for t in t_hole if t in t_skin]      # the diagonal is an opening edge
                        ih = [q[t] for t in t_hole]; ia = ih.index(a)
                        if ih[(ia + 1) % 3] != c: a, c = c, a
                        face(br, [vRP(*a, sg), vRP(*c, sg), vRL(*c, sg), vRL(*a, sg)], sg)
                    for hp in holes:
                        glass.append([V((GL[a][c].x, GL[a][c].y * sg, GL[a][c].z)) for a, c in (hp if sg > 0 else reversed(hp))])
                        if len(hp) == 4:
                            for e in range(4):
                                if kd(*nb[e]) in ("skin", "gap"):
                                    a, c = hp[e], hp[(e + 1) % 4]; face(br, [vRP(*a, sg), vRP(*c, sg), vRL(*c, sg), vRL(*a, sg)], sg)
        # nose and tail closed with fans
        for (i, flip) in ((0, 1), (NS - 1, -1)):
            c = bs.verts.new(sum((P[i][j] for j in (0, M)), V()) / 2 + X * (0.03 * flip))
            for sg in (1, -1):
                for j in range(M): face(bs, [c, vP(i, j + 1, sg), vP(i, j, sg)], sg * flip)
        # cabin floor and the two bulkheads of the liner
        for i in range(iL0, iL1): face(bl, [vL(i, jf, 1), vL(i + 1, jf, 1), vL(i + 1, jf, -1), vL(i, jf, -1)], 1)
        for (i, want) in ((iL0, -1), (iL1, 1)):
            ring = [vL(i, j, 1) for j in range(jf, M + 1)] + [vL(i, j, -1) for j in range(M - 1, jf - 1, -1)]
            f = bl.faces.new(ring)
            if f.normal.x * want < 0: f.normal_flip()

        B._obj(bs, "fuselage", mat); B._obj(bg, "door_gaps", "seal"); B._obj(br, "window_reveals", "seal"); I._obj(bl, "liner", "liner")
        return glass

    def skin_rivets(s, B, frames, stringers, step=0.045, mat="white"):
        """Bake-only rivet rows along station rings (frames) and along rows (stringers), skipping openings."""
        NS, M = len(ST), len(ROWS) - 1; P, N = s.P, s.N; out = []
        ok = lambda i, j: s.kind(i, j) == "skin" if 0 <= i < NS - 1 and 0 <= j < M else False
        def run(a, na, c, nc):
            k = max(1, round((c - a).length / step))
            for t in range(k):
                f = (t + 0.5) / k; p = a.lerp(c, f); n = na.lerp(nc, f)
                for sg in (1, -1): out.append((V((p.x, p.y * sg, p.z)), V((n.x, n.y * sg, n.z))))
        for x in frames:
            i = s.si(x)
            for j in range(M):
                if ok(i, j) and ok(i - 1, j): run(P[i][j], N[i][j], P[i][j + 1], N[i][j + 1])
        for j, (x0, x1) in stringers:
            for i in range(s.si(x0), s.si(x1)):
                if ok(i, j) and ok(i, j - 1): run(P[i][j], N[i][j], P[i + 1][j], N[i + 1][j])
        rivets(B, out, r=0.0045, mat=mat)
