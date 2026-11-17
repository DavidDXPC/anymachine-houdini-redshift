# ibc_stack: two tote tanks (intermediate bulk containers) stacked.  1.2 (X) x 1.0 (Y) x 2.3 (Z), origin centre of the
# footprint on the floor, taps and label plates face -Y.  Hand-modelled from sheets/ibc_stack_turn.png / _detail.png.
#   each tank 1.2 x 1.0 x 1.15: steel pallet base (eight feet round a closed core, so nothing shows through), opaque
#   white blow-moulded tank with the liquid showing as a darker lower half, tubular galvanised cage (six rings, upright
#   tubes), a stepped sump at the front with the drain tap in it, a label plate on the cage, the screw lid on top.
#   blender -b --factory-startup -t 4 --python build.py [-- --nobake] [--size 1024] [--spp 24] [--noreview]
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import _eq as eq
from _eq import pw, V, T, at, frame
b = eq.new("ibc_stack")
HX, HY, H1 = 0.6, 0.5, 1.15
R = 0.011                      # cage tube radius
CX, CY = HX - R, HY - R        # cage centre lines
TXh, TYh = HX - 2 * R - 0.002, HY - 2 * R - 0.002      # tank half sizes
ZP, ZS, ZT = 0.13, 0.31, 1.105  # pallet top, sump step, tank top
ZTOP = H1 - R                  # top ring


