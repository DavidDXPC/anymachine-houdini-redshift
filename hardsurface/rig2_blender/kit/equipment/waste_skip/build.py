# waste_skip: open-top offshore waste skip.  3.6 (X) x 1.8 (Y) x 1.4 (Z), origin centre of the footprint on the floor.
# Hand-modelled from sheets/waste_skip_turn.png / _detail.png.
#   tapered steel body (floor 2.6 x 1.32, top 3.48 x 1.68) with pressed vertical ribs, a box-section top rim, two skids
#   with fork pockets over a closed core, four lifting lugs with shackles (their tops are the top of the box), a green
#   tarpaulin lashed over the -X half, a four-leg wire sling lying slack with its red master link on the tarpaulin,
#   stencilled number 74036 (invented) on all four sides.
#   blender -b --factory-startup -t 4 --python build.py [-- --nobake] [--size 2048] [--spp 24] [--noreview]
import sys, os, math
import bmesh
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import _eq as eq
from _eq import pw, V, T, at, frame
from mathutils import Matrix
b = eq.new("waste_skip")
HX, HY, H = 1.8, 0.9, 1.4
ZF, ZW, ZR0, ZR1 = 0.12, 1.15, 1.13, 1.23          # floor, wall top, rim underside, rim top
BX, BY, TX, TY = 1.3, 0.66, 1.74, 0.84            # floor and wall-top half sizes
XT = -0.1                                         # the tarpaulin covers x < XT
B, BT = "dblue", "dblue_t"


def mesh(name, verts, faces, mat, detail=False):
    bm = bmesh.new(); vs = [bm.verts.new(v) for v in verts]
    for f in faces: bm.faces.new([vs[i] for i in f])
    return b._obj(bm, name, mat, detail)


# stencil figures drawn as strokes (the family's seven-stroke figures read too coarse at this size), bake only
GLY = {"7": [[(0, 1), (1, 1), (0.35, 0)]], "4": [[(0.78, 0), (0.78, 1), (0, 0.32), (1, 0.32)]],
       "0": [[(0.25, 0), (0.75, 0), (1, 0.18), (1, 0.82), (0.75, 1), (0.25, 1), (0, 0.82), (0, 0.18), (0.25, 0)]],
       "3": [[(0, 1), (0.75, 1), (1, 0.84), (1, 0.66), (0.75, 0.52), (0.3, 0.52)], [(0.75, 0.52), (1, 0.38), (1, 0.16), (0.75, 0), (0, 0)]],
       "6": [[(1, 1), (0.25, 1), (0, 0.82), (0, 0.18), (0.25, 0), (0.75, 0), (1, 0.18), (1, 0.4), (0.75, 0.56), (0, 0.56)]]}


def sten(text, u0, v0, h, mat="paintw"):
    """In the current wall frame: lower-left (u0, v0), figure height h.  Long strokes get a stencil bridge."""
    cw = h * 0.58; t = h * 0.15; step = cw * 1.32
    for i, ch in enumerate(text):
        for line in GLY[ch]:
            P = [V((u0 + i * step + t / 2 + x * (cw - t), v0 + t / 2 + y * (h - t), 0)) for x, y in line]
            for p, q in zip(P, P[1:]):
                L = (q - p).length; a = math.atan2(q.y - p.y, q.x - p.x)
                parts = [(-t / 2, L + t / 2)] if L < 0.55 * h else [(-t / 2, L / 2 - t * 0.22), (L / 2 + t * 0.22, L + t / 2)]
                with at(b, T(p) @ Matrix.Rotation(a, 4, "Z")):
                    for s0, s1 in parts: b.box("d_sten", (s0, -t / 2, 0.0002), (s1, t / 2, 0.001), mat=mat, skip="-z", detail=True)
    return len(text) * step


