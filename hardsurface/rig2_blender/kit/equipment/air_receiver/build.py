# air_receiver: vertical air receiver (pressure vessel).  1.4 (X) x 1.4 (Y) x 2.8 (Z), origin centre of the footprint
# on the floor, manway faces -Y.  Hand-modelled from sheets/air_receiver_turn.png / _detail.png.
#   shell 1.1 m diameter with a dished top head, standing on a skirt plate of the same diameter (it closes the space
#   under the bottom head: the piece is cover) with a base ring and three buttress legs on bolted base plates (one at
#   +Y, two at the front quarters); bolted manway with hinge and handles at chest height (-Y); flanged inlet and outlet
#   nozzles at +-X with green pipe stubs; relief valve (the top of the box) and pressure gauge on the top head; drain
#   line with a ball valve out through the skirt at the front; skirt access opening at the back (baked); nameplate on
#   a bracket above the manway; two lifting lugs.  The sheet drew four legs and an open bottom: the brief asks for
#   three legs and a skirt plate.  The skirt is 1.0 m, so the knuckle of the bottom head reads above it.  Manway with
#   two handles and a strap hinge; relief valve with an open spring bonnet; gauge on a syphon with a cock; a small
#   instrument line with a valve down the back-left quarter.  Close-up review against sheets/air_receiver_close1.png.
#   blender -b --factory-startup -t 4 --python build.py [-- --nobake] [--size 2048] [--spp 24] [--noreview]
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import _eq as eq
from _eq import pw, V, T, at, frame
b = eq.new("air_receiver")
HX = HY = 0.7; H = 2.8
R = 0.55; N = 24
ZB, ZT, DH = 0.66, 2.25, 0.25         # bottom tangent (skirt joint), top tangent, head depth
W, G = "lgrey", "lgrey_t"


def head_z(r): return ZT + DH * math.sqrt(max(0.0, 1 - (r / R) ** 2))


# ---------------- shell, skirt and base ring in one turn; girth welds baked
RS = 0.5; TK = math.asin(RS / R); ZK = ZB - DH * math.cos(TK)      # skirt radius; where the bottom head meets it
prof = [(RS + 0.06, 0.0), (RS + 0.06, 0.025), (RS, 0.025), (RS, ZK)] + [(R * math.sin(TK + (math.pi / 2 - TK) * i / 3), ZB - DH * math.cos(TK + (math.pi / 2 - TK) * i / 3)) for i in range(1, 4)] + [(R, ZT)] + [(R * math.sin(math.pi / 2 * (1 - i / 5)), ZT + DH * math.cos(math.pi / 2 * (1 - i / 5))) for i in range(1, 6)]
prof[-1] = (0.0, ZT + DH)
b.lathe("shell", prof, n=N, mat=W, phase=0.0)
for z in (ZB, 1.45, ZT):      # girth welds on the same facets as the shell
    b.lathe("d_seam", [(R - 0.001, z - 0.009), (R + 0.004, z - 0.004), (R + 0.004, z + 0.004), (R - 0.001, z + 0.009)], n=N, mat=W, detail=True, phase=0.0)
b.torus("d_skirtweld", (0, 0, ZK - 0.002), RS + 0.003, 0.008, n=N, m=6, mat=W, detail=True)
for ang, z0, z1 in ((120, ZB + 0.01, 1.44), (45, 1.46, ZT - 0.01)):      # long seams on a shell vertex line
    a = math.radians(ang); b.weld((R * math.cos(a), R * math.sin(a), z0), (R * math.cos(a), R * math.sin(a), z1), r=0.005, mat=W)
