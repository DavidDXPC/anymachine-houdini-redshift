import math
from .geometry import Vector as V, Matrix, Mesh
from .builder import Build
from . import structural as lm, builder as hs
from .structural import Z, sect, rect, tube
Vector = V
def F(o, ex, ey):
    """Frame matrix: origin o, local x and y (made orthonormal), z = x cross y."""
    ex = V(ex).normalized(); ey = V(ey); ey = (ey - ex * ey.dot(ex)).normalized(); ez = ex.cross(ey)
    m = Matrix.Identity(4)
    for i, c in enumerate((ex, ey, ez)):
        for k in range(3): m[k][i] = c[k]
    for k in range(3): m[k][3] = V(o)[k]
    return m


def obox(b, name, M, mn, mx, mat="paint", bev=0.0, skip="", detail=False, bev_axes=None):
    """hs box in the local frame M."""
    return b.box(name, mn, mx, mat=mat, bev=bev, skip=skip, detail=detail, xf=M, bev_axes=bev_axes)


def polytube(b, name, pts, r, n=6, mat="paint", caps=(True, True)):
    """One tube through a polyline with mitred joints (no overlapping ends)."""
    pts = [V(p) for p in pts]; bm = Mesh(); rings = []
    t0 = (pts[1] - pts[0]).normalized(); e1 = t0.orthogonal().normalized()
    if abs(t0.z) < 0.9: e1 = t0.cross(Z).normalized()
    for i, p in enumerate(pts):
        tin = (p - pts[i - 1]).normalized() if i > 0 else (pts[1] - p).normalized()
        tout = (pts[i + 1] - p).normalized() if i < len(pts) - 1 else tin
        if i > 0:                       # carry the section along without twisting
            q = pts[i - 1] - pts[i - 2] if i > 1 else tin
            e1 = (e1 - tin * e1.dot(tin)).normalized()
        tb = (tin + tout).normalized(); e2 = tin.cross(e1).normalized(); ring = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n; off = (e1 * math.cos(a) + e2 * math.sin(a)) * r
            d = tb.dot(tin); off = off - tin * (off.dot(tb) / d) if abs(d) > 1e-4 else off      # project onto the mitre plane
            ring.append(bm.verts.new(p + off))
        rings.append(ring)
    for a_, c_ in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n; bm.faces.new((a_[k], a_[j], c_[j], c_[k]))
    if caps[0]: bm.faces.new(list(reversed(rings[0])))
    if caps[1]: bm.faces.new(rings[-1])

    return b._obj(bm, name, mat)

class Grating:
    def __init__(self, build):
        self.build = build

    def quad(self, a, b, c, d):
        a,b,c,d = map(V,(a,b,c,d))
        for u,v in ((b-a,d-a),(d-a,b-a)):
            n = max(1, round(v.length/0.045))
            for i in range(n):
                p = a + v*(i+0.5)/n
                sect(self.build, "grate_bar", p, p+u, rect(.004,.012), v.normalized(), "galv", caps=(True,True))


# 5 x 7 stencil glyphs used by the survival craft.
GLYPHS = {
    "L":(16,16,16,16,16,16,31), "I":(31,4,4,4,4,4,31),
    "F":(31,16,16,30,16,16,16), "E":(31,16,16,30,16,16,31),
    "B":(30,17,17,30,17,17,30), "O":(14,17,17,17,17,17,14),
    "A":(14,17,17,31,17,17,17), "T":(31,4,4,4,4,4,4),
    "C":(15,16,16,16,16,16,15), "P":(30,17,17,30,16,16,16),
    "Y":(17,17,10,4,4,4,4), "2":(14,17,1,2,4,8,31),
    "6":(14,16,16,30,17,17,14), "R":(30,17,17,30,20,18,17),
    "S":(15,16,16,14,1,1,30), "N":(17,25,25,21,19,19,17),
    " ":(0,)*7,
}


def text(b, label, o, ex, ey, height, mat="stencil", lift=.0012, spacing=1.05):
    mesh = Mesh()
    dx,dy = height/7, height/7
    x0 = -dx*(len(label)*6*spacing-1)/2
    for i, char in enumerate(label):
        for row, bits in enumerate(GLYPHS[char]):
            for col in range(5):
                if bits & (16 >> col):
                    x,y = x0+dx*(i*6*spacing+col), height/2-dy*(row+1)
                    mesh.faces.new([mesh.verts.new((x+u*dx,y+v*dy,lift)) for u,v in ((0,0),(1,0),(1,1),(0,1))])
    return b._obj(mesh,"label_"+label.lower().replace(" ","_"),mat,True,xf=F(o,ex,ey))