def ibc(level, lid):
    zl = (0.58, 0.47)[level]       # liquid line
    # ---- pallet: closed dark core, eight feet, a top frame
    b.box("core", (-HX + 0.03, -HY + 0.03, 0.0), (HX - 0.03, HY - 0.03, ZP - 0.035), mat="void", skip="-z,+z")
    for x0, x1 in ((-HX, -HX + 0.16), (-0.11, 0.11), (HX - 0.16, HX)):
        for y0, y1 in ((-HY, -HY + 0.14), (-0.09, 0.09), (HY - 0.14, HY)):
            if abs(x0 + x1) < 0.01 and abs(y0 + y1) < 0.01: continue
            b.box("foot", (x0, y0, 0.0), (x1, y1, ZP - 0.035), mat="galv", skip="-z,+z", bev=0.006, bev_axes="z")
    b.box("deck", (-HX, -HY, ZP - 0.035), (HX, HY, ZP), mat="galv", bev=0.004, bev_axes="xy", skip="+z")
    for sx in (-1, 1):
        for sy in (-1, 1): b.bolt((sx * (HX - 0.08), sy * HY, ZP - 0.018), (0, sy, 0), r=0.009, mat="steel")
    # ---- tank: sump step, liquid half, empty half with rounded shoulders
    b.box("tank_sump", (-TXh, -TYh + 0.085, ZP), (TXh, TYh, ZS), mat="liquid", skip="-z,+z", bev=0.04, bev_axes="z")
    eq.quad(b, "tank_step", (-TXh + 0.04, -TYh + 0.085, ZS), (1, 0, 0), (0, -1, 0), 2 * TXh - 0.08, 0.085, "liquid")
    b.box("tank_liquid", (-TXh, -TYh, ZS), (TXh, TYh, zl), mat="liquid", skip="-z,+z", bev=0.04, bev_axes="z")
    b.box("tank", (-TXh, -TYh, zl), (TXh, TYh, ZT), mat="plastic", skip="-z", bev=0.04)
    for x in (-0.36, -0.2, 0.2, 0.36):      # moulded ribs on the top, the filler neck (bake only)
        b.box("d_rib", (x - 0.02, -TYh + 0.1, ZT - 0.001), (x + 0.02, TYh - 0.1, ZT + 0.004), mat="plastic", detail=True, bev=0.003)
    b.box("d_line", (-TXh - 0.0005, -TYh - 0.0005, zl - 0.012), (TXh + 0.0005, TYh + 0.0005, zl + 0.004), mat="liquid", detail=True)
    # ---- cage: rings with rounded corners, upright tubes
    for z in (ZP + 0.02, 0.33, 0.53, 0.73, 0.93, ZTOP):
        pts = pw.route([(0, -CY, z), (CX, -CY, z), (CX, CY, z), (-CX, CY, z), (-CX, -CY, z), (0, -CY, z)], 0.05, k=2)
        pw.tube(b, "ring", pts, R, n=6, mat="galv_t")
    for i in range(1, 6):
        x = -CX + 2 * CX * i / 6
        for sy in (-1, 1): pw.tube(b, "upright", [(x, sy * CY, ZP), (x, sy * CY, ZTOP)], R, n=6, mat="galv_t", side=(0, 1, 0))
    for i in range(1, 5):
        y = -CY + 2 * CY * i / 5
        for sx in (-1, 1): pw.tube(b, "upright", [(sx * CX, y, ZP), (sx * CX, y, ZTOP)], R, n=6, mat="galv_t")
    for x in (-0.2, 0.2): pw.tube(b, "top_bar", [(x, -CY, ZTOP), (x, CY, ZTOP)], R, n=6, mat="galv_t")
    # ---- label plate on the cage front, tap in the sump, lid
    b.box("label", (-0.2, -HY, 0.64), (0.2, -HY + 0.006, 0.9), mat="steel", skip="+y")
    for sx in (-1, 1):
        for sz in (0.665, 0.875): b.rivet((sx * 0.18, -HY, sz), (0, -1, 0), r=0.007, mat="steel")
    yt = -TYh + 0.085; zt = ZP + 0.085
    with at(b, frame((0, yt, zt), (0, -1, 0), (1, 0, 0))):
        b.lathe("tap", [(0.062, 0.0), (0.062, 0.012), (0.036, 0.012), (0.036, 0.05), (0.044, 0.05), (0.044, 0.088), (0.03, 0.088), (0.03, 0.02), (0.0, 0.02)], n=8, mat="black", phase=0.0)
        for i in range(4):
            a = math.pi / 4 + i * math.pi / 2; b.bolt((0.049 * math.cos(a), 0.049 * math.sin(a), 0.012), (0, 0, 1), r=0.007, mat="steel")
    b.cyl("tap_stem", (0, yt - 0.034, zt + 0.03), (0, yt - 0.034, zt + 0.066), 0.012, n=6, mat="black", caps=(False, True))
    b.box("tap_handle", (-0.012, yt - 0.046, zt + 0.062), (0.13, yt - 0.022, zt + 0.074), mat="cblue", bev=0.003)
    if lid:
        b.lathe("lid", [(0.105, ZT - 0.002), (0.105, ZT + 0.03), (0.095, H1), (0.0, H1)], n=12, mat="rubber", phase=0.0)
        for i in range(12):
            a = 2 * math.pi * i / 12
            b.box("d_lidrib", (0.103 * math.cos(a) - 0.006, 0.103 * math.sin(a) - 0.006, ZT), (0.103 * math.cos(a) + 0.006, 0.103 * math.sin(a) + 0.006, ZT + 0.03), mat="rubber", detail=True)


ibc(0, False)
with at(b, T(V((0, 0, H1)))): ibc(1, True)
# stains: few per material (each one is a mix in the paint shader, and the glTF exporter walks them all)
ZL = 2 * H1 - 0.045
eq.puddle(b, (0.05, 0.02, ZL), 0.5, ("plastic",), strength=0.45)
eq.run(b, (0.0, -TYh, ZP + 0.1 + H1), (0, -1, 0), 0.2, 0.22, ("liquid", "galv"), i=1, strength=0.6)
eq.run(b, (0.0, -TYh, ZP + 0.1), (0, -1, 0), 0.2, 0.22, ("liquid", "galv"), i=1, strength=0.6)
eq.run(b, (-TXh, 0.1, ZL), (-1, 0, 0), 0.4, 1.9, ("plastic", "liquid"), i=2, strength=0.3)
eq.run(b, (0.25, TYh, ZL), (0, 1, 0), 0.4, 1.8, ("plastic",), i=4, strength=0.3)

eq.tail(b, HERE, HX, HY, 2 * H1, size=1024, front=dict(minus_y="drain taps and label plates", plus_x="plain cage side"),
        over={"plastic": dict(dirt=0.45), "liquid": dict(dirt=0.4)})