# skirt access opening at the back quarter and two vent holes (bake only)
for ang, w, h, z in ((52.5, 0.125, 0.3, 0.22), (142.5, 0.06, 0.06, 0.5), (262.5, 0.06, 0.06, 0.5)):      # facet centres
    a = math.radians(ang); nrm = V((math.cos(a), math.sin(a), 0)); side = V((-math.sin(a), math.cos(a), 0))
    rr = RS * math.cos(math.pi / N)
    with at(b, frame(nrm * rr + V((0, 0, z)), nrm, side)):
        b.box("d_open", (-w / 2, -h / 2, -0.004), (w / 2, h / 2, 0.002), mat="dark", detail=True)
        if w > 0.1:
            b.box("d_openf", (-w / 2 - 0.008, -h / 2 - 0.02, -0.004), (w / 2 + 0.008, h / 2 + 0.02, 0.0012), mat=W, detail=True, bev=0.001)

# ---------------- three buttress legs on base plates (the +Y plate is the +Y face of the box)
for ang in (90, 210, 330):
    a = math.radians(ang)
    with at(b, frame((0, 0, 0), (0, 0, 1), (math.cos(a), math.sin(a), 0))):      # local X = radial
        b.box("leg", (RS - 0.01, -0.07, 0.02), (R + 0.105, 0.07, 0.95), mat=W, skip="-z,-x,+z", bev=0.008, bev_axes="z")
        b.prism("leg_top", (R - 0.03, 0, 0.95), (1, 0, 0), (0, 0, 1), [(0, 0), (0.135, 0), (0, 0.16)], -0.07, 0.07, mat=W, skip_side=(0, 2), caps=(True, True))
        b.box("leg_plate", (RS - 0.04, -0.12, 0.0), (R + 0.15, 0.12, 0.02), mat=W, skip="-z", bev=0.004, bev_axes="z")
        for sx, sy in ((0.115, -0.085), (0.115, 0.085)):
            b.cyl("nut", (R + sx, sy, 0.02), (R + sx, sy, 0.048), 0.02, n=6, mat="steel", caps=(False, True))
            b.cyl("stud", (R + sx, sy, 0.048), (R + sx, sy, 0.062), 0.011, n=6, mat="steel", caps=(False, True))
        for sy in (-1, 1):
            b.prism("leg_gus", (R + 0.105, sy * 0.0, 0.02), (1, 0, 0), (0, 0, 1), [(0, 0), (0.04, 0), (0, 0.14)], sy * 0.07 - 0.005, sy * 0.07 + 0.005, mat=G)
        b.weld((R + 0.106, -0.07, 0.3), (R + 0.106, -0.07, 0.94), mat=W); b.weld((R - 0.0, 0.072, 0.03), (R + 0.0, 0.072, 0.94), mat=W)
        b.weld((R - 0.0, -0.072, 0.03), (R + 0.0, -0.072, 0.94), mat=W)

# ---------------- manway (-Y), nameplate above it
pw.manway(b, (0, -R, 1.5), (0, -1, 0), 0.24, 0.0512, mat=W, nb=18, nr=0.018, n=20, t=0.035, handles=False)
MZ = 0.0512 + 0.006 + 0.035          # cover face, out from the shell
with at(b, frame((0, -R, 1.5), (0, -1, 0), (0, 0, 1))):          # local X = up, local Y = -X of the model, local Z = out
    for sy in (-1, 1):      # two upright handles
        y = sy * 0.1
        pw.tube(b, "handle", pw.route([(-0.11, y, MZ - 0.005), (-0.11, y, MZ + 0.0468), (0.11, y, MZ + 0.0468), (0.11, y, MZ - 0.005)], 0.02, k=2), 0.011, n=6, mat="steel")
        for sx in (-1, 1): b.cyl("d_handle_boss", (sx * 0.11, y, MZ - 0.001), (sx * 0.11, y, MZ + 0.004), 0.02, n=12, mat="steel", caps=(False, True), detail=True)
    # hinge on the -X side: a bracket off the shell, a pin, two straps bolted to the cover
    b.box("hinge_brk", (-0.06, 0.35, -0.15), (0.06, 0.4, MZ + 0.03), mat=G, skip="-z", bev=0.005, bev_axes="x")
    b.cyl("hinge_pin", (-0.15, 0.375, MZ + 0.01), (0.15, 0.375, MZ + 0.01), 0.018, n=8, mat="steel")
    for sx in (-1, 1):
        b.box("hinge_strap", (sx * 0.105 - 0.028, 0.17, MZ), (sx * 0.105 + 0.028, 0.395, MZ + 0.02), mat=G, skip="-z", bev=0.004, bev_axes="y")
        for y in (0.2, 0.27): b.bolt((sx * 0.105, y, MZ + 0.02), (0, 0, 1), r=0.011, mat="steel")
    b.torus("d_gasket", (0, 0, MZ - 0.038), 0.326, 0.004, n=40, m=6, mat="dark", detail=True)
    b.cyl("d_centre", (0, 0, MZ - 0.001), (0, 0, MZ + 0.004), 0.03, n=16, mat=W, caps=(False, True), detail=True)
