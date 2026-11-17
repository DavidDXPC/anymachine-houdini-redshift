# xmas_tree: wellhead valve tree on a kerb.  1.6 (X) x 1.6 (Y) x 2.6 (Z), origin centre of the footprint on the floor,
# master valve handwheels face -Y, wing arms along X (choke at +X).
# Hand-modelled from sheets/xmas_tree_turn.png, _detail.png and _close1.png.
#   square ochre kerb 0.30 m with grating (opaque, baked) and four lifting eyes; wellhead base flange; casing head
#   with a side outlet each way along X (small gate valves, blind flanges); tubing head with blind outlets along Y;
#   two stacked master gate valves (cast barrel bodies, necks, bonnets and red handwheels to the front); cross block with
#   a wing each side: studded flanges, wing valve with its handwheel up, then the choke (+X) or a blind cap (-X);
#   tree cap with needle valve and pressure gauge (the top of the box).  The box is taller than the sheet's tree, so
#   the stack has the two masters under the cross (the sheet has the upper one at the cross) and the casing and tubing
#   heads with their outlets below, which the sheet does not show: they also widen the piece as cover.
#   blender -b --factory-startup -t 4 --python build.py [-- --nobake] [--size 2048] [--spp 24] [--noreview]
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import _eq as eq
from _eq import pw, V, T, at, frame
b = eq.new("xmas_tree")
HX = HY = 0.8; H = 2.6
GR, GT, Y, WH, ST = "green", "green_t", "yellow", "wheel", "steel"
ZK, ZG = 0.30, 0.285          # kerb top, grating
N = 12                        # turned parts
RF, RBC, NB, NR = 0.34, 0.292, 8, 0.024

# ---------------- kerb: four plate walls, grating inside (one quad, the bars baked), lifting eyes
KT = 0.05
b.box("kerb", (-HX, -HY, 0), (HX, -HY + KT, ZK), mat=Y, skip="-z")
b.box("kerb", (-HX, HY - KT, 0), (HX, HY, ZK), mat=Y, skip="-z")
b.box("kerb", (-HX, -HY + KT, 0), (-HX + KT, HY - KT, ZK), mat=Y, skip="-z,-y,+y")
b.box("kerb", (HX - KT, -HY + KT, 0), (HX, HY - KT, ZK), mat=Y, skip="-z,-y,+y")
eq.grid_panel(b, (-HX + KT, -HY + KT, ZG), (1, 0, 0), (0, 1, 0), 2 * (HX - KT), 2 * (HY - KT), pitch=0.04, bw=0.011, mesh="galv_t")
for sx in (-1, 1):
    for sy in (-1, 1):
        xe, ye = sx * (HX - 0.07), sy * (HY - KT / 2)      # lifting eye: a plate, its hole baked
        b.prism("eye", (xe, ye, ZK), (1, 0, 0), (0, 0, 1), [(-0.045, 0), (0.045, 0), (0.045, 0.05), (0.02, 0.085), (-0.02, 0.085), (-0.045, 0.05)], -0.008, 0.008, mat=Y + "_t", skip_side=(0,))
        b.cyl("d_eye", (xe, ye - 0.0095, ZK + 0.048), (xe, ye + 0.0095, ZK + 0.048), 0.017, n=12, mat="dark", detail=True)
        for k in range(3):      # kerb fixing bolts and corner welds (bake only)
            b.bolt((sx * (0.25 + 0.2 * k), sy * HY, 0.05), (0, sy, 0), r=0.012, mat=ST)
            b.bolt((sx * HX, sy * (0.25 + 0.2 * k), 0.05), (sx, 0, 0), r=0.012, mat=ST)
        b.weld((sx * HX, sy * (HY - KT), 0.02), (sx * HX, sy * (HY - KT), ZK - 0.02), mat=Y)


def pair(zc, r0=0.2, under=True):
    """Two studded flanges back to back on the vertical bore, nuts both sides."""
    b.lathe("flange", [(r0, zc - 0.065), (RF, zc - 0.065), (RF, zc + 0.065), (r0, zc + 0.065)], n=N, mat=GR, phase=0.0)
    b.lathe("d_joint", [(RF + 0.0006, zc - 0.005), (RF + 0.0006, zc + 0.005)], n=N, mat="dark", detail=True, phase=0.0)      # the ring gasket gap
    pw.bolts(b, RBC, NB, NR, [(zc + 0.065, 1)], True, ST)
    pw.bolts(b, RBC, NB, NR, [(zc - 0.065, -1)], under, ST, h=None if under else 0.006)
    for i in range(NB):      # stud ends through the nuts (bake only)
        a = 2 * math.pi * (i + 0.5) / NB
        for sg in ((-1, 1) if under else (1,)):
            z = zc + sg * (0.065 + NR * 0.95)
            b.cyl("d_stud", (RBC * math.cos(a), RBC * math.sin(a), z - sg * 0.002), (RBC * math.cos(a), RBC * math.sin(a), z + sg * 0.005), NR * 0.5, n=8, mat=ST, caps=(False, True), detail=True)


