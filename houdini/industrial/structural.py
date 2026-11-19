import math
from .geometry import Vector as V, Matrix, Mesh
from .builder import Build
Z = V((0,0,1))
start = Build

def rect(w, h):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def isec(w, h, tf, tw):
    a, c, d = w / 2, h / 2, tw / 2
    return [(-a, -c), (a, -c), (a, -c + tf), (d, -c + tf), (d, c - tf), (a, c - tf), (a, c), (-a, c), (-a, c - tf), (-d, c - tf), (-d, -c + tf), (-a, -c + tf)]


def lsec(w, t):          # flat leg centred on the line with its outer face on it, second leg pointing to -e2
    a = w / 2
    return [(-a, 0), (-a, -w), (-a + t, -w), (-a + t, -t), (a, -t), (a, 0)]


def sect(b, name, p0, p1, outline, e1, mat="paint", caps=(False, False), ext=(0, 0)):
    """A member: outline swept from p0 to p1.  e1 is the section's first axis (made square to the member);
    the second is axis x e1."""
    p0, p1 = V(p0), V(p1); ax = p1 - p0; L = ax.length; ax = ax / L
    e1 = V(e1); e1 = (e1 - ax * e1.dot(ax)).normalized(); e2 = ax.cross(e1)
    return b.prism(name, p0, e1, e2, outline, -ext[0], L + ext[1], mat=mat, caps=caps)


def angle(b, name, p0, p1, w, t, n_out, mat="paint", caps=(False, False), ext=(0, 0)):
    """Angle section lying on a truss face whose outward normal is n_out: one leg flat in the face, one pointing in."""
    p0, p1 = V(p0), V(p1); ax = (p1 - p0).normalized(); n = V(n_out); n = (n - ax * n.dot(ax)).normalized()
    return sect(b, name, p0, p1, lsec(w, t), n.cross(ax), mat, caps, ext)


def tube(b, name, p0, p1, r, n=6, mat="paint", caps=(False, False), r1=None):
    return b.cyl(name, V(p0), V(p1), r, n=n, mat=mat, caps=caps, r1=r1)


def plate(b, name, c, n, e1, w, h, t=0.016, mat="paint", lift=0.0):
    """A flat plate lying on a surface at c (normal n): front and edges, no back."""
    c, n = V(c), V(n).normalized()
    return sect(b, name, c + n * lift, c + n * (lift + t), rect(w, h), e1, mat, caps=(False, True))


# ------------------------------------------------------------------ railings and ladders
def rail_run(b, pts, h=1.1, mat="yel", bay=1.5, toe=0.1, r=0.022, n=5, closed=False, name="rail", mid=True, skip_first_post=False):
    """Tube handrail along a polyline of deck-level points: top and mid rail, posts, toe board."""
    pts = [V(p) for p in pts]; segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
    for si, (a, c) in enumerate(segs):
        d = c - a; L = d.length; u = d / L
        for hh in ((h, h * 0.5) if mid else (h,)):
            tube(b, name, a + Z * hh - u * r, c + Z * hh + u * r, r, n, mat)
        if toe:
            side = V((-u.y, u.x, 0)).normalized()
            sect(b, name + "_toe", a + Z * toe / 2, c + Z * toe / 2, rect(0.03, toe), side, mat)
        k = max(1, math.ceil(L / bay - 1e-6))
        for j in range(k + 1):
            if j == 0 and (si > 0 or (closed and False) or skip_first_post): continue
            if closed and si == len(segs) - 1 and j == k: continue
            p = a + d * j / k
            tube(b, name + "_post", p, p + Z * h, r, n, mat)