with at(b, frame((0, -R * 0.98, 2.0), (0, -1, 0), (1, 0, 0))):
    for sx in (-1, 1): b.box("plate_brk", (sx * 0.11 - 0.006, -0.03, 0), (sx * 0.11 + 0.006, 0.03, 0.045), mat=G, skip="-z")
    b.box("nameplate", (-0.17, -0.09, 0.045), (0.17, 0.09, 0.052), mat="steel", bev=0.002)
    b.box("d_plate_in", (-0.15, -0.07, 0.052), (0.15, 0.07, 0.0535), mat="stainless", detail=True)
    for sx in (-1, 1):
        for sy in (-1, 1): b.rivet((sx * 0.158, sy * 0.078, 0.052), (0, 0, 1), r=0.006, mat="steel")

# ---------------- inlet and outlet nozzles (+-X), flange faces on the box, bores closed dark, green pipe stubs behind
DN = 0.17
for sx, z in ((-1, 1.5), (1, 1.5)):
    pw.nozzle(b, (sx * R * 0.995, 0, z), (sx, 0, 0), DN, HX - R * 0.995, mat=W, real=True, n=12)
    with at(b, frame((sx * HX, 0, z), (sx, 0, 0))):
        b.lathe("bore", [(DN / 2 * 0.86, 0.0), (0.0, 0.0)], n=12, mat="dark", phase=0.0)
    with at(b, frame((sx * R, 0, z), (sx, 0, 0))):
        b.torus("d_nozweld", (0, 0, 0.004), DN / 2 + 0.006, 0.008, n=24, m=6, mat=W, detail=True)
# small instrument nozzle at the back with a blind flange
pw.nozzle(b, (0.0, R * 0.995, 1.75), (0, 1, 0), 0.09, 0.07, mat=W, blind=True, real=False, n=8)