# ---------------- body: outer shell, inner lining and floor
o = [(-BX, -BY, ZF), (BX, -BY, ZF), (BX, BY, ZF), (-BX, BY, ZF), (-TX, -TY, ZW), (TX, -TY, ZW), (TX, TY, ZW), (-TX, TY, ZW)]
mesh("shell", o, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0)], B)
d = 0.012; zi = ZF + 0.02
i_ = [(-BX + d, -BY + d, zi), (BX - d, -BY + d, zi), (BX - d, BY - d, zi), (-BX + d, BY - d, zi), (-TX + d, -TY + d, ZR1 - 0.01), (TX - d, -TY + d, ZR1 - 0.01), (TX - d, TY - d, ZR1 - 0.01), (-TX + d, TY - d, ZR1 - 0.01)]
mesh("lining", i_, [(1, 0, 4, 5), (2, 1, 5, 6), (3, 2, 6, 7), (0, 3, 7, 4), (0, 1, 2, 3)], "inside")

# wall frames: local X along the wall, local Y up the slope, local Z out
sl = math.hypot(TY - BY, ZW - ZF); sy_, sz_ = (TY - BY) / sl, (ZW - ZF) / sl
el = math.hypot(TX - BX, ZW - ZF); ex_, ez_ = (TX - BX) / el, (ZW - ZF) / el
WF = dict(front=frame((0, -BY, ZF), (0, -sz_, -sy_), (1, 0, 0)), back=frame((0, BY, ZF), (0, sz_, -sy_), (-1, 0, 0)),
          right=frame((BX, 0, ZF), (ez_, 0, -ex_), (0, 1, 0)), left=frame((-BX, 0, ZF), (-ez_, 0, -ex_), (0, -1, 0)))
for k in ("front", "back"):
    with at(b, WF[k]):
        for u in (-1.16, -0.9, -0.64, 0.64, 0.9, 1.16):
            b.box("rib", (u - 0.05, 0.015, -0.002), (u + 0.05, sl - 0.03, 0.045), mat=BT, skip="-z", bev=0.012, bev_axes="y")
        sten("74036", -0.583, 0.47, 0.32)
        b.weld((-BX, 0.004, 0.002), (BX, 0.004, 0.002), mat=B)
for k in ("right", "left"):
    with at(b, WF[k]):
        for u in (-0.54, 0.54):
            b.box("rib", (u - 0.05, 0.015, -0.002), (u + 0.05, el - 0.035, 0.045), mat=BT, skip="-z", bev=0.012, bev_axes="y")
        sten("74036", -0.428, 0.54, 0.235)
        b.weld((-BY, 0.004, 0.002), (BY, 0.004, 0.002), mat=B)
# corner seams (bake only)
for sx in (-1, 1):
    for sy in (-1, 1): b.weld((sx * BX, sy * BY, ZF), (sx * TX, sy * TY, ZW), r=0.006, mat=B)

# ---------------- top rim (box section); under the tarpaulin the tarpaulin's skirt stands in its place
RW = 0.08
for sy in (-1, 1):
    y0, y1 = sorted((sy * HY, sy * (HY - RW)))
    b.box("rim", (XT - 0.02, y0, ZR0), (HX, y1, ZR1), mat=B, bev=0.006, bev_axes="x", skip="-x")
b.box("rim", (HX - RW, -HY + RW, ZR0), (HX, HY - RW, ZR1), mat=B, bev=0.006, bev_axes="y", skip="-y,+y")
b.box("rim_in", (-HX + 0.01, -HY + 0.01, ZR0), (XT - 0.02, HY - 0.01, ZR0 + 0.002), mat="inside", skip="+z,-x,+x,-y,+y")      # closes the gap under the tarpaulin edge

# ---------------- skids with fork pockets over a closed core
for sy in (-1, 1):
    y0, y1 = sorted((sy * 0.6, sy * 0.44))
    b.box("skid", (-BX, y0, 0.0), (BX, y1, ZF), mat=B, bev=0.006, bev_axes="x", skip="-z,+z")
    for x in (-0.75, 0.75):
        eq.quad(b, "d_pocket", (x - sy * 0.17, sy * 0.6, 0.025), (sy, 0, 0), (0, 0, 1), 0.34, 0.07, "void", detail=True, lift=0.0006)
    for x in (-1.25, -0.4, 0.4, 1.25):
        b.weld((x, sy * 0.6, ZF), (x + 0.2, sy * 0.6, ZF), mat=B)
