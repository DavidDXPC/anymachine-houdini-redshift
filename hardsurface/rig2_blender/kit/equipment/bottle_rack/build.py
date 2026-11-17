# bottle_rack: gas cylinder rack (bottle quad).  1.3 (X) x 1.0 (Y) x 1.9 (Z), origin centre of the footprint on the
# floor, the open side with the chain faces -Y.  Hand-modelled from sheets/bottle_rack_turn.png / _detail.png.
#   galvanised frame on a fork-pocket base, posts and rails 70 mm, a lifting eye on each top corner (the top of the
#   box), expanded-mesh panels on both ends and the back (opaque: one quad each, the mesh and the cylinders behind it
#   are baked), six cylinders 0.36 m in two rows (three maroon, three grey, white shoulders, grey caps), a chain across
#   the front, a blank hazard diamond on each end.
#   blender -b --factory-startup -t 4 --python build.py [-- --nobake] [--size 1024] [--spp 24] [--noreview]
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import _eq as eq
from _eq import pw, V, T, at, frame
b = eq.new("bottle_rack")
HX, HY, H = 0.65, 0.5, 1.9
P = 0.07                         # post and rail section
ZB, ZT = 0.2, 1.76               # base top, frame top
G = "galv"

# ---------------- base: closed box with fork pockets (dark, baked), chequer floor
b.box("base", (-HX, -HY, 0.0), (HX, HY, ZB), mat=G, bev=0.006, skip="-z")
for sy in (-1, 1):
    for x in (-0.3, 0.3):
        with at(b, frame((x, sy * HY, 0.085), (0, sy, 0), (1, 0, 0))):
            b.box("d_pocket", (-0.14, -0.045, -0.002), (0.14, 0.045, 0.0008), mat="dark", detail=True)
            for q in ((-0.155, -0.06, -0.14, 0.06), (0.14, -0.06, 0.155, 0.06), (-0.155, 0.045, 0.155, 0.06), (-0.155, -0.06, 0.155, -0.045)):
                b.box("d_pocket_rim", (q[0], q[1], 0), (q[2], q[3], 0.004), mat=G, detail=True)
for sx in (-1, 1):
    for sy in (-1, 1):
        b.box("corner_shoe", (sx * HX - (0.11 if sx > 0 else 0), sy * HY - (0.11 if sy > 0 else 0), 0.0), (sx * HX + (0.11 if sx < 0 else 0), sy * HY + (0.11 if sy < 0 else 0), 0.012), mat=G, detail=True)

# ---------------- frame: posts, top rails, mid rails on the closed sides, kick rail and top rail at the front
for sx in (-1, 1):
    for sy in (-1, 1):
        x0, x1 = sorted((sx * HX, sx * (HX - P))); y0, y1 = sorted((sy * HY, sy * (HY - P)))
        b.box("post", (x0, y0, ZB), (x1, y1, ZT), mat=G, bev=0.005, bev_axes="z", skip="-z,+z")
        pw.lug(b, "eye", (sx * (HX - 0.035), sy * (HY - 0.09), ZT), (0, 1, 0), 0.055, H - ZT, 0.035, 0.024, 0.085, 0.02, mat=G + "_t")
        for z in (ZT - 0.035, 1.0, ZB + 0.06):      # joint bolts on the end faces
            b.bolt((sx * HX, sy * (HY - 0.035), z), (sx, 0, 0), r=0.011, mat="steel")
for sy in (-1, 1):
    y0, y1 = sorted((sy * HY, sy * (HY - P)))
    b.box("top_rail", (-HX + P, y0, ZT - P), (HX - P, y1, ZT), mat=G, skip="-x,+x")
for sx in (-1, 1):
    x0, x1 = sorted((sx * HX, sx * (HX - P)))
    b.box("top_rail", (x0, -HY + P, ZT - P), (x1, HY - P, ZT), mat=G, skip="-y,+y")
    b.box("mid_rail", (x0, -HY + P, 0.97), (x1, HY - P, 1.03), mat=G, skip="-y,+y")
    b.box("low_rail", (x0, -HY + P, ZB), (x1, HY - P, ZB + 0.09), mat=G, skip="-y,+y,-z")
b.box("mid_rail", (-HX + P, HY - P, 0.97), (HX - P, HY, 1.03), mat=G, skip="-x,+x")
b.box("low_rail", (-HX + P, HY - P, ZB), (HX - P, HY, ZB + 0.09), mat=G, skip="-x,+x,-z")
b.box("kick_rail", (-HX + P, -HY, ZB), (HX - P, -HY + 0.03, ZB + 0.12), mat=G, skip="-x,+x,-z")
b.weld((-HX + P, -HY + 0.03, ZB + 0.001), (HX - P, -HY + 0.03, ZB + 0.001), mat=G)