def gate(c, stem, run, hr, hw, hs, rb, k, RW, real=True, nn=10):
    """Cast gate valve: a barrel-shaped body turned about the bore (half length hr, belly radius about hw), a neck
    out along 'stem' to the bonnet seat at hs, bonnet flange with its stud ring, gland, stem and spoked handwheel."""
    with at(b, frame(c, run, stem)):          # local Z = bore
        b.lathe("valve_body", [(hw * 0.76, -hr), (hw * 0.97, -hr * 0.66), (hw * 1.08, -hr * 0.24), (hw * 1.08, hr * 0.24), (hw * 0.97, hr * 0.66), (hw * 0.76, hr)], n=nn + 2, mat=GR, phase=0.0)
        if real:      # casting seam and a foundry boss (bake only)
            b.lathe("d_cast", [(hw * 1.082, -0.006), (hw * 1.088, 0.0), (hw * 1.082, 0.006)], n=(nn + 2) * 2, mat=GR, detail=True, phase=0.0)
    with at(b, frame(c, stem, run)):          # local Z = stem, local X = bore
        z1, z2, z3, z4 = hs + 0.04 * k, hs + 0.085 * k, hs + 0.16 * k, hs + 0.22 * k
        b.lathe("bonnet", [(rb * 0.92, hw * 0.55), (rb * 0.8, hs - 0.02 * k), (rb * 0.8, z1), (rb, z1), (rb, z2), (rb * 0.56, z2), (rb * 0.42, z3), (rb * 0.32, z3), (rb * 0.32, z4), (0, z4)], n=nn, mat=GR, phase=0.0)
        pw.bolts(b, rb * 0.79, 8, rb * 0.115, [(z2, 1)], real, ST)
        b.cyl("stem", (0, 0, z4), (0, 0, hs + 0.30 * k), rb * 0.13, n=6, mat=ST, caps=(False, True))
        b.lathe("d_gland", [(rb * 0.2, z4 - 0.002), (rb * 0.2, z4 + 0.004)], n=6, mat=ST, detail=True, cap_top=True)
    pw.handwheel(b, V(c) + V(stem) * (hs + 0.27 * k), stem, RW, mat=WH, n=12 if real else 10, m=4, spokes=3 if real else 2)


# ---------------- the vertical stack
b.lathe("wellhead", [(0.40, ZG), (0.40, ZG + 0.06), (0.30, ZG + 0.06), (0.27, ZG + 0.10), (0.25, ZG + 0.12), (0.25, 0.575)], n=N, mat=GR, phase=0.0)
pw.bolts(b, 0.35, 8, NR, [(ZG + 0.06, 1)], True, ST)
pair(0.64, 0.24, False)
b.lathe("tubing_head", [(0.235, 0.705), (0.262, 0.75), (0.262, 0.9), (0.235, 0.945)], n=N, mat=GR, phase=0.0)
pair(1.01, 0.23, False)
ZM1, ZM2, ZX = 1.255, 1.745, 2.22
gate((0, 0, ZM1), (0, -1, 0), (0, 0, 1), 0.18, 0.2, 0.25, 0.165, 1.0, 0.2)
pair(1.50, 0.15, False)
gate((0, 0, ZM2), (0, -1, 0), (0, 0, 1), 0.18, 0.2, 0.25, 0.165, 1.0, 0.2)
pair(1.99, 0.15, False)
XB, ZXH = 0.22, 0.165        # cross block half sizes
b.box("cross", (-XB, -0.2, ZX - ZXH), (XB, 0.2, ZX + ZXH), mat=GR, bev=0.03, skip="-z")
for sy in (-1, 1):            # blanking plate on the front and back of the cross block
    b.box("cross_plate", (-0.17, sy * 0.2 - (0.016 if sy < 0 else 0), ZX - 0.13), (0.17, sy * 0.2 + (0.016 if sy > 0 else 0), ZX + 0.13), mat=GT, bev=0.004, skip="+y" if sy < 0 else "-y")
