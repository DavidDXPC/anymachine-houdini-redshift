# _pw.py: shared helpers for the pipework family (pipe_kit, pipe_rack, cable_tray, storage_tank, separator,
# separator_tower).  Sits on the rig 1 kit (dugout_blender/props_hand/_common/hs.py, only imported).  Adds what that
# kit lacks: placed frames (at), mitred tubes and section sweeps (tube, sweep, bar), steel sections, vessels with
# dished heads, flanges with bolt circles, valves, clamps on shoes, ladders, handrails, the rig 2 paint presets, and
# tail(): finish, stats, unwrap, wear, bake (preview sizes only on this PC), split into pieces, export, review.
import bpy, bmesh, sys, os, json, math, subprocess
import numpy as np
from mathutils import Vector as V, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "dugout_blender", "props_hand", "_common"))
import hs
KT = os.path.join(HERE, "..", "_tex", "out"); kt = lambda n: os.path.join(KT, n)
A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(k, d=None): return A[A.index(k) + 1] if k in A else d
T = Matrix.Translation
PI = math.pi


def new(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    b = hs.Build(name); b.xf = None
    return b


class at:
    """with at(b, M): everything built inside is placed by M (nests)."""
    def __init__(s, b, M): s.b, s.M = b, M
    def __enter__(s):
        s.old = s.b.xf; s.b.xf = s.M if s.old is None else s.old @ s.M
    def __exit__(s, *a): s.b.xf = s.old


def frame(c, z, x=None):
    """Placement: local Z -> z, local X -> x (made square to z), origin -> c.  Always a rotation (no mirror)."""
    z = V(z).normalized()
    if x is None:
        x = z.cross(V((0, 0, 1)))
        if x.length < 1e-4: x = V((1, 0, 0))
    x = V(x); x = (x - z * x.dot(z)).normalized(); y = z.cross(x)
    M = Matrix.Identity(4)
    for i, col in enumerate((x, y, z)):
        for k in range(3): M[k][i] = col[k]
    for k in range(3): M[k][3] = V(c)[k]
    return M


# ------------------------------------------------------------------ sweeps
def tube(b, name, pts, r, n=8, mat="pipe", caps=(False, False), detail=False, plumb=(None, None), phase=0.0, side=None):
    """Round tube along a polyline, mitred joints.  phase 0 puts vertices on the side and up axes, so the bounding
    box of a level pipe is exactly its diameter.  plumb: plane normals for the two end cuts."""
    pts = [V(p) for p in pts]; bm = bmesh.new(); m = len(pts)
    d = [(pts[i + 1] - pts[i]).normalized() for i in range(m - 1)]
    ax = d[0]
    ex = V(side) if side is not None else ax.cross(V((0, 0, 1)))
    if ex.length < 1e-4: ex = V((1, 0, 0))
    ex = (ex - ax * ex.dot(ax)).normalized(); ey = ax.cross(ex)
    u = [(ex * math.cos(2 * PI * (i + phase) / n) + ey * math.sin(2 * PI * (i + phase) / n)) * r for i in range(n)]
    rings = []
    for i in range(m):
        din = d[max(i - 1, 0)]
        if i == 0: t = V(plumb[0]) if plumb[0] else d[0]
        elif i == m - 1: t = V(plumb[1]) if plumb[1] else d[-1]
        else: t = (d[i - 1] + d[i]).normalized()
        q = [uu - din * (uu.dot(t) / din.dot(t)) for uu in u]
        rings.append([bm.verts.new(pts[i] + qq) for qq in q])
        if i < m - 1:
            dn = d[i]; u = [qq - dn * qq.dot(dn) for qq in q]
    for a, c in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((a[i], a[j], c[j], c[i]))
    if caps[0]: bm.faces.new(list(reversed(rings[0])))
    if caps[1]: bm.faces.new(rings[-1])
    hs._quad_caps(bm)
    return b._obj(bm, name, mat, detail)


def arc(c, a, bv, r, a0, a1, k=3):
    """Points on an arc about c in the plane of unit vectors a, bv, from angle a0 to a1 (degrees), k segments."""
    c, a, bv = V(c), V(a), V(bv)
    return [c + (a * math.cos(math.radians(a0 + (a1 - a0) * i / k)) + bv * math.sin(math.radians(a0 + (a1 - a0) * i / k))) * r for i in range(k + 1)]


def route(pts, R, k=3):
    """A pipe centre line through corner points, each corner rounded to bend radius R.  The bend is the polygon
    drawn round the arc (k corners), so every straight leaves square to its end and the tube keeps its true radius."""
    pts = [V(p) for p in pts]; out = [pts[0]]
    def add(q):
        if (q - out[-1]).length > 1e-6: out.append(q)
    for i in range(1, len(pts) - 1):
        p = pts[i]; d0 = (p - pts[i - 1]).normalized(); d1 = (pts[i + 1] - p).normalized()
        ang = d0.angle(d1)
        if ang < 1e-3: continue
        tl = R * math.tan(ang / 2); s = p - d0 * tl; c = s + ((d1 - d0 * d1.dot(d0)).normalized()) * R
        a = (s - c).normalized(); dl = ang / k
        add(s)
        for j in range(k): add(c + (a * math.cos(dl * (j + 0.5)) + d0 * math.sin(dl * (j + 0.5))) * (R / math.cos(dl / 2)))
        add(p + d1 * tl)
    add(pts[-1])
    return out


def sweep(b, name, pts, prof, up=(0, 0, 1), mat="grey", caps=(True, True), detail=False):
    """A closed section [(s, u)] (counter-clockwise; u along 'up', s to the left when looking along the path with up
    on top) swept along a polyline lying square to 'up' (or any single straight segment).  Mitred corners."""
    pts = [V(p) for p in pts]; upv = V(up).normalized(); bm = bmesh.new(); m = len(pts)
    d = [(pts[i + 1] - pts[i]).normalized() for i in range(m - 1)]
    rings = []
    for i in range(m):
        d0 = d[max(i - 1, 0)]; d1 = d[min(i, m - 2)]; t = (d0 + d1).normalized()
        ey = upv - d0 * upv.dot(d0)
        if ey.length < 1e-4: ey = V((0, 1, 0)) - d0 * d0.y
        ey.normalize(); ex0 = ey.cross(d0); ex = ey.cross(t).normalized(); ex = ex / max(ex.dot(ex0), 0.2)
        rings.append([bm.verts.new(pts[i] + ex * s + ey * u_) for s, u_ in prof])
    n = len(prof)
    for a, c in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n; bm.faces.new((a[i], a[j], c[j], c[i]))
    if caps[0]: bm.faces.new(list(reversed(rings[0])))
    if caps[1]: bm.faces.new(rings[-1])
    hs._quad_caps(bm)
    return b._obj(bm, name, mat, detail)


def bar(b, name, p0, p1, prof, up=(0, 0, 1), mat="grey", caps=(True, True), detail=False):
    return sweep(b, name, [p0, p1], prof, up, mat, caps, detail)


# steel sections, counter-clockwise, centred (h along 'up', w across)
def P_box(h, w, o=(0, 0)):
    return [(o[0] - w / 2, o[1] - h / 2), (o[0] + w / 2, o[1] - h / 2), (o[0] + w / 2, o[1] + h / 2), (o[0] - w / 2, o[1] + h / 2)]


def P_I(h, w, tf=0.018, tw=0.012):
    a, c, e, g = w / 2, tw / 2, h / 2, h / 2 - tf
    return [(-a, -e), (a, -e), (a, -g), (c, -g), (c, g), (a, g), (a, e), (-a, e), (-a, g), (-c, g), (-c, -g), (-a, -g)]


def P_H(h, w, tf=0.02, tw=0.014):
    """H column section with the web along 'up' turned on its side: flanges are the s = +-h/2 faces."""
    return [(-u_, s) for s, u_ in P_I(h, w, tf, tw)][::1]


def P_C(h, w, t=0.014):
    """Channel, web on the s = 0 side (the back), flanges pointing to +s."""
    e = h / 2
    return [(0, -e), (w, -e), (w, -e + t), (t, -e + t), (t, e - t), (w, e - t), (w, e), (0, e)]


def P_L(a, t=0.012):
    return [(0, 0), (a, 0), (a, t), (t, t), (t, a), (0, a)]


# ------------------------------------------------------------------ pipe fittings
#          n sides, flange radius, flange thick, hub, bolts, nut radius
PIPE = {0.11: dict(n=8, R=0.115, t=0.022, hub=0.03, nb=8, nr=0.013),
        0.22: dict(n=12, R=0.185, t=0.028, hub=0.04, nb=8, nr=0.017),
        0.40: dict(n=16, R=0.295, t=0.036, hub=0.055, nb=12, nr=0.022)}


def spec(D):
    k = min(PIPE, key=lambda q: abs(q - D)); s = dict(PIPE[k])
    if abs(k - D) > 1e-6:
        f = D / k; s.update(R=s["R"] * f, t=s["t"] * f, hub=s["hub"] * f, nr=s["nr"] * f)
    return s


def bolts(b, R, nb, nr, zs, real=True, mat="steel", h=None, ph=0.5):
    """A bolt circle in the current frame (axis local Z): nuts standing on the planes z in zs = [(z, sign)]."""
    h = h or nr * 0.95
    for i in range(nb):
        a = 2 * PI * (i + ph) / nb; x, y = R * math.cos(a), R * math.sin(a)
        for z, sg in zs:
            if real: b.cyl("nut", (x, y, z), (x, y, z + sg * h), nr, n=6, mat=mat, caps=(False, True))
            else: b.bolt((x, y, z), (0, 0, sg), r=nr, h=min(h, 0.007), mat=mat)


def flange(b, c, ax, D, mat="pipe_t", real=True, pair=True, blind=False, n=None, steel="steel", side=None, sp=None, gap=0.006, low=False):
    """pair: two weld-neck flanges back to back, centred on c, slid over the pipe.  Not pair: one flange with its
    face at c looking along ax (hub behind); blind adds the cover plate on the face.  Returns the half length."""
    s = sp or spec(D); rp = D / 2; R, t, hub = s["R"], s["t"], s["hub"]; n = n or max(12, s["n"])
    rh = rp + (R - rp) * 0.32; g = gap / 2
    with at(b, frame(c, ax, side)):
        if pair:
            if low: prof = [(rp + 0.001, -t - hub), (rh, -t), (R, -t), (R, t), (rh, t), (rp + 0.001, t + hub)]; g = 0
            else: prof = [(rp + 0.001, -t - g - hub), (rh, -t - g), (R, -t - g), (R, -g), (R - 0.012, -g), (R - 0.012, g), (R, g), (R, t + g), (rh, t + g), (rp + 0.001, t + g + hub)]
            b.lathe("flange", prof, n=n, mat=mat, phase=0.0)
            bolts(b, (R + rh) / 2, s["nb"], s["nr"], [(-t - g, -1), (t + g, 1)], real, steel)
            return t + g + hub
        prof = [(rp + 0.001, -t - hub), (rh, -t), (R, -t), (R, 0)]
        if blind: prof += [(R - 0.012, 0), (R - 0.012, gap), (R, gap), (R, gap + t), (0, gap + t)]
        else: prof += [(rp * 0.86, 0)]
        b.lathe("flange", prof, n=n, mat=mat, phase=0.0)
        zs = [(-t, -1)] + ([(gap + t, 1)] if blind else [])
        bolts(b, (R + rh) / 2, s["nb"], s["nr"], zs, real, steel)
        return gap + t if blind else 0


def clamp(b, c, ax, D, n=None, w=None, mat="steel", ears="z", real=True):
    """Stainless two-piece band round a pipe at c, ears with a bolt each side."""
    rp = D / 2; n = n or spec(D)["n"]; w = w or max(0.04, D * 0.22); rb = rp + max(0.008, D * 0.035); e = max(0.03, D * 0.16)
    with at(b, frame(c, ax, (0, 1, 0) if abs(V(ax).normalized().y) < 0.9 else (1, 0, 0))):
        b.lathe("band", [(rp + 0.001, -w / 2), (rb, -w / 2), (rb, w / 2), (rp + 0.001, w / 2)], n=n, mat=mat, phase=0.0)
        for sg in ((-1, 1) if ears else ()):
            x0, x1 = sorted((sg * (rb - 0.004), sg * (rb + e)))
            b.box("ear", (x0, -0.012, -w * 0.4), (x1, 0.012, w * 0.4), mat=mat, skip="+x" if sg < 0 else "-x")
            xm = sg * (rb + e * 0.55); nr = min(0.012, e * 0.3)
            if real:
                b.cyl("nut", (xm, 0.012, 0), (xm, 0.012 + nr, 0), nr, n=6, mat=mat, caps=(False, True))
                b.cyl("nut", (xm, -0.012, 0), (xm, -0.012 - nr, 0), nr, n=6, mat=mat, caps=(False, True))
            else:
                b.bolt((xm, 0.012, 0), (0, 1, 0), r=nr, mat=mat); b.bolt((xm, -0.012, 0), (0, -1, 0), r=nr, mat=mat)
    return rb


def shoe(b, p, D, h, axis="x", mat="grey", steel="steel", plate=True, real=True):
    """Pipe support shoe standing on p (centre of its foot): base plate, post, gussets, cradle plate.  The pipe of
    diameter D runs along 'axis' with its underside at p.z + h."""
    x, y, z = p; w = max(0.07, D * 0.3); L = max(0.16, D * 0.75); pt = 0.012
    M = T(V(p)) if axis == "x" else T(V(p)) @ Matrix.Rotation(PI / 2, 4, "Z")
    with at(b, M):
        if plate:
            b.box("shoe_base", (-L / 2, -L * 0.45, 0), (L / 2, L * 0.45, pt), mat=mat, bev=0.003, skip="-z")
            for sx in (-1, 1):
                for sy in (-1, 1):
                    q = (sx * (L / 2 - 0.025), sy * (L * 0.45 - 0.025), pt)
                    if real: b.cyl("nut", q, (q[0], q[1], pt + 0.012), 0.012, n=6, mat=steel, caps=(False, True))
                    else: b.bolt(q, (0, 0, 1), r=0.011, mat=steel)
        z0 = pt if plate else 0
        b.box("shoe_post", (-w / 2, -w / 2, z0), (w / 2, w / 2, h - 0.01), mat=mat, skip="-z,+z")
        b.box("shoe_cradle", (-L * 0.42, -max(w * 0.9, D * 0.3), h - 0.01), (L * 0.42, max(w * 0.9, D * 0.3), h), mat=mat)
        if h > 0.09:
            g = min(L / 2 - w / 2 - 0.01, h - 0.03)
            for sx in (-1, 1):
                b.prism("shoe_gus", (sx * w / 2, 0, z0), (sx, 0, 0), (0, 0, 1), [(0, 0), (g, 0), (0, min(h - z0 - 0.02, g * 1.4))], -0.005, 0.005, mat=mat + "_t")
    return h


def handwheel(b, c, ax, R, r=None, mat="wheel", n=12, m=5, spokes=2):
    r = r or max(0.008, R * 0.085)
    with at(b, frame(c, ax)):
        b.torus("wheel", (0, 0, 0), R, r, n=n, m=m, mat=mat)
        for i in range(spokes):
            with at(b, Matrix.Rotation(PI * i / spokes, 4, "Z")):
                b.box("spoke", (-R + r * 0.5, -r * 0.8, -r * 0.6), (R - r * 0.5, r * 0.8, r * 0.6), mat=mat, skip="-x,+x")
        b.cyl("hub", (0, 0, -r * 2.5), (0, 0, r * 1.6), R * 0.2, n=8, mat=mat, caps=(False, True))


def valve(b, c, ax, up, D, body="pipe", wheel="wheel", steel="steel", real=True, n=None, low=False):
    """Gate valve between two pipe ends: flanged body, bonnet, yoke, stem and handwheel.  Centre c on the pipe axis,
    run along ax, stem along up.  Returns (half length, top height above the axis)."""
    s = spec(D); rp = D / 2; R, t, hub = s["R"], s["t"], s["hub"]; n = n or max(10, s["n"]); rh = rp + (R - rp) * 0.32
    Lb = D * 0.55 + 0.03; x1 = Lb; x2 = Lb + 2 * t + 0.006; x3 = x2 + hub      # body half, flange outer, hub end
    rb = rp * 1.28
    with at(b, frame(c, ax, up)):          # local Z along the run, local X = up
        prof = [(rp + 0.001, -x3), (rh, -x2), (R, -x2), (R, -x1), (rb * 0.9, -x1), (rb, -x1 * 0.55), (rb, x1 * 0.55), (rb * 0.9, x1), (R, x1), (R, x2), (rh, x2), (rp + 0.001, x3)]
        b.lathe("valve_body", prof, n=n, mat=body, phase=0.0)
        if not low:
            b.lathe("d_gap", [(R + 0.0005, -x1 - t - 0.004), (R + 0.0005, -x1 - t + 0.002)], n=n, mat="dark", detail=True, phase=0.0)
            b.lathe("d_gap", [(R + 0.0005, x1 + t - 0.002), (R + 0.0005, x1 + t + 0.004)], n=n, mat="dark", detail=True, phase=0.0)
        bolts(b, (R + rh) / 2, s["nb"], s["nr"], [(-x2, -1), (x2, 1)], real, steel)
    hb = rb * 0.8; rn = rp * 0.85; zb = rb + D * 0.35; rf = rn + max(0.03, D * 0.2); tb = max(0.016, t * 0.7)
    zt = zb + 2 * tb + D * 0.5; zy = zt + D * 0.75; rw = max(0.075, D * 0.62)
    with at(b, frame(c, up, ax)):          # local Z = up, local X along the run
        nn = max(8, n - 4)
        b.lathe("bonnet", [(rn, hb), (rn, zb), (rf, zb), (rf, zb + 2 * tb), (rn * 0.85, zb + 2 * tb), (rn * 0.55, zt), (rn * 0.55, zt + 0.01), (0, zt + 0.01)], n=nn, mat=body, phase=0.0)
        bolts(b, (rf + rn) / 2 + 0.002, 6 if D < 0.3 else 8, s["nr"] * 0.8, [(zb + 2 * tb, 1)], real, steel)
        yw = rn * 0.5; yt = max(0.012, D * 0.07)
        for sg in (-1, 1):
            x0, x1_ = sorted((sg * (yw - yt), sg * yw))
            b.box("yoke", (x0, -yt * 1.1, zt), (x1_, yt * 1.1, zy), mat=body + "_t", skip="-z,+z")
        b.box("yoke_top", (-yw, -yt * 1.3, zy), (yw, yt * 1.3, zy + yt * 1.6), mat=body + "_t")
        b.cyl("stem", (0, 0, zt), (0, 0, zy + yt * 1.6 + D * 0.42), max(0.008, D * 0.055), n=6, mat=steel, caps=(False, True))
    top = zy + yt * 1.6 + D * 0.3
    handwheel(b, V(c) + V(up).normalized() * top, up, rw, mat=wheel, n=10 if low else 12, m=4 if low else 5)
    return x3, zy + yt * 1.6 + D * 0.42


# ------------------------------------------------------------------ vessels
def head(r, depth, k, z0, sg):
    """Elliptical head profile from the pole (sg = -1, going up to the tangent) or from the tangent to the pole."""
    p = [(r * math.sin(PI / 2 * i / k), z0 + sg * depth * math.cos(PI / 2 * i / k)) for i in range(k + 1)]
    return p if sg < 0 else p[::-1]


def vessel(b, name, c, ax, r, L, depth=None, n=24, mat="white", k=4, side=None, mid=()):
    """Pressure vessel: centre c, axis ax, tangent-to-tangent length L, dished ends of the given depth (default r/2).
    mid: extra ring stations along the shell (fractions) are not needed for shape, so none are made."""
    depth = depth or r * 0.5
    with at(b, frame(c, ax, side)):
        b.lathe(name, head(r, depth, k, -L / 2, -1) + head(r, depth, k, L / 2, 1), n=n, mat=mat, phase=0.0)


def seam(b, c, ax, r, mat="white", side=None, n=32, rr=0.007):
    """Bake-only girth weld round a vessel or pipe."""
    with at(b, frame(c, ax, side)):
        b.torus("d_seam", (0, 0, 0), r + rr * 0.3, rr, n=n, m=6, mat=mat, detail=True, squash=0.6)


def nozzle(b, p, ax, D, L, mat="white", pad=True, blind=False, pair=False, real=True, n=None, steel="steel", fmat=None, embed=0.06, fn=None):
    """A nozzle standing off a shell: p is the point on the shell, ax points out.  Stub of length L to the flange
    face, a reinforcing pad (bake only), a single flange (blind: with its cover) or a flange pair.  Returns the end."""
    p, ax = V(p), V(ax).normalized(); s = spec(D); n = n or max(8, s["n"]); fmat = fmat or mat + "_t"
    tube(b, "noz", [p - ax * embed, p + ax * L], D / 2, n=n, mat=mat)
    if pair:
        hl = flange(b, p + ax * L, ax, D, mat=fmat, real=real, pair=True, n=fn or max(12, n), steel=steel)
        return p + ax * (L + hl)
    e = flange(b, p + ax * L, ax, D, mat=fmat, real=real, pair=False, blind=blind, n=fn or max(12, n), steel=steel)
    return p + ax * (L + e)


def manway(b, p, ax, r, L, mat="white", nb=16, nr=0.02, real=True, n=16, steel="steel", up=(0, 0, 1), handles=True, t=0.035):
    """Bolted manway: neck of radius r standing L off the shell point p, flange ring and cover, hinge, two handles."""
    p, ax = V(p), V(ax).normalized(); R = r + 0.085
    with at(b, frame(p, ax, up)):          # local X = up
        b.lathe("manway", [(r, -0.08), (r, L - t), (R, L - t), (R, L), (R - 0.012, L), (R - 0.012, L + 0.006), (R, L + 0.006), (R, L + 0.006 + t), (0, L + 0.006 + t)], n=n, mat=mat, phase=0.0)
        bolts(b, R - 0.04, nb, nr, [(L + 0.006 + t, 1)], real, steel, ph=0.5)
        zt = L + 0.006 + t
        if handles:
            for sy in (-1, 1):
                y = sy * r * 0.42; hh = r * 0.4
                tube(b, "handle", [(-hh, y, zt - 0.005), (-hh, y, zt + 0.05), (hh, y, zt + 0.05), (hh, y, zt - 0.005)], 0.011, n=4, mat=steel, phase=0.5)
            # hinge: a davit arm on the side
            b.box("hinge", (-0.09, R - 0.01, L - t - 0.06), (0.09, R + 0.06, zt), mat=mat + "_t", skip="-y")
            b.cyl("hinge_pin", (-0.11, R + 0.035, zt - 0.03), (0.11, R + 0.035, zt - 0.03), 0.022, n=6, mat=steel)
    return zt


def saddle(b, c, r, z0, wy, tx_, mat="white", ang=62, k=6, base=0.03, axis="x"):
    """Saddle under a horizontal vessel (axis along X, centre c, radius r): a slab across the vessel standing on z0,
    its top following the shell.  wy: half width at the foot, tx_: thickness along the vessel."""
    cx, cy, cz = c
    a0 = math.radians(ang); ya = r * math.sin(a0); za = cz - r * math.cos(a0)
    out = [(-wy, z0 + base), (wy, z0 + base), (wy, za - 0.02), (ya, za)]
    out += [(r * 0.997 * math.sin(a0 * (1 - 2 * i / k)), cz - r * 0.997 * math.cos(a0 * (1 - 2 * i / k))) for i in range(1, k)]
    out += [(-ya, za), (-wy, za - 0.02)]
    skip = tuple(range(3, 3 + k))
    b.prism("saddle", (cx, cy, 0), (0, 1, 0), (0, 0, 1), out, -tx_ / 2, tx_ / 2, mat=mat, skip_side=skip)
    b.box("saddle_base", (cx - tx_ / 2 - 0.06, cy - wy - 0.06, z0), (cx + tx_ / 2 + 0.06, cy + wy + 0.06, z0 + base), mat=mat, skip="-z")
    return wy + 0.06


def lug(b, name, O, ex, LW, LH, LC, HR, HC, t, mat="white_t", bev=0.0):
    """Lifting eye: a plate with a hole standing on O in the plane of ex and Z, thickness t centred on O."""
    o = [(-LW, 0), (-LW / 2, 0), (0, 0), (LW / 2, 0), (LW, 0), (LW, LH - LC)]
    o += [(LW - LC + LC * 0.707, LH - LC + LC * 0.707), (LW - LC, LH), (-LW + LC, LH), (-LW + LC - LC * 0.707, LH - LC + LC * 0.707)]
    o += [(-LW, LH - LC), (-LW, (LH - LC) * 0.5)]
    inner = [(HR * math.cos(math.radians(a)), HC + HR * math.sin(math.radians(a))) for a in (-135, -112.5, -90, -67.5, -45, 0, 45, 67.5, 112.5, 135, 180, 202.5)]
    b.ring_plate(name, O, ex, (0, 0, 1), o, inner, -t / 2, t / 2, mat=mat, skip_outer=(0, 1, 2, 3), bev=bev)


# ------------------------------------------------------------------ access steel
def ladder(b, p, h, normal=(0, -1, 0), w=0.45, mat="yellow_t", rung=0.3, standoff=0.0, cage=None):
    """Vertical ladder: foot centre p, height h, climbing face looks along normal (the structure is behind it).
    standoff: bracket length back to the structure (every ~2.4 m).  cage: (z0, z1) heights above the foot between
    which safety hoops and five vertical straps are built."""
    nrm = V(normal).normalized(); side = V((0, 0, 1)).cross(nrm)
    with at(b, frame(p, (0, 0, 1), side)):          # local X = side, local +Y = towards the structure
        for sx in (-1, 1):
            x0, x1 = sorted((sx * w / 2, sx * (w / 2 + 0.012)))
            b.box("ladder_side", (x0, -0.03, 0), (x1, 0.03, h), mat=mat, skip="-z")
        k = int((h - 0.25) / rung)
        for i in range(k + 1):
            z = 0.25 + i * rung
            if z > h - 0.05: break
            b.box("rung", (-w / 2, -0.012, z - 0.012), (w / 2, 0.012, z + 0.012), mat=mat, skip="-x,+x")
        if standoff > 0:
            nbk = max(2, int(h / 2.4) + 1)
            for i in range(nbk):
                z = 0.4 + (h - 0.8) * i / (nbk - 1)
                for sx in (-1, 1):
                    xc = sx * (w / 2 + 0.006)
                    b.box("ladder_brk", (xc - 0.006, 0.03, z - 0.025), (xc + 0.006, 0.03 + standoff, z + 0.025), mat=mat, skip="-y,+y")
        if cage:
            z0, z1 = cage; R = 0.36; cy = -(R - 0.06); nh = max(2, int((z1 - z0) / 0.9) + 1); K = 6
            for i in range(nh):
                z = z0 + (z1 - z0) * i / (nh - 1)
                pts = [(R * math.cos(math.radians(140 + 260 * j / K)), cy + R * math.sin(math.radians(140 + 260 * j / K)), z) for j in range(K + 1)]
                sweep(b, "hoop", pts, P_box(0.05, 0.008), up=(0, 0, 1), mat=mat, caps=(True, True))
            for a in (180, 225, 270, 315, 360):
                ar = math.radians(a)
                with at(b, T(V(((R - 0.008) * math.cos(ar), cy + (R - 0.008) * math.sin(ar), 0))) @ Matrix.Rotation(ar + PI / 2, 4, "Z")):
                    b.box("cage_bar", (-0.02, -0.004, z0), (0.02, 0.004, z1), mat=mat, skip="-z,+z")


def handrail(b, p0, p1, h=1.1, mat="yellow_t", toe=0.1, ends=(True, True), bay=1.5, knee=True, r=0.022, inset=0.0, toe_mat=None):
    """Rail along p0 -> p1 (level): posts at most 'bay' apart (ends: whether the end posts are built), top rail, knee
    rail and toe board.  The toe board sits on the side the path's left normal points away from (outer edge)."""
    p0, p1 = V(p0), V(p1); L = (p1 - p0).length; d = (p1 - p0) / L; nb = max(1, math.ceil(L / bay - 1e-6))
    for i in range(nb + 1):
        if (i == 0 and not ends[0]) or (i == nb and not ends[1]): continue
        q = p0 + d * (L * i / nb)
        b.box("rail_post", (q.x - 0.02, q.y - 0.02, q.z), (q.x + 0.02, q.y + 0.02, q.z + h - r), mat=mat, skip="-z,+z")
    tube(b, "rail_top", [p0 + V((0, 0, h - r)), p1 + V((0, 0, h - r))], r, n=5, mat=mat, caps=(True, True), phase=0.25)
    for kz in ((0.5,) if knee is True else (0.36, 0.68) if knee == 2 else ()):      # knee=2: two mid rails
        tube(b, "rail_knee", [p0 + V((0, 0, h * kz)), p1 + V((0, 0, h * kz))], r * 0.8, n=3, mat=mat, phase=0.25)
    if toe:
        sweep(b, "toe", [p0, p1], P_box(toe, 0.008, (0, toe / 2)), mat=toe_mat or mat, caps=(False, False))


def plate_bolts(b, O, ex, ey, pts, r=0.014, real=True, mat="steel", h=None, ns=6):
    """Bolt heads on a plate: O + ex*u + ey*v for (u, v) in pts, standing along ex x ey."""
    O, ex, ey = V(O), V(ex).normalized(), V(ey).normalized(); n = ex.cross(ey); h = h or r * 0.9
    for u, v in pts:
        q = O + ex * u + ey * v
        if real: b.cyl("bolt", q, q + n * h, r, n=ns, mat=mat, caps=(False, True))
        else: b.bolt(q, n, r=r, mat=mat)


# ------------------------------------------------------------------ paint
def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


OWM = (0.76, 0.71, 0.61)          # mean of paint_offwhite.png, linear


def tn(r, g, b_):
    return tuple(min(1.5, lin(v) / m) for v, m in zip((r, g, b_), OWM))


def presets():
    RS = kt("rust_steel.png"); OC = kt("paint_ochre.png"); OW = kt("paint_offwhite.png"); GV = kt("steel_galv.png")
    DB = kt("paint_darkblue.png"); DA = kt("deck_antislip.png")
    B = dict(tile=1.3, edge=0.45, bias=-0.02, rust=0.3, dirt=0.4, low=0.3)
    def ow(rgb, **kw):
        d = dict(B); d.update(tint=tn(*rgb)); d.update(kw); return (OW, d, rgb)
    return dict(
        white=(OW, dict(B, tile=2.2, sat=0.25, value=0.62, rust=0.2, dirt=0.3, tint=(0.97, 1.0, 1.02)), (180, 183, 182)),
        pipe=(OW, dict(B, low=0.0, sat=0.3, value=0.95, top=0.1), (224, 222, 216)),
        green=ow((52, 96, 74)), blue=ow((48, 84, 132)), red=ow((142, 52, 46)),
        grey=ow((104, 116, 126), edge=0.25, bias=-0.06), lgrey=ow((146, 152, 154), tile=2.0, rust=0.15, dirt=0.3, edge=0.22, bias=-0.07, low=0.15), orange=ow((205, 92, 38)), wheel=ow((176, 40, 36)),
        glass=ow((58, 92, 86), edge=0.0, rust=0.0, rough=0.2), black=ow((34, 34, 36), edge=0.1, rust=0.0), cred=ow((150, 48, 42), edge=0.1, rust=0.0), cblue=ow((44, 78, 136), edge=0.1, rust=0.0),
        yellow=(OC, dict(B, tile=1.0, sat=0.9, value=0.82), (214, 168, 34)),
        dblue=(DB, dict(B, tile=1.7, sat=0.8, value=0.9, tint=(0.75, 0.92, 0.9), edge=0.25, bias=-0.06, rust=0.2), (44, 66, 96)),
        steel=(GV, dict(tile=0.5, metal=0.8, rough=0.42, edge=0.25, bias=-0.08, rust=0.35, dirt=0.3, chip_metal=0.1, value=0.95, low=0.15), (176, 178, 180)),
        galv=(GV, dict(tile=0.6, metal=0.6, rough=0.55, edge=0.25, bias=-0.08, rust=0.4, dirt=0.35, chip_metal=0.1, value=0.85, low=0.2), (150, 153, 156)),
        grate=(GV, dict(tile=0.6, metal=0.3, rough=0.7, edge=0.15, bias=-0.1, rust=0.3, dirt=0.6, chip_metal=0.1, value=0.5, low=0.0, top=0.0), (92, 96, 100)),
        deck=(DA, dict(tile=1.0, edge=0.2, bias=-0.1, rust=0.3, dirt=0.5, value=0.8), (70, 80, 92)),
        dark=(RS, dict(tile=0.9, value=0.1, edge=0.0, bias=-0.5, rust=0.0, dirt=1.0, rough=0.9, low=0.0, top=0.0), (18, 18, 18)),
    )


def paints(b, over=None):
    """Fill every material the build used.  A name ending _t is the thin-part version of its base (less edge wear:
    the inside-occlusion edge mask reads thin parts as all edge).  over: {name: {changes}} or {name: (base, {changes})}."""
    P = presets(); RS = kt("rust_steel.png"); pal = {}
    for name in list(b.matdb):
        base = name[:-2] if name.endswith("_t") else name
        o = (over or {}).get(name) or (over or {}).get(base)
        if isinstance(o, tuple): base, o = o
        sheet, kw, rgb = P[base]; kw = dict(kw)
        if name.endswith("_t"): kw.update(edge=kw.get("edge", 0.45) * 0.55, bias=kw.get("bias", 0) - 0.03)
        if o: kw.update(o)
        b.wear(name, sheet, RS, **kw); pal[name] = [round(lin(v), 4) for v in rgb]
    return pal


# ------------------------------------------------------------------ finish
def bbox(o):
    co = np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]); return co.min(0), co.max(0)