# ---------------- cylinders: front row maroon, maroon, grey; back row maroon, grey, grey
RC = 0.18; ZS, ZN = 1.42, 1.56          # shoulder start, neck
ROWS = [(-0.2, ("maroon", "maroon", "cylgrey")), (0.2, ("maroon", "cylgrey", "cylgrey"))]
XS = (-0.37, 0.0, 0.37)
sh = [(RC * math.cos(math.radians(a)) if a else RC, ZS + (ZN - ZS) * math.sin(math.radians(a))) for a in (0, 30, 55, 75)]
for y, cols in ROWS:
    for x, c in zip(XS, cols):
        with at(b, T(V((x, y, 0))) @ eq.RZ(17 * (x + 2 * y) * 10)):
            b.lathe("cyl", [(RC, ZB), (RC, ZS)], n=12, mat=c, phase=0.0)
            b.lathe("shoulder", sh + [(0.05, ZN + 0.01), (0.05, ZN + 0.03)], n=12, mat="pipe", phase=0.0)
            b.lathe("cap", [(0.062, ZN + 0.03), (0.062, ZN + 0.11), (0.045, ZN + 0.155), (0.0, ZN + 0.165)], n=8, mat="grey", phase=0.0)
            b.lathe("d_collar", [(0.066, ZN + 0.028), (0.066, ZN + 0.045), (0.06, ZN + 0.045)], n=12, mat="steel", detail=True, phase=0.0)
            pw.seam(b, (0, 0, ZS - 0.01), (0, 0, 1), RC, mat=c, n=24, rr=0.004)

# ---------------- mesh panels (opaque), with the cylinders behind them baked in
ZM0, ZM1 = ZB + 0.09, ZT - P


def backs(seq, u_of):          # seq: [(centre along the panel, colour)]
    out = []
    for c, col in seq:
        u0, u1 = u_of(c) - RC * 0.97, u_of(c) + RC * 0.97
        out += [(u0, u1, 0.0, ZS - ZM0, col), (u0 + 0.03, u1 - 0.03, ZS - ZM0, ZS - ZM0 + 0.1, "paintw"), (u_of(c) - 0.06, u_of(c) + 0.06, ZS - ZM0 + 0.1, ZN + 0.16 - ZM0, "grey")]
    return out


XP = HX - 0.03; YP = HY - 0.03; WY = 2 * (HY - P); WX = 2 * (HX - P)
eq.mesh_panel(b, (XP, -HY + P, ZM0), (0, 1, 0), (0, 0, 1), WY, ZM1 - ZM0, backs=backs([(-0.2, "cylgrey"), (0.2, "cylgrey")], lambda y: y + HY - P), lw=0.11, sw=0.055, bw=0.009)
eq.mesh_panel(b, (-XP, HY - P, ZM0), (0, -1, 0), (0, 0, 1), WY, ZM1 - ZM0, backs=backs([(-0.2, "maroon"), (0.2, "maroon")], lambda y: HY - P - y), lw=0.11, sw=0.055, bw=0.009)
eq.mesh_panel(b, (HX - P, YP, ZM0), (-1, 0, 0), (0, 0, 1), WX, ZM1 - ZM0, backs=backs([(-0.37, "maroon"), (0.0, "cylgrey"), (0.37, "cylgrey")], lambda x: HX - P - x), lw=0.11, sw=0.055, bw=0.009)
for sx in (-1, 1):             # blank hazard diamond on each end, on the mesh
    with at(b, frame((sx * XP, 0.0, 1.38), (sx, 0, 0), (0, sx, 0)) @ eq.RZ(45)):
        b.box("diamond", (-0.12, -0.12, 0.0), (0.12, 0.12, 0.006), mat="steel", skip="-z")
        for u, v in ((-0.1, -0.1), (0.1, 0.1), (-0.1, 0.1), (0.1, -0.1)): b.rivet((u, v, 0.006), (0, 0, 1), r=0.007, mat="steel")

# ---------------- chain across the open front, hooked to the posts
ZC = 1.05; n = 21; yc = -HY + 0.035
pts = [V((-HX + P + (WX) * i / n, yc - 0.02, ZC - 0.16 * (1 - (2 * i / n - 1) ** 2))) for i in range(n + 1)]
for i, (p, q) in enumerate(zip(pts, pts[1:])):
    d = (q - p); L = d.length; m = (p + q) / 2
    with at(b, frame(m, d.normalized(), (0, 1, 0))):       # local Z along the chain
        if i % 2: b.box("link", (-0.004, -0.016, -L * 0.72), (0.004, 0.016, L * 0.72), mat="steel_t", bev=0.003, bev_axes="x")
        else: b.box("link", (-0.016, -0.004, -L * 0.72), (0.016, 0.004, L * 0.72), mat="steel_t", bev=0.003, bev_axes="y")
for sx in (-1, 1):
    b.box("hook_plate", (sx * (HX - P) - (0.012 if sx > 0 else 0), -HY + 0.008, ZC - 0.07), (sx * (HX - P) + (0.012 if sx < 0 else 0), -HY + 0.06, ZC + 0.07), mat=G + "_t")

# ---------------- grime
eq.run(b, (0.37, -0.2 - RC, 1.3), (0, -1, 0), 0.25, 0.9, ("cylgrey", "maroon"), i=2, strength=0.4)
eq.run(b, (-0.37, -0.2 - RC, 1.1), (0, -1, 0), 0.2, 0.7, ("maroon",), i=4, strength=0.4)
eq.run(b, (0.3, -HY, ZB), (0, -1, 0), 0.5, 0.2, (G,), i=1, strength=0.5)
eq.run(b, (HX, 0.1, ZB), (1, 0, 0), 0.5, 0.2, (G,), i=3, strength=0.5)

eq.tail(b, HERE, HX, HY, H, size=1024, front=dict(minus_y="open side: three cylinders behind a chain", plus_x="mesh end with a hazard diamond", plus_y="mesh back"),
        uv_scale={"void": 1.0})