# ---------------- top head: relief valve (top of the box), pressure gauge, two lifting lugs
XR, XG = -0.2, 0.23
zr = head_z(abs(XR)) - 0.03; h = H - zr
with at(b, T(V((XR, 0, zr)))):
    b.lathe("relief", [(0.045, 0.0), (0.045, 0.09), (0.085, 0.09), (0.085, 0.118), (0.06, 0.118), (0.07, 0.15), (0.07, 0.2), (0.05, 0.215), (0.05, 0.225), (0.075, 0.225), (0.075, 0.243),
                       (0.034, 0.243), (0.034, h - 0.06), (0.062, h - 0.06), (0.062, h - 0.042), (0.03, h - 0.04), (0.03, h - 0.004), (0.0, h)], n=10, mat="steel", phase=0.0)
    for k in range(int((h - 0.06 - 0.25) / 0.022)): b.torus("d_spring", (0, 0, 0.255 + k * 0.022), 0.034, 0.0065, n=20, m=6, mat="steel", detail=True)
    for sx in (-1, 1): b.box("relief_yoke", (sx * 0.056 - 0.007, -0.014, 0.243), (sx * 0.056 + 0.007, 0.014, h - 0.06), mat="steel", skip="-z,+z")
    b.box("relief_pivot", (-0.02, -0.075, h - 0.06), (0.02, -0.045, h - 0.02), mat="steel", skip="-z")
    pw.bolts(b, 0.067, 6, 0.01, [(0.118, 1)], True, "steel")
    pw.tube(b, "relief_out", [(0, 0.05, 0.175), (0, 0.15, 0.175)], 0.04, n=8, mat="steel", caps=(False, False))
    with at(b, frame((0, 0.15, 0.175), (0, 1, 0))):
        b.lathe("relief_fl", [(0.04, -0.02), (0.075, -0.02), (0.075, 0.0), (0.0, 0.0)], n=10, mat="steel", phase=0.0)
    b.box("relief_lever", (-0.012, -0.16, h - 0.045), (0.012, 0.02, h - 0.025), mat="wheel", bev=0.003)
    b.lathe("d_repad", [(0.11, -0.01), (0.11, 0.034), (0.045, 0.034)], n=20, mat=W, detail=True, phase=0.0)
zg = head_z(XG) - 0.02
b.cyl("gauge_stub", (XG, 0, zg), (XG, 0, zg + 0.07), 0.03, n=8, mat="steel", caps=(False, True))
b.cyl("gauge_stem", (XG, 0, zg + 0.07), (XG, 0, zg + 0.2), 0.013, n=6, mat="brass", caps=(False, False))
with at(b, frame((XG + 0.03, 0, zg + 0.105), (0, 1, 0))): b.torus("syphon", (0, 0, 0), 0.03, 0.009, n=10, m=5, mat="brass")
b.box("gauge_cock", (XG - 0.02, -0.02, zg + 0.145), (XG + 0.02, 0.02, zg + 0.185), mat="brass", bev=0.004)
b.cyl("cock_stem", (XG, -0.02, zg + 0.165), (XG, -0.04, zg + 0.165), 0.008, n=6, mat="steel", caps=(False, True))
b.box("cock_lever", (XG - 0.01, -0.046, zg + 0.158), (XG + 0.085, -0.036, zg + 0.172), mat="brass", bev=0.003)
b.cyl("gauge", (XG, 0.024, zg + 0.265), (XG, -0.03, zg + 0.265), 0.07, n=14, mat="steel")
b.cyl("d_dial", (XG, -0.0305, zg + 0.265), (XG, -0.033, zg + 0.265), 0.058, n=20, mat="paintw", caps=(True, True), detail=True)
b.box("d_needle", (XG - 0.004, -0.0345, zg + 0.26), (XG + 0.004, -0.033, zg + 0.31), mat="black", detail=True)
for sy in (-1, 1):
    pw.lug(b, "lug", (0.0, sy * 0.4, head_z(0.4) - 0.03), (1, 0, 0), 0.07, 0.15, 0.045, 0.026, 0.1, 0.02, mat=G)

# ---------------- drain: out through the skirt at the front, ball valve with a red lever, plugged end
ZD = 0.24
pw.tube(b, "drain", [(0, -RS + 0.02, ZD), (0, -RS - 0.04, ZD)], 0.022, n=8, mat="steel")
with at(b, frame((0, -RS - 0.04, ZD), (0, -1, 0), (1, 0, 0))):
    b.lathe("drain_valve", [(0.03, 0.0), (0.03, 0.015), (0.036, 0.02), (0.036, 0.06), (0.03, 0.065), (0.03, 0.08), (0.022, 0.08), (0.022, 0.105), (0.0, 0.105)], n=8, mat="brass", phase=0.0)