def ladder(b, p0, p1, out, w=0.45, mat="galv", cage_mat="yel", cage_from=2.3, rung=0.3, hoop=0.9, cage_r=0.36, name="ladder", cage_to=None):
    """Ladder from p0 up to p1 (centre line), climbing side towards 'out'.  Cage of hoops and straps from cage_from."""
    p0, p1 = V(p0), V(p1); ax = p1 - p0; L = ax.length; ax = ax / L
    out = V(out); out = (out - ax * out.dot(ax)).normalized(); s = ax.cross(out)
    for sg in (-1, 1):
        sect(b, name + "_str", p0 + s * sg * w / 2, p1 + s * sg * w / 2, rect(0.015, 0.06), s, mat, caps=(False, True))
    for i in range(1, int(L / rung)):
        c = p0 + ax * i * rung
        sect(b, name + "_rung", c - s * w / 2, c + s * w / 2, rect(0.022, 0.022), ax, mat)
    if cage_from is None or cage_from >= L: return
    angs = [math.radians(a) for a in (-140, -100, -60, -20, 20, 60, 100, 140)]
    ring = lambda c, rr: [c + out * (0.30 + rr * math.cos(a)) + s * (rr * math.sin(a)) for a in angs]
    Lc = min(L, cage_to or L); k = max(1, round((Lc - cage_from) / hoop)); bm = Mesh()
    for i in range(k + 1):
        c = p0 + ax * (cage_from + (Lc - cage_from) * i / k)
        for rr, fl in ((cage_r, False), (cage_r - 0.006, True)):
            lo = [bm.verts.new(p - ax * 0.025) for p in ring(c, rr)]; hi = [bm.verts.new(p + ax * 0.025) for p in ring(c, rr)]
            for j in range(len(angs) - 1):
                f = (lo[j], lo[j + 1], hi[j + 1], hi[j]); bm.faces.new(tuple(reversed(f)) if fl else f)
    b._obj(bm, name + "_hoop", cage_mat)
    c0, c1 = p0 + ax * cage_from, p0 + ax * Lc
    for a in (-100, -20, 20, 100):          # vertical straps inside the hoops
        a = math.radians(a); o = out * (0.30 + (cage_r - 0.009) * math.cos(a)) + s * ((cage_r - 0.009) * math.sin(a))
        rad = (out * math.cos(a) + s * math.sin(a))
        sect(b, name + "_strap", c0 + o, c1 + o, rect(0.006, 0.04), rad, cage_mat)


def oplate(b, name, c, n, e1, outline, t=0.016, mat="paint", lift=0.0):
    """A plate of any convex outline (in e1, n x e1 ... see sect) lying on a surface at c."""
    c, n = V(c), V(n).normalized()
    return sect(b, name, c + n * lift, c + n * (lift + t), outline, e1, mat, caps=(False, True))


def bolts(b, pts, n, r=0.02, h=0.016, mat="paint", real=False):
    """Bolt heads at pts, standing along n.  real: six-sided heads in the game mesh; otherwise bake-only."""
    n = V(n).normalized()
    for p in pts:
        p = V(p)
        if real: b.cyl("bolt", p, p + n * h, r, n=6, mat=mat, caps=(False, True))
        else: b.bolt(p, n, r=r, h=h, mat=mat)


def grid(c, e1, e2, nx, ny, dx, dy):
    c, e1, e2 = V(c), V(e1).normalized(), V(e2).normalized()
    return [c + e1 * ((i - (nx - 1) / 2) * dx) + e2 * ((j - (ny - 1) / 2) * dy) for i in range(nx) for j in range(ny)]