def tail(b, here, ref=None, pieces=None, size=2048, uv_scale=None, over=None, tintable=(), review=None, margin=0.004, weld=0.0002):
    """finish, stats, unwrap, wear, preview bake (never the full one on this PC unless asked), split, export, review.
    ref: (min, max) the whole model must fill.  pieces: [(name, bake offset, ref_min, ref_max)] in tag order 1..n:
    built apart (at(b, T(offset))) so they do not shade each other, split and moved home after the bake.
    tintable: materials whose faces get _TINT = 1 (vertex attribute, exported): the game multiplies its colour there."""
    lo, hi = b.finish(weld=weld)
    if tintable:
        me = lo.data; ta = me.attributes.new("_TINT", "FLOAT", "POINT"); vals = np.zeros(len(me.vertices), np.float32)
        for p in me.polygons:
            if me.materials[p.material_index].name[len(b.name) + 1:] in tintable: vals[list(p.vertices)] = 1.0
        ta.data.foreach_set("value", vals)
    st = b.stats(*ref) if ref else b.stats()
    dm = {"dark": 0.3}; dm.update(uv_scale or {})
    st.update(b.unwrap(margin=margin, uv_scale=dm))
    pal = paints(b, over)
    baked = "--nobake" not in A
    if baked:
        sz = int(arg("--size", size)); b.bake(here, size=sz, samples=int(arg("--spp", 24))); st["texture"] = sz
    else: st["texture"] = 0
    st["texture_target"] = size
    if pieces:
        objs = b.split([p[0] for p in pieces]); st["pieces"] = {}
        for o, p in zip(objs, pieces):
            o.data.transform(T(-V(p[1]))); o.data.update(); mn, mx = bbox(o); o.data.calc_loop_triangles()
            d = dict(tris=len(o.data.loop_triangles), min=[round(float(v), 4) for v in mn], max=[round(float(v), 4) for v in mx])
            if p[2] is not None:
                d["bbox_err_mm"] = round(float(max(np.abs(mn - np.array(p[2])).max(), np.abs(mx - np.array(p[3])).max())) * 1000, 2)
            st["pieces"][p[0]] = d
        st["tris"] = sum(d["tris"] for d in st["pieces"].values())
        st["bbox_err_mm"] = max([d.get("bbox_err_mm", 0) for d in st["pieces"].values()])
        sel = objs
    else:
        sel = [lo]
    json.dump(st, open(os.path.join(here, "stats.json"), "w"), indent=1); print("STATS", json.dumps(st))
    bpy.ops.object.select_all(action="DESELECT")
    for o in sel: o.select_set(True)
    bpy.context.view_layer.objects.active = sel[0]
    kw = dict(filepath=os.path.join(here, b.name + ".glb"), export_format="GLB", use_selection=True, export_tangents=True, export_apply=True, export_yup=True)
    try: bpy.ops.export_scene.gltf(export_attributes=bool(tintable), **kw)
    except TypeError: bpy.ops.export_scene.gltf(**kw)
    for im in bpy.data.images:
        if im.filepath_raw and os.path.exists(bpy.path.abspath(im.filepath_raw)):
            try: im.filepath = bpy.path.relpath(im.filepath_raw, start=here)
            except Exception: pass
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(here, b.name + ".blend"))
    cfg = dict(id=b.name, baked=baked, palette=pal, tintable=list(tintable))
    cfg.update(review or {})
    json.dump(cfg, open(os.path.join(here, "_review.json"), "w"), indent=1)
    if "--noreview" not in A:
        subprocess.run([bpy.app.binary_path, "-b", "--factory-startup", "-t", "4", "--python", os.path.join(HERE, "_review.py"), "--", here], stdout=subprocess.DEVNULL)
    return st
