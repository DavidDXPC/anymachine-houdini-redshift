import math
from . import pipework as pw
from .pipework import V, T, at, frame, Matrix
RZ = lambda a: Matrix.Rotation(math.radians(a), 4, "Z")
RX = lambda a: Matrix.Rotation(math.radians(a), 4, "X")
RY = lambda a: Matrix.Rotation(math.radians(a), 4, "Y")

new = pw.new


def quad(b, name, O, ex, ey, w, h, mat, detail=False, lift=0.0):
    """One rectangle: corner O, edges ex*w and ey*h, facing ex x ey."""
    n = V(ex).normalized().cross(V(ey).normalized())
    with at(b, frame(V(O) + n * lift, n, ex)):
        return b.box(name, (0, 0, -0.01), (w, h, 0), mat=mat, skip="-x,+x,-y,+y,-z", detail=detail)


def mesh_panel(b, O, ex, ey, w, h, backs=(), mesh="galv_t", void="void", lw=0.09, sw=0.045, bw=0.008, lo=True, lift=0.0):
    """An opaque expanded-mesh panel.  Game mesh: one quad (material 'void', dark).  Bake source: diamond mesh strands
    3 mm proud, and 'backs' [(u0, u1, v0, v1, material)]: flat patches 1 mm proud that stand for what is seen through
    the mesh (cylinders, a drum).  Players cannot see through it: it is cover."""
    n = V(ex).normalized().cross(V(ey).normalized())
    if lo: quad(b, "mesh_panel", O, ex, ey, w, h, void, lift=lift)
    with at(b, frame(V(O) + n * lift, n, ex)):
        for u0, u1, v0, v1, m in backs:
            b.box("d_back", (u0, v0, 0.0002), (u1, v1, 0.001), mat=m, skip="-z", detail=True)
        k = sw / lw
        for s in (-1, 1):
            c = -k * w if s > 0 else 0.0
            c = math.floor(c / sw) * sw + (sw / 2 if s > 0 else 0)
            while c < h + k * w + sw:
                # line v = c + s*k*u for u in [0, w], clipped to v in [0, h]
                u0, u1 = 0.0, w
                if s > 0:
                    u0 = max(u0, (0 - c) / k); u1 = min(u1, (h - c) / k)
                else:
                    u0 = max(u0, (c - h) / k); u1 = min(u1, c / k)
                if u1 - u0 > 0.02:
                    p0 = (u0, c + s * k * u0, 0); L = (u1 - u0) * math.hypot(1, k)
                    with at(b, T(V(p0)) @ Matrix.Rotation(math.atan2(s * k, 1), 4, "Z")):
                        b.box("d_strand", (0, -bw / 2, 0.0005), (L, bw / 2, 0.0035), mat=mesh, skip="-z,-x,+x", detail=True)
                c += sw


def grid_panel(b, O, ex, ey, w, h, pitch=0.05, bw=0.008, mesh="galv_t", void="void", lo=True, backs=(), lift=0.0):
    """As mesh_panel, with a square welded-wire grid."""
    n = V(ex).normalized().cross(V(ey).normalized())
    if lo: quad(b, "grid_panel", O, ex, ey, w, h, void, lift=lift)
    with at(b, frame(V(O) + n * lift, n, ex)):
        for u0, u1, v0, v1, m in backs:
            b.box("d_back", (u0, v0, 0.0002), (u1, v1, 0.001), mat=m, skip="-z", detail=True)
        nu = max(1, round(w / pitch)); nv = max(1, round(h / pitch))
        for i in range(1, nu):
            u = w * i / nu; b.box("d_wire", (u - bw / 2, 0, 0.0005), (u + bw / 2, h, 0.0035), mat=mesh, skip="-z,-y,+y", detail=True)
        for j in range(1, nv):
            v = h * j / nv; b.box("d_wire", (0, v - bw / 2, 0.0005), (w, v + bw / 2, 0.0035), mat=mesh, skip="-z,-x,+x", detail=True)


SEG = dict(a=(0, 2, 1, 0), b=(1, 1, 0, 1), c=(1, 0, 0, 1), d=(0, 0, 1, 0), e=(0, 0, 0, 1), f=(0, 1, 0, 1), g=(0, 1, 1, 0))
DIG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g",
       "A": "abcefg", "C": "adef", "E": "adefg", "F": "aefg", "H": "bcefg", "L": "def", "P": "abefg", "U": "bcdef", " ": ""}


def stencil(b, text, O, ex, ey, h, mat="paintw", gap=0.3):
    """Stencil-cut figures (seven strokes with bridges, like a cut stencil), bake only, 1 mm of paint on the surface.
    O: lower-left of the text on the surface, ex along the text, ey up.  Returns the width."""
    n = V(ex).normalized().cross(V(ey).normalized()); cw = h * 0.5; t = h * 0.15; step = cw * (1 + gap); br = t * 0.35
    with at(b, frame(O, n, ex)):
        for i, ch in enumerate(text):
            x0 = i * step
            for s in DIG.get(ch, ""):
                cx, cy, dx, dy = SEG[s]; hh = (h - t) / 2
                if dx:   # horizontal stroke at height cy*hh
                    y = cy * hh; b.box("d_sten", (x0 + br + t * 0.5, y, 0.0002), (x0 + cw - br - t * 0.5, y + t, 0.001), mat=mat, skip="-z", detail=True)
                else:    # vertical stroke on column cx, half cy
                    x = x0 + cx * (cw - t); y = cy * hh; b.box("d_sten", (x, y + br + t * 0.5, 0.0002), (x + t, y + hh + t * 0.5 - br, 0.001), mat=mat, skip="-z", detail=True)
    return len(text) * step - cw * gap


def run(b, top, n, w, h, mats, i=2, strength=0.45):
    """A grime run hanging down from the point 'top' on an upright face with normal n."""
    c = V(top) - V((0, 0, h / 2))
    b.decal("sn_%02d.png" % i, c, n, (0, 0, 1), w, h, kind="stain", mats=tuple(mats), depth=0.25, strength=strength)


def puddle(b, c, w, mats, i=5, strength=0.5):
    """A stain on a level face (oil under a pump, a ring under a drum)."""

    b.decal("st_%02d.png" % i,c,(0,0,1),(0,1,0),w,kind="stain",mats=mats,strength=strength)