for sy in (-1, 1):            # blind bosses front and back of the cross (bake only), corner studs
    for sx in (-1, 1):
        for sz in (-1, 1):
            if sy < 0: b.cyl("nut", (sx * 0.13, sy * 0.216, ZX + sz * 0.09), (sx * 0.13, sy * 0.236, ZX + sz * 0.09), 0.022, n=6, mat=ST, caps=(False, True))
            else: b.bolt((sx * 0.13, sy * 0.216, ZX + sz * 0.09), (0, sy, 0), r=0.02, mat=ST)

# ---------------- tree cap: flange, needle valve, pressure gauge (dial top = top of the box)
ZCAP = ZX + ZXH
b.lathe("cap", [(0.19, ZCAP - 0.002), (0.19, ZCAP + 0.045), (0.07, ZCAP + 0.045), (0.07, ZCAP + 0.06), (0.028, ZCAP + 0.06), (0.028, ZCAP + 0.066)], n=12, mat=GR, phase=0.0)
pw.bolts(b, 0.14, 8, 0.02, [(ZCAP + 0.045, 1)], False, ST)
RG = 0.055; ZGA = H - RG
b.cyl("gauge_stem", (0, 0, ZCAP + 0.06), (0, 0, ZGA - RG + 0.01), 0.014, n=6, mat="brass", caps=(False, False))
b.box("needle_valve", (-0.022, -0.022, ZCAP + 0.064), (0.022, 0.022, ZCAP + 0.098), mat=ST, bev=0.004)
b.cyl("needle_stem", (0.02, 0, ZCAP + 0.081), (0.085, 0, ZCAP + 0.081), 0.008, n=6, mat=ST, caps=(False, True))
b.box("needle_tee", (0.08, -0.03, ZCAP + 0.074), (0.092, 0.03, ZCAP + 0.088), mat=ST)
with at(b, frame((0, 0.022, ZGA), (0, -1, 0), (1, 0, 0))):
    b.lathe("gauge", [(RG * 0.9, 0.0), (RG, 0.004), (RG, 0.046), (RG * 0.9, 0.05), (0, 0.05)], n=12, mat=ST, phase=0.0, cap_bot=True)
    b.cyl("d_dial", (0, 0, 0.049), (0, 0, 0.0515), RG * 0.84, n=24, mat="paintw", caps=(False, True), detail=True)
    b.box("d_needle", (-0.004, -0.008, 0.0515), (0.004, RG * 0.7, 0.053), mat="black", detail=True)

# ---------------- wings off the cross: studded flanges, wing valve (handwheel up), choke at +X, blind cap at -X
RW_, RWB = 0.165, 0.128
for sx in (-1, 1):
    with at(b, frame((0, 0, ZX), (sx, 0, 0), (0, 0, 1))):          # local Z = outward along the wing
        b.lathe("wing", [(RW_, XB - 0.002), (RW_, 0.265), (0.1, 0.265), (0.1, 0.345), (RW_, 0.345), (RW_, 0.39), (0.11, 0.39)], n=10, mat=GR, phase=0.0)
        pw.bolts(b, RWB, 8, 0.017, [(0.265, 1), (0.345, -1)], False, ST)
        if sx > 0:      # choke: flange, body with its bean housing, end plug
            b.lathe("choke", [(0.11, 0.60), (RW_, 0.60), (RW_, 0.64), (0.105, 0.64), (0.105, 0.75), (0.085, 0.765), (0.085, 0.785), (0.05, 0.80), (0.0, 0.80)], n=12, mat=GR, phase=0.0)
            pw.bolts(b, RWB, 6, 0.019, [(0.64, 1)], True, ST)
        else:           # blind cap
            b.lathe("blind", [(0.11, 0.60), (RW_, 0.60), (RW_, 0.64), (RW_ - 0.01, 0.64), (RW_ - 0.01, 0.646), (RW_, 0.646), (RW_, 0.69), (0.0, 0.69)], n=12, mat=GR, phase=0.0)
            pw.bolts(b, RWB, 6, 0.019, [(0.69, 1)], False, ST)
    gate((sx * 0.495, 0, ZX), (0, 0, 1), (sx, 0, 0), 0.107, 0.125, 0.16, 0.1, 0.55, 0.11, real=False, nn=8)