b.cyl("drain_stem", (0, -RS - 0.08, ZD + 0.03), (0, -RS - 0.08, ZD + 0.06), 0.01, n=6, mat="steel", caps=(False, True))
b.box("drain_lever", (-0.012, -RS - 0.092, ZD + 0.055), (0.14, -RS - 0.068, ZD + 0.067), mat="wheel", bev=0.003)
with at(b, frame((0, -RS, ZD), (0, -1, 0))):
    b.lathe("d_drainpad", [(0.05, -0.02), (0.05, 0.003), (0.022, 0.003)], n=16, mat=W, detail=True, phase=0.0)

# ---------------- small-bore instrument line down the back-left quarter: boss, valve, two clips
AI = math.radians(142.5); ci, si = math.cos(AI), math.sin(AI); RP = R + 0.055
pw.tube(b, "line", pw.route([(R * 0.98 * ci, R * 0.98 * si, 2.08), (RP * ci, RP * si, 2.08), (RP * ci, RP * si, 0.82), (R * 0.98 * ci, R * 0.98 * si, 0.82)], 0.04, k=2), 0.016, n=6, mat="steel")
with at(b, frame((RP * ci, RP * si, 0), (0, 0, 1), (ci, si, 0))):          # local X = radial
    b.lathe("line_valve", [(0.017, 1.26), (0.03, 1.275), (0.03, 1.345), (0.017, 1.36)], n=8, mat="brass", phase=0.0)
    b.cyl("line_stem", (0.028, 0, 1.31), (0.06, 0, 1.31), 0.009, n=6, mat="steel", caps=(False, True))
    b.box("line_lever", (0.055, -0.01, 1.3), (0.068, 0.01, 1.42), mat="wheel", bev=0.003)
    for z in (1.02, 1.72):
        b.box("line_clip", (-0.06, -0.022, z - 0.015), (0.02, 0.022, z + 0.015), mat=G, skip="-x")
        b.bolt((0.02, 0, z), (1, 0, 0), r=0.008, mat="steel")
    for z in (2.08, 0.82): b.lathe("d_boss", [(0.03, z - 0.03), (0.03, z + 0.03)], n=10, mat=W, detail=True, at=(-0.045, 0, 0), phase=0.0)

# ---------------- grime: a run under the manway, under a nozzle, under the back nozzle (three on the shell paint)
eq.run(b, (0.05, -R, 1.2), (0, -1, 0), 0.5, 1.1, (W,), i=2, strength=0.5)
eq.run(b, (R, 0.0, 1.42), (1, 0, 0), 0.3, 1.2, (W,), i=4, strength=0.5)
eq.run(b, (-R * 0.7, R * 0.7, ZT), (-0.7, 0.7, 0), 0.45, 1.5, (W,), i=3, strength=0.4)

CLOSE = dict(sheet="air_receiver_close1", shots=[
    dict(eye=(0, -2.5, 1.55), at=(0, -0.55, 1.55), lens=45), dict(eye=(2.3, -0.6, 1.5), at=(0, -0.6, 1.5), lens=55), dict(eye=(0, -2.0, 2.8), at=(0, 0, 2.6), lens=55),
    dict(eye=(1.7, -1.5, 1.6), at=(0.62, 0, 1.5), lens=65), dict(eye=(0, -2.3, 2.02), at=(0, -0.55, 2.05), lens=70), dict(eye=(0.6, -2.0, 0.6), at=(0, -0.3, 0.45), lens=45)])
eq.tail(b, HERE, HX, HY, H, size=2048, close=CLOSE,
        over={"lgrey": dict(tint=pw.tn(192, 194, 189), value=1.0, dirt=0.7, rust=0.5, edge=0.6, bias=-0.03)},
        grunge={"lgrey": dict(streak=0.95, chips=0.6, grime=0.6, fade=0.15)},
        front=dict(minus_y="manway, nameplate, drain valve", plus_x="flanged nozzle (the same at -X)", plus_y="one leg, small blind nozzle, skirt access opening towards +X+Y"))