b.box("core", (-BX + 0.03, -0.44, 0.0), (BX - 0.03, 0.44, ZF), mat="void", skip="-z,+z,-y,+y")


# ---------------- tarpaulin over the -X half: a sagging sheet, a skirt down over the rim, a flap into the skip
def zt(x, y):
    u = (x + HX) / (XT + HX); v = (y + HY) / (2 * HY)
    f = min(1.0, 5.0 * min(u, v, 1 - v)) * (1.0 - 0.45 * max(0.0, u - 0.7) / 0.3)
    return ZR1 + 0.006 + f * (0.03 + 0.02 * math.sin(5.1 * x + 1.3) * math.cos(4.3 * y) + 0.012 * math.sin(9 * x + 2 * y))


NX, NY = 14, 10
bm = bmesh.new(); G = {}
for i in range(NX + 1):
    for j in range(NY + 1):
        x = -HX + (XT + HX) * i / NX; y = -HY + 2 * HY * j / NY
        G[i, j] = bm.verts.new((x, y, zt(x, y)))
for i in range(NX):
    for j in range(NY): bm.faces.new((G[i, j], G[i + 1, j], G[i + 1, j + 1], G[i, j + 1]))
edge = [(i, 0) for i in range(NX, -1, -1)] + [(0, j) for j in range(1, NY + 1)] + [(i, NY) for i in range(1, NX + 1)]       # along -Y, -X, +Y
low = []; inn = []
for k, (i, j) in enumerate(edge):
    v = G[i, j]; zb = ZR0 - 0.05 + 0.035 * (k % 2) + 0.01 * math.sin(k * 1.7)
    low.append(bm.verts.new((v.co.x, v.co.y, zb)))
    cx = max(-HX + 0.07, v.co.x) if i == 0 else v.co.x; cy = max(-HY + 0.07, min(HY - 0.07, v.co.y)) if j in (0, NY) else v.co.y
    inn.append(bm.verts.new((cx, cy, zb)))
for k in range(len(edge) - 1):
    a, c = G[edge[k]], G[edge[k + 1]]
    bm.faces.new((a, c, low[k + 1], low[k])); bm.faces.new((low[k], low[k + 1], inn[k + 1], inn[k]))
fl = [bm.verts.new((XT + 0.015, -HY + 2 * HY * j / NY, ZR1 - 0.09 + 0.02 * math.sin(j * 2.1))) for j in range(NY + 1)]      # free edge hangs into the skip
for j in range(NY): bm.faces.new((G[NX, j], fl[j], fl[j + 1], G[NX, j + 1]))
for k in (0, len(edge) - 1):      # close the skirt ends at the free edge
    pass
bm.normal_update()
b._obj(bm, "tarp", "tarp")
for sy in (-1, 1):      # skirt ends
    y0, y1 = sorted((sy * HY, sy * (HY - 0.07)))
    b.box("tarp_end", (XT - 0.002, y0, ZR0 - 0.04), (XT, y1, ZR1 + 0.006), mat="tarp", skip="-x,-y,+y,-z,+z")
# eyelets and lashing down to cleats on the walls (bake only, on the skirt) and the cleats (real)
for sy in (-1, 1):
    for x in (-1.55, -1.1, -0.65, -0.25):
        b.cyl("d_eye", (x, sy * (HY - 0.0005), ZR0 + 0.02), (x, sy * (HY + 0.003), ZR0 + 0.02), 0.022, n=10, mat="brass", caps=(False, True), detail=True)
        b.cyl("d_eyeh", (x, sy * (HY + 0.0025), ZR0 + 0.02), (x, sy * (HY + 0.0035), ZR0 + 0.02), 0.012, n=8, mat="void", caps=(False, True), detail=True)