# choke stem, indicator and T handle
XC = 0.7
b.lathe("choke_bonnet", [(0.075, ZX + 0.09), (0.075, ZX + 0.14), (0.05, ZX + 0.14), (0.04, ZX + 0.2), (0.022, ZX + 0.2), (0.022, ZX + 0.27), (0.0, ZX + 0.27)], n=8, mat=GR, at=(XC, 0, 0), phase=0.0)
b.box("choke_handle", (XC - 0.012, -0.11, ZX + 0.262), (XC + 0.012, 0.11, ZX + 0.286), mat=ST, bev=0.004)
b.box("d_scale", (XC - 0.0235, -0.012, ZX + 0.205), (XC - 0.0215, 0.012, ZX + 0.262), mat="brass", detail=True)

# ---------------- casing head outlets along X: neck, small gate valve, blind flange
DO = 0.11; ZO = 0.44
for sx in (-1, 1):
    pw.tube(b, "outlet", [(sx * 0.23, 0, ZO), (sx * 0.31, 0, ZO)], DO / 2, n=8, mat=GR)
    hl = 0.11
    gate((sx * 0.475, 0, ZO), (0, 0, 1), (sx, 0, 0), 0.085, 0.085, 0.11, 0.07, 0.6, 0.08, real=False, nn=6)
    for sg in (-1, 1):
        with at(b, frame((sx * (0.475 + sg * 0.097), 0, ZO), (sx, 0, 0))): b.lathe("oflange", [(0.06, -0.013), (0.1, -0.013), (0.1, 0.013), (0.06, 0.013)], n=8, mat=GT, phase=0.0)
    pw.flange(b, (sx * (0.475 + hl + 0.05), 0, ZO), (sx, 0, 0), DO, mat=GT, pair=False, blind=True, real=False, n=10)
# ---------------- tubing head outlets along Y: neck and blind flange, a bleed plug in it
ZT_ = 0.825
for sy in (-1, 1):
    pw.tube(b, "outlet", [(0, sy * 0.22, ZT_), (0, sy * 0.33, ZT_)], DO / 2, n=8, mat=GR)
    e = pw.flange(b, (0, sy * 0.33, ZT_), (0, sy, 0), DO, mat=GT, pair=False, blind=True, real=False, n=10)
    b.cyl("plug", (0, sy * (0.33 + e), ZT_), (0, sy * (0.33 + e + 0.03), ZT_), 0.022, n=6, mat=ST, caps=(False, True))

# ---------------- grime and grease
eq.run(b, (0, -0.2, ZM1 - 0.1), (0, -1, 0), 0.4, 0.5, (GR,), i=2, strength=0.5)
eq.run(b, (0.25, 0.0, 0.57), (1, 0.3, 0), 0.4, 0.35, (GR,), i=4, strength=0.5)
eq.run(b, (-0.495, -0.125, ZX), (0, -1, 0), 0.25, 0.3, (GR,), i=1, strength=0.5)
eq.run(b, (0.3, -HY, ZK), (0, -1, 0), 0.6, 0.3, (Y,), i=3, strength=0.4)
eq.run(b, (HX, 0.2, ZK), (1, 0, 0), 0.6, 0.3, (Y,), i=0, strength=0.4)
eq.run(b, (-0.2, HY, ZK), (0, 1, 0), 0.7, 0.3, (Y,), i=2, strength=0.4)

CLOSE = dict(sheet="xmas_tree_close1", shots=[
    dict(eye=(0, -2.6, 1.5), at=(0, 0, 1.5), lens=62), dict(eye=(-2.6, -0.2, 1.5), at=(0, -0.2, 1.5), lens=62), dict(eye=(0, -2.6, ZX), at=(0, 0, ZX), lens=62),
    dict(eye=(0.55, -2.4, ZX + 0.25), at=(0.5, 0, ZX + 0.05), lens=70), dict(eye=(0, -1.9, 2.6), at=(0, 0, 2.47), lens=80), dict(eye=(1.0, -2.0, 1.2), at=(0, 0, 0.45), lens=55)])
eq.tail(b, HERE, HX, HY, H, size=2048, close=CLOSE,
        over={"green": dict(tint=pw.tn(66, 96, 82), dirt=0.7, rust=0.45, edge=0.65, bias=0.0), "wheel": dict(edge=0.7, rust=0.45, bias=0.02), "yellow": dict(dirt=0.75, edge=0.6, low=0.7)},
        grunge={"green": dict(chips=0.7, streak=0.85, grime=0.65), "wheel": dict(chips=0.9), "yellow": dict(chips=0.75, streak=0.9)},
        front=dict(minus_y="master valve handwheels, gauge dial", plus_x="wing with the choke (T handle)", minus_x="wing with the blind cap", plus_y="backs of the valve bodies"))