def grid_plate(b, name, O, ex, ey, xs, ys, t, holes=(), warp=None, mat="paint"):
    """A plate cut from a grid: cells (i, j) listed in holes are left open (windows, slots, clipped corners).
    warp(x, y) -> (x, y) reshapes the outline.  Front, back and every wall, all quads."""
    O, ex, ey = V(O), V(ex).normalized(), V(ey).normalized(); ez = ex.cross(ey); bm = Mesh(); nx, ny = len(xs), len(ys)
    holes = set(holes); solid = lambda i, j: 0 <= i < nx - 1 and 0 <= j < ny - 1 and (i, j) not in holes
    F, B = {}, {}
    def vert(D, i, j, s):
        if (i, j) not in D:
            x, y = (warp(xs[i], ys[j]) if warp else (xs[i], ys[j])); D[(i, j)] = bm.verts.new(O + ex * x + ey * y + ez * (s * t / 2))
        return D[(i, j)]
    for i in range(nx - 1):
        for j in range(ny - 1):
            if not solid(i, j): continue
            c = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            bm.faces.new([vert(F, *p, 1) for p in c]); bm.faces.new([vert(B, *p, -1) for p in reversed(c)])
            for k, nb in enumerate(((i, j - 1), (i + 1, j), (i, j + 1), (i - 1, j))):
                if solid(*nb): continue
                p, q = c[k], c[(k + 1) % 4]
                bm.faces.new((vert(B, *p, -1), vert(B, *q, -1), vert(F, *q, 1), vert(F, *p, 1)))
    return b._obj(bm, name, mat)


def spun(b, name, c, axis, profile, n=14, mat="paint", detail=False, torus=None):
    """hs.lathe (or a torus (R, r)) about any axis through c: profile [(radius, distance along the axis)]."""
    q = Z.rotation_difference(V(axis).normalized()).to_matrix().to_4x4(); old = getattr(b, "xf", None)
    b.xf = Matrix.Translation(V(c)) @ q
    o = b.torus(name, (0, 0, 0), torus[0], torus[1], n=n, m=6, mat=mat, detail=detail) if torus else b.lathe(name, profile, n=n, mat=mat, detail=detail)
    b.xf = old; return o


def sheave(b, c, axis, r, w=0.09, mat="dark", n=14, name="sheave", groove=0.045, hub=None):
    """A rope sheave: grooved rim, dished web, hub boss."""
    hub = hub or r * 0.3; a = w / 2
    prof = [(0, -a * 1.25), (hub, -a * 1.25), (hub, -a * 0.55), (r - 0.07, -a * 0.55), (r - 0.05, -a), (r, -a), (r, -a * 0.5), (r - groove, 0),
            (r, a * 0.5), (r, a), (r - 0.05, a), (r - 0.07, a * 0.55), (hub, a * 0.55), (hub, a * 1.25), (0, a * 1.25)]
    return spun(b, name, c, axis, prof, n=n, mat=mat)


def sweep(b, name, pts, radii, side, n=8, mat="paint", caps=(True, True)):
    """A bar of changing oval section along a curve.  radii [(in the plane of the curve, along 'side')]."""
    pts = [V(p) for p in pts]; side = V(side).normalized(); bm = Mesh(); rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized(); en = side.cross(t).normalized(); ra, rb = radii[i]
        rings.append([bm.verts.new(p + en * (ra * math.cos(2 * math.pi * k / n)) + side * (rb * math.sin(2 * math.pi * k / n))) for k in range(n)])
    for a, c in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n; bm.faces.new((a[k], a[j], c[j], c[k]))
    if caps[0]: bm.faces.new(list(reversed(rings[0])))
    if caps[1]: bm.faces.new(rings[-1])

    return b._obj(bm, name, mat)


def flange(b, c, axis, r, t, nb, rb, mat="paint", bolt_mat="galv", n=12, bolt_r=0.02, both=True, real=True, name="flange"):
    """A flange pair on a tube joint at c: two discs and a bolt circle (heads one side, nuts the other)."""
    c, axis = V(c), V(axis).normalized(); e1 = axis.orthogonal().normalized(); e2 = axis.cross(e1)
    for sg in ((-1, 1) if both else (1,)):
        b.cyl(name, c + axis * sg * 0.003, c + axis * sg * (0.003 + t), r, n=n, mat=mat, caps=(True, True))
        bolts(b, [c + (e1 * math.cos(2 * math.pi * (k + 0.5) / nb) + e2 * math.sin(2 * math.pi * (k + 0.5) / nb)) * rb + axis * sg * (0.003 + t) for k in range(nb)],
              axis * sg, r=bolt_r, h=bolt_r * 0.9, mat=bolt_mat, real=real)