for y in (-0.55, 0.0, 0.55):
    b.cyl("d_eye", (-HX + 0.0005, y, ZR0 + 0.02), (-HX - 0.003, y, ZR0 + 0.02), 0.022, n=10, mat="brass", caps=(False, True), detail=True)
    b.cyl("d_eyeh", (-HX - 0.0025, y, ZR0 + 0.02), (-HX - 0.0035, y, ZR0 + 0.02), 0.012, n=8, mat="void", caps=(False, True), detail=True)

# ---------------- lifting lugs on the rim corners, shackles, sling legs and master link
LK = V((-1.0, 0.05, zt(-1.0, 0.05) + 0.024))
for sx in (-1, 1):
    for sy in (-1, 1):
        px, py = sx * 1.58, sy * (HY - 0.04)
        pw.lug(b, "lug", (px, py, ZR1 - 0.004), (1, 0, 0), 0.12, H - ZR1 + 0.004, 0.06, 0.032, 0.1, 0.035, mat=BT)
        b.box("lug_pad", (px - 0.14, py - 0.038, ZR1 - 0.002), (px + 0.14, py + 0.038, ZR1 + 0.012), mat=BT, bev=0.004, skip="-z")
        hc = V((px, py, ZR1 + 0.096))
        with at(b, frame(hc + V((0, -sy * 0.04, -0.02)), (1, 0, 0), (0, 1, 0))):      # shackle bow, hanging in to the skip side
            b.torus("shackle", (0, 0, 0), 0.05, 0.015, n=10, m=5, mat="steel")
        b.cyl("shackle_pin", (px - 0.06, py, hc.z), (px + 0.06, py, hc.z), 0.018, n=6, mat="steel")
        s0 = hc + V((0, -sy * 0.09, -0.04))
        if sx < 0:     # legs on the tarpaulin: follow it
            pts = [s0]
            for t in (0.25, 0.5, 0.75):
                q = s0.lerp(LK, t); pts.append(V((q.x, q.y, zt(q.x, q.y) + 0.018)))
            pts.append(V((LK.x - 0.13, LK.y + sy * 0.03, LK.z)))
        else:          # legs across the open top: slack, resting on the tarpaulin edge
            q1 = V((XT - 0.25, sy * 0.3, zt(XT - 0.25, sy * 0.3) + 0.018)); q0 = s0.lerp(q1, 0.5) + V((0, 0, -0.035))
            pts = [s0, q0, q1, V((-0.75, sy * 0.12, zt(-0.75, sy * 0.12) + 0.018)), V((LK.x + 0.13, LK.y + sy * 0.03, LK.z))]
        pw.tube(b, "sling", pts, 0.016, n=6, mat="rope", caps=(True, True))
        fer = pts[0].lerp(pts[1], 0.35); fer2 = pts[0].lerp(pts[1], 0.55)
        b.cyl("ferrule", fer, fer2, 0.024, n=6, mat="steel")
with at(b, T(LK) @ Matrix.Diagonal((1.7, 1.0, 1.0, 1.0))):
    b.torus("link", (0, 0, 0), 0.085, 0.02, n=12, m=5, mat="cred")

# ---------------- grime
eq.run(b, (0.9, -TY, ZW), (0, -1, 0), 0.5, 0.9, (B,), i=2, strength=0.45)
eq.run(b, (-0.9, TY, ZW), (0, 1, 0), 0.5, 0.9, (B,), i=4, strength=0.45)
eq.run(b, (TX, 0.3, ZW), (1, 0, 0), 0.45, 0.9, (B,), i=3, strength=0.4)
eq.puddle(b, (0.6, 0.0, zi), 1.2, ("inside",), strength=0.7)

eq.tail(b, HERE, HX, HY, H, size=2048, views=[(-90, 0), (0, 0), (90, 0), (180, 0), (0, 90), (-40, 24)],
        over={"inside": ("dblue", dict(dirt=0.9, rust=0.6, edge=0.5, bias=0.03, value=0.75)), "dblue": dict(edge=0.6, bias=0.0, rust=0.45, dirt=0.65), "tarp": dict(tile=0.7)},
        front=dict(minus_y="long side, number 74036", plus_y="long side, number 74036", minus_x="tapered end under the tarpaulin", plus_x="tapered end, open half of the skip"))
