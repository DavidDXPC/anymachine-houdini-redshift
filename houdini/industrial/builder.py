"""Connected mesh construction shared by the original part-by-part recipes."""
import math
import random
from .geometry import Mesh, Part, Vector, box_mesh

V = Vector


class Build:
    def __init__(self, name):
        self.name, self.tag, self.xf = name, 0, None
        self.lo, self.hi, self.decals = [], [], []
        self.rng = random.Random(7)

    def _obj(self, mesh, name, mat, detail=False, xf=None):
        part = Part(mesh, name, mat, self.tag, self.xf if xf is None else xf)
        (self.hi if detail else self.lo).append(part)
        return part

    def box(self, name, mn, mx, mat="paint", bev=0.0, skip="", detail=False, seg=1,
            flip=False, xf=None, bev_axes=None, bev_all=False):
        mesh = box_mesh(mn, mx, bev, skip, bev_axes, bev_all, flip)
        return self._obj(mesh, name, mat, detail, xf)

    def cyl(self, name, p0, p1, r, n=8, mat="paint", caps=(True,True),
            detail=False, r1=None, bev=0., phase=.5):
        p0, p1 = V(p0), V(p1)
        axis = (p1-p0).normalized()
        ex = (axis.cross(V((0,0,1))) if abs(axis.z)<.9 else axis.orthogonal()).normalized()
        ey = axis.cross(ex)
        r1 = r if r1 is None else r1
        width = min(bev,r*.49,r1*.49,(p1-p0).length*.49)
        levels = []
        if width and caps[0]:
            levels.extend(((p0, r-width),(p0+axis*width,r)))
        else:
            levels.append((p0,r))
        if width and caps[1]:
            levels.extend(((p1-axis*width,r1),(p1,r1-width)))
        else:
            levels.append((p1,r1))
        mesh = Mesh()
        angles = [2*math.pi*(i+phase)/n for i in range(n)]
        directions = [ex*math.cos(a)+ey*math.sin(a) for a in angles]
        rings = [[mesh.verts.new(p+d*radius) for d in directions] for p,radius in levels]
        for a,b in zip(rings,rings[1:]):
            for i in range(n):
                j=(i+1)%n
                mesh.faces.new((a[i],a[j],b[j],b[i]))
        if caps[0]: mesh.faces.new(reversed(rings[0]))
        if caps[1]: mesh.faces.new(rings[-1])
        return self._obj(mesh,name,mat,detail)

    def decal(self, image, center, normal, up, w, h=None, **settings):
        # Projection metadata is independent of the geometry and material binding.
        self.decals.append((image,center,normal,up,w,h,settings))


    def lathe(s, name, profile, n=12, mat="paint", at=(0, 0, 0), detail=False, cap_top=False, cap_bot=False, phase=0.5):
        """Profile [(r, z), ...] going up the outside, spun round Z.  r = 0 at an end closes it with a fan."""
        bm = Mesh(); at = V(at); rings = []
        for r, z in profile:
            if r <= 1e-6: rings.append([bm.verts.new(at + V((0, 0, z)))])
            else: rings.append([bm.verts.new(at + V((r * math.cos(2 * math.pi * (i + phase) / n), r * math.sin(2 * math.pi * (i + phase) / n), z))) for i in range(n)])
        for a, b_ in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n
                if len(a) == 1 and len(b_) == 1: continue
                if len(a) == 1: bm.faces.new((a[0], b_[j], b_[i]))
                elif len(b_) == 1: bm.faces.new((a[i], a[j], b_[0]))
                else: bm.faces.new((a[i], a[j], b_[j], b_[i]))
        if cap_bot and len(rings[0]) > 1: bm.faces.new(list(reversed(rings[0])))
        if cap_top and len(rings[-1]) > 1: bm.faces.new(rings[-1])

        return s._obj(bm, name, mat, detail)

    def torus(s, name, c, R, r, n=14, m=6, mat="paint", detail=False, squash=1.0):
        prof = [(R - r * math.cos(2 * math.pi * k / m), -r * squash * math.sin(2 * math.pi * k / m)) for k in range(m + 1)]
        o = s.lathe(name, prof, n=n, mat=mat, at=c, detail=detail)
        return o

    def ring_plate(s, name, O, ex, ey, outer, inner, t0, t1, mat="paint", detail=False, skip_outer=(), bev=0.0, back=True, wall=True):
        """A plate with a hole: outer and inner outlines of equal count (counter-clockwise in ex,ey), all quads."""
        O, ex, ey = V(O), V(ex), V(ey); ez = ex.cross(ey); bm = Mesh(); N = len(outer)
        P = lambda p, t: O + ex * p[0] + ey * p[1] + ez * t
        vo0 = [bm.verts.new(P(p, t0)) for p in outer]; vo1 = [bm.verts.new(P(p, t1)) for p in outer]
        vi0 = [bm.verts.new(P(p, t0)) for p in inner]; vi1 = [bm.verts.new(P(p, t1)) for p in inner]
        for i in range(N):
            j = (i + 1) % N
            bm.faces.new((vo1[i], vo1[j], vi1[j], vi1[i]))
            if back: bm.faces.new((vo0[j], vo0[i], vi0[i], vi0[j]))
            if i not in skip_outer: bm.faces.new((vo0[i], vo0[j], vo1[j], vo1[i]))
            if wall: bm.faces.new((vi0[j], vi0[i], vi1[i], vi1[j]))
        return s._obj(bm, name, mat, detail)

    def strip(s, name, O, U, eV, eN, profile, mat="paint", detail=False, closed=False, fix=True):
        """A cross-section polyline [(v, n), ...] swept along U (a vector with length).  Normal points to +eN."""
        O, U, eV, eN = V(O), V(U), V(eV), V(eN); bm = Mesh()
        a = [bm.verts.new(O + eV * p[0] + eN * p[1]) for p in profile]
        b = [bm.verts.new(O + U + eV * p[0] + eN * p[1]) for p in profile]
        n = len(profile)
        for i in range(n if closed else n - 1):
            j = (i + 1) % n; bm.faces.new((a[i], b[i], b[j], a[j]))

        # orient: first face normal should have a positive eN part, unless the profile is closed
        if fix and not closed and sum(f.normal.dot(eN) for f in bm.faces) < 0:
            for f in bm.faces: f.normal_flip()
        return s._obj(bm, name, mat, detail)

    def prism(s, name, O, ex, ey, outline, t0, t1, mat="paint", detail=False, caps=(True, True), bev=0.0, skip_side=()):
        """A convex outline (counter-clockwise in ex,ey) extruded along ex x ey from t0 to t1."""
        O, ex, ey = V(O), V(ex), V(ey); ez = ex.cross(ey); bm = Mesh(); N = len(outline)
        a = [bm.verts.new(O + ex * p[0] + ey * p[1] + ez * t0) for p in outline]
        b = [bm.verts.new(O + ex * p[0] + ey * p[1] + ez * t1) for p in outline]
        for i in range(N):
            if i in skip_side: continue
            j = (i + 1) % N; bm.faces.new((a[i], a[j], b[j], b[i]))
        if caps[0]: bm.faces.new(list(reversed(a)))
        if caps[1]: bm.faces.new(b)
        return s._obj(bm, name, mat, detail)

    # ---------------------------------------------------------------- bake-only detail
    def bolt(s, p, n, r=0.011, h=0.006, mat="steel", hexa=True):
        p, n = V(p), V(n).normalized()
        s.cyl("d_bolt", p - n * 0.001, p + n * h, r, n=6 if hexa else 12, mat=mat, caps=(False, True), detail=True, bev=r * 0.18)
        s.cyl("d_washer", p - n * 0.001, p + n * 0.0018, r * 1.45, n=14, mat=mat, caps=(False, True), detail=True)

    def rivet(s, p, n, r=0.007, mat="paint"):
        p, n = V(p), V(n).normalized()
        s.cyl("d_rivet", p - n * 0.001, p + n * r * 0.45, r, n=10, mat=mat, caps=(False, True), detail=True, r1=r * 0.55, )

    def weld(s, p0, p1, r=0.0035, mat="paint", step=0.012):
        """A lumpy weld bead lying on a joint."""
        p0, p1 = V(p0), V(p1); L = (p1 - p0).length; ax = (p1 - p0) / L
        ex = ax.orthogonal().normalized(); ey = ax.cross(ex); bm = Mesh(); k = max(2, int(L / step)); rings = []
        for i in range(k + 1):
            rr = r * (0.75 + 0.5 * s.rng.random()); c = p0 + ax * (L * i / k)
            rings.append([bm.verts.new(c + (ex * math.cos(a * math.pi / 3) + ey * math.sin(a * math.pi / 3)) * rr) for a in range(6)])
        for i in range(k):
            for a in range(6):
                b = (a + 1) % 6; bm.faces.new((rings[i][a], rings[i][b], rings[i + 1][b], rings[i + 1][a]))
        return s._obj(bm, "d_weld", mat, True)
