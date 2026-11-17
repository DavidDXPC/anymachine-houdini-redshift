# heat_exchanger: shell-and-tube exchanger on two saddles.  4.2 (X) x 1.2 (Y) x 1.9 (Z), origin centre of the footprint
# on the floor, nameplate faces -Y, flat channel cover at -X, dished bonnet at +X.
# Hand-modelled from sheets/heat_exchanger_turn.png, _detail.png and _close1.png.
#   shell 1.0 m over its ribbed aluminium cladding (ribs and grooves baked, four stainless bands with buckles), axis
#   0.90 m up (lower than the sheet, so the piece is cover); three girth joints 1.2 m across (the width of the box),
#   20 studs with nuts each side: flat channel cover, channel to shell, shell to bonnet; two top nozzles through
#   flashing collars, each with a flange and a blind cover (the nuts on the covers are the top of the box); two bottom
#   nozzles with blind covers; saddles: wear plate, web, three ribs a side, base plate, four anchor bolts; a skid of two
#   channel rails, end beams and a drip plate, with a tie plate on the centre line between the saddles (it and the
#   skid close the space under the shell); drains under channel and bonnet; lifting lugs; nameplate on a bracket.
#   blender -b --factory-startup -t 4 --python build.py [-- --nobake] [--size 2048] [--spp 24] [--noreview]
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import _eq as eq
from _eq import pw, V, T, at, frame
b = eq.new("heat_exchanger")
HX, HY, H = 2.1, 0.6, 1.9
ZC = 0.90
RS, RF, RCH, RN, RB = 0.50, 0.60, 0.46, 0.45, 0.46     # cladding, girth flanges, channel barrel, shell neck, bonnet
N = 24; NB = 20; NR = 0.03; NH = NR * 0.95; RBC = 0.546
ZP = 0.14                                              # skid top
TF = 0.055                                             # flange thickness
W, G, AL, ALD, ST = "lgrey", "lgrey_t", "alu", "alud", "stainless"
XC0 = -HX + NH                # outer face of the channel cover (the nuts on it are the -X face of the box)
XJ = -1.60                    # channel / shell joint plane
XB = 1.60                     # shell / bonnet joint plane
XL0, XL1 = -1.47, 1.47        # cladding
XT = 1.80                     # bonnet tangent
ALONG = frame((0, 0, ZC), (1, 0, 0), (0, 0, 1))        # local Z = +X, local X = up, local Y = -Y

with at(b, ALONG):
    # channel: cover, channel flange, barrel, flange pair, shell neck into the cladding
    ch = [(0.0, XC0), (RF, XC0), (RF, XC0 + 0.115), (RCH + 0.04, XC0 + 0.115), (RCH, XC0 + 0.16), (RCH, XJ - 0.10), (RCH + 0.04, XJ - TF),
          (RF, XJ - TF), (RF, XJ + TF), (RN + 0.04, XJ + TF), (RN, XJ + 0.10), (RN, XL0)]
    b.lathe("channel", ch, n=N, mat=W, phase=0.0)
    bn = [(RN, XL1), (RN, XB - 0.10), (RN + 0.04, XB - TF), (RF, XB - TF), (RF, XB + TF), (RB + 0.04, XB + TF), (RB, XB + 0.10), (RB, XT)] + pw.head(RB, HX - XT, 5, XT, 1)[1:]
    b.lathe("bonnet", bn, n=N, mat=W, phase=0.0)
    PLANES = [(XC0, -1), (XC0 + 0.115, 1), (XJ - TF, -1), (XJ + TF, 1), (XB - TF, -1), (XB + TF, 1)]
    pw.bolts(b, RBC, NB, NR, PLANES, True, "steel")
    for i in range(NB):        # bake only: stud ends standing out of the nuts, washers under them
        a = 2 * math.pi * (i + 0.5) / NB; x, y = RBC * math.cos(a), RBC * math.sin(a)
        for z, sg in PLANES:
            z0, z1 = sorted((z + sg * (NH - 0.001), z + sg * (NH + 0.0055)))
            b.cyl("d_stud", (x, y, z0), (x, y, z1), 0.013, n=10, mat="steel", caps=(sg < 0, sg > 0), detail=True)
            z0, z1 = sorted((z - sg * 0.001, z + sg * 0.003))
            b.cyl("d_washer", (x, y, z0), (x, y, z1), NR * 1.3, n=14, mat="steel", caps=(sg < 0, sg > 0), detail=True)
    for x in (XC0 + 0.06, XJ, XB):       # the joint faces: a dark gasket line round each flange pair
        b.lathe("d_gap", [(RF + 0.0006, x - 0.004), (RF + 0.0006, x + 0.004)], n=N, mat="dark", detail=True, phase=0.0)
        for sg in (-1, 1): b.lathe("d_face", [(RF + 0.0004, x + sg * 0.006), (RF + 0.002, x + sg * 0.012), (RF + 0.0004, x + sg * 0.018)][::sg], n=N, mat=W, detail=True, phase=0.0)
    b.lathe("cladding", [(RN, XL0), (RS, XL0), (RS, XL1), (RN, XL1)], n=N, mat=AL, phase=0.0)
    XBAND = (-1.36, -0.46, 0.46, 1.36)
    for x in XBAND:
        b.lathe("band", [(RS + 0.005, x - 0.032), (RS + 0.005, x + 0.032)], n=N, mat=ST, phase=0.0)
    # bake only: the cladding's ribs (four to a facet) with dark grooves between, sheet laps, a lap seam with rivets, band buckles, welds
    ra = RS * math.cos(math.pi / N); fw = 2 * RS * math.sin(math.pi / N)
    for i in range(N):
        th = 2 * math.pi * (i + 0.5) / N
        with at(b, frame((ra * math.cos(th), ra * math.sin(th), 0), (math.cos(th), math.sin(th), 0), (0, 0, 1))):      # local X along the shell
            for k in range(4):
                y = (k - 1.5) * fw / 4
                b.box("d_rib", (XL0 + 0.004, y - 0.011, -0.003), (XL1 - 0.004, y + 0.011, 0.0034), mat=AL, detail=True, bev=0.004, bev_axes="x")
                b.box("d_groove", (XL0 + 0.004, y + 0.011, -0.003), (XL1 - 0.004, y + fw / 4 - 0.011, 0.0004), mat=ALD, detail=True)
            if i == 2:
                for k in range(30): b.rivet((XL0 + 0.05 + k * 0.098, fw / 2 - 0.012, 0.0036), (0, 0, 1), r=0.006, mat=AL)
            if i in (17, 18, 5, 6):          # front (-Y) and back: a buckle on each band, with its tail
                side = -1 if i in (17, 5) else 1
                for x in XBAND:
                    if side > 0: b.box("d_buckle", (x - 0.026, -fw / 2 - 0.0, 0.0052), (x + 0.026, -fw / 2 + 0.05, 0.0105), mat=ST, detail=True, bev=0.002)
                    else: b.box("d_tail", (x - 0.02, fw / 2 - 0.09, 0.0052), (x + 0.02, fw / 2, 0.0075), mat=ST, detail=True)
    for x in (-0.49, 0.49):        # laps between the cladding sheets
        b.lathe("d_lap", [(RS + 0.0036, x - 0.012), (RS + 0.0046, x - 0.008), (RS + 0.0046, x + 0.0), (RS + 0.0005, x + 0.003)], n=N, mat=AL, detail=True, phase=0.0)
        b.lathe("d_lapline", [(RS + 0.0006, x + 0.003), (RS + 0.0006, x + 0.009)], n=N, mat=ALD, detail=True, phase=0.0)
    for x in (XC0 + 0.16, XJ - 0.10, XB + 0.10):
        b.torus("d_weld", (0, 0, x), RCH + 0.002, 0.007, n=N * 2, m=6, mat=W, detail=True, squash=0.6)
    b.torus("d_weld", (0, 0, XT), RB + 0.001, 0.006, n=N * 2, m=6, mat=W, detail=True, squash=0.6)

# lifting lugs on the channel cover flange and on the bonnet
pw.lug(b, "lug", (XC0 + 0.03, 0, ZC + RF - 0.012), (0, 1, 0), 0.07, 0.15, 0.05, 0.028, 0.095, 0.022, mat=G)
pw.lug(b, "lug", (XT + 0.02, 0, ZC + RB - 0.012), (1, 0, 0), 0.07, 0.14, 0.05, 0.026, 0.09, 0.022, mat=G)

# ---------------- nozzles: neck through a flashing collar, flange and blind cover with studs
DT = 0.26; SP = pw.spec(DT)
LT = H - (ZC + RS - 0.02) - 0.006 - SP["t"] - SP["nr"] * 0.95        # so the nuts on the top covers are the top of the box
for x in (-1.0, 1.0):
    p = (x, 0, ZC + RS - 0.02)
    pw.nozzle(b, p, (0, 0, 1), DT, LT, mat=W, real=True, blind=True, n=12, embed=0.0)
    with at(b, T(V((x, 0, 0)))):
        b.lathe("collar", [(DT / 2 + 0.085, ZC + RS - 0.05), (DT / 2 + 0.03, ZC + RS + 0.03), (DT / 2 + 0.001, ZC + RS + 0.05)], n=12, mat=AL, phase=0.0)
        for i in range(12):
            a = 2 * math.pi * (i + 0.5) / 12; r = DT / 2 + 0.05
            b.rivet((r * math.cos(a), r * math.sin(a), ZC + RS + 0.001), (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.83), r=0.007, mat=AL)
        b.torus("d_weld", (0, 0, ZC + RS + 0.052), DT / 2 + 0.002, 0.006, n=24, m=6, mat=W, detail=True, squash=0.7)
XN = (-0.5, 0.5); ZNB = ZC - RS + 0.02
for x in XN:
    pw.nozzle(b, (x, 0, ZNB), (0, 0, -1), DT, 0.10, mat=W, real=False, blind=True, n=12, embed=0.0)
    with at(b, T(V((x, 0, 0)))):
        b.lathe("collar_b", [(DT / 2 + 0.001, ZC - RS - 0.05), (DT / 2 + 0.03, ZC - RS - 0.03), (DT / 2 + 0.085, ZC - RS + 0.05)], n=12, mat=AL, phase=0.0)
ZNE = ZNB - 0.10 - 0.006 - SP["t"]            # underside of the bottom covers

# ---------------- saddles: wear plate, web, ribs, base plate, anchor bolts
XS = (-1.0, 1.0); RW = RS + 0.012; ZB = ZP + 0.03; ANG = 60; K = 8
for n_, x in enumerate(XS):
    a0 = math.radians(ANG)
    arc = lambda r, k0, k1: [(r * math.sin(a0 * (2 * i / K - 1)), ZC - r * math.cos(a0 * (2 * i / K - 1))) for i in range(k0, k1, 1 if k1 > k0 else -1)]
    wear = arc(RW, 0, K + 1) + arc(RS - 0.003, K, -1)
    b.prism("wear_plate", (x, 0, 0), (0, 1, 0), (0, 0, 1), wear, -0.2, 0.2, mat=G, skip_side=tuple(range(K + 1, 2 * K + 1)))
    ya, za = RW * math.sin(a0 * 0.92), ZC - RW * math.cos(a0 * 0.92)
    web = [(-0.46, ZB), (0.46, ZB), (0.46, za - 0.03), (ya, za)] + [(RW * 0.999 * math.sin(a0 * 0.92 * (1 - 2 * i / K)), ZC - RW * 0.999 * math.cos(a0 * 0.92 * (1 - 2 * i / K))) for i in range(1, K)] + [(-ya, za), (-0.46, za - 0.03)]
    b.prism("web", (x, 0, 0), (0, 1, 0), (0, 0, 1), web, -0.014, 0.014, mat=G, skip_side=tuple(range(3, 3 + K)) + (0,))
    b.box("base_plate", (x - 0.2, -0.53, ZP), (x + 0.2, 0.53, ZB), mat=G, bev=0.004, skip="-z")
    for sx in (-1, 1):
        for y in (-0.32, 0.0, 0.32):
            zt = ZC - math.sqrt(RW * RW - y * y) + 0.002
            x0, x1 = sorted((x + sx * 0.014, x + sx * 0.17))
            b.box("rib", (x0, y - 0.008, ZB), (x1, y + 0.008, zt), mat=G, skip="-z,+z,%sx" % ("-" if sx > 0 else "+"))
            b.weld((x0 if sx > 0 else x1, y - 0.009, ZB + 0.003), (x1 if sx > 0 else x0, y - 0.009, ZB + 0.003), mat=W)
        b.weld((x + sx * 0.015, -0.45, ZB + 0.003), (x + sx * 0.015, 0.45, ZB + 0.003), mat=W)
        for sy in (-1, 1):
            q = (x + sx * 0.14, sy * 0.48, ZB)
            b.cyl("anchor_nut", q, (q[0], q[1], ZB + 0.024), 0.024, n=6, mat="steel", caps=(False, True))
            b.cyl("d_anchor_stud", (q[0], q[1], ZB + 0.023), (q[0], q[1], ZB + 0.0295), 0.012, n=10, mat="steel", caps=(False, True), detail=True)
            b.cyl("d_anchor_washer", (q[0], q[1], ZB - 0.001), (q[0], q[1], ZB + 0.004), 0.038, n=14, mat="steel", caps=(False, True), detail=True)
            if n_:          # the sliding saddle: slotted holes
                b.box("d_slot", (q[0] - 0.05, q[1] - 0.014, ZB - 0.001), (q[0] + 0.05, q[1] + 0.014, ZB + 0.0006), mat="dark", detail=True)

# ---------------- skid: two channel rails (toes out), end beams, cross members under the saddles, drip plate
XK = 2.04; ZD = 0.1
for sy in (-1, 1):
    y0, y1 = sorted((sy * HY, sy * (HY - 0.085)))
    b.box("rail_top", (-XK + 0.1, y0, ZP - 0.016), (XK - 0.1, y1, ZP), mat="grey", skip="-x,+x")
    b.box("rail_bot", (-XK + 0.1, y0, 0.0), (XK - 0.1, y1, 0.016), mat="grey", skip="-x,+x,-z")
    yw = sy * (HY - 0.07)
    eq.quad(b, "rail_web", (-XK + 0.1 if sy < 0 else XK - 0.1, yw, 0.016), (-sy, 0, 0), (0, 0, 1), 2 * XK - 0.2, ZP - 0.032, "grey")
    for x in (-1.6, -0.55, 0.55, 1.6):       # web stiffeners in the channel, drain holes (bake only)
        b.box("d_stiff", (x - 0.005, min(yw, yw + sy * 0.004), 0.016), (x + 0.005, max(yw, yw + sy * 0.004), ZP - 0.016), mat="grey", detail=True)
    for k in range(10): b.bolt((-1.8 + k * 0.4, sy * (HY - 0.035), ZP), (0, 0, 1), r=0.011, mat="steel")
    for sx in (-1, 1):
        b.box("d_padeye", (sx * (XK - 0.05) - 0.04, sy * HY - 0.004, 0.03), (sx * (XK - 0.05) + 0.04, sy * HY + 0.004, 0.11), mat="grey", detail=True, bev=0.002)
        b.cyl("d_padhole", (sx * (XK - 0.05), sy * (HY + 0.0041), 0.07), (sx * (XK - 0.05), sy * (HY + 0.0046), 0.07), 0.018, n=12, mat="dark", caps=(True, True), detail=True)
for sx in (-1, 1):
    x0, x1 = sorted((sx * XK, sx * (XK - 0.1)))
    b.box("end_beam", (x0, -HY, 0.0), (x1, HY, ZP), mat="grey", skip="-z", bev=0.006)
for x in XS:
    b.box("cross", (x - 0.2, -HY + 0.085, ZD), (x + 0.2, HY - 0.085, ZP), mat="grey", skip="-y,+y,-z")
b.box("drip", (-XK + 0.1, -HY + 0.07, ZD - 0.01), (XK - 0.1, HY - 0.07, ZD), mat="grey", skip="-x,+x,-y,+y,-z")
# tie plate on the centre line between the saddles, cut round the bottom nozzles
RFB = SP["R"] + 0.004
for x0, x1, z0, z1 in ((XS[0] + 0.014, XN[0] - RFB, ZD, ZC - RS + 0.004), (XN[0] + RFB, XN[1] - RFB, ZD, ZC - RS + 0.004), (XN[1] + RFB, XS[1] - 0.014, ZD, ZC - RS + 0.004),
                       (XN[0] - RFB, XN[0] + RFB, ZD, ZNE - 0.012), (XN[1] - RFB, XN[1] + RFB, ZD, ZNE - 0.012)):
    b.box("tie_plate", (x0, -0.009, z0), (x1, 0.009, z1), mat=G, skip="-z,-x,+x" + (",+z" if z1 > ZNE else ""))
for x in (-0.86, 0.0, 0.86):
    for sy in (-1, 1):
        b.box("d_tie_stiff", (x - 0.004, min(sy * 0.009, sy * 0.014), ZD), (x + 0.004, max(sy * 0.009, sy * 0.014), ZC - RS), mat=G, detail=True)

# ---------------- drains under the channel and the bonnet: stub, small valve with a red lever, plug
for x, r in ((XJ - 0.3, RCH), (XT - 0.08, RB)):
    zt = ZC - r
    b.cyl("drain", (x, 0, zt + 0.02), (x, 0, zt - 0.2), 0.03, n=8, mat="steel", caps=(False, True))
    b.box("drain_valve", (x - 0.045, -0.045, zt - 0.15), (x + 0.045, 0.045, zt - 0.07), mat="brass", bev=0.008)
    b.box("drain_lever", (x - 0.012, -0.2, zt - 0.122), (x + 0.012, -0.03, zt - 0.1), mat="wheel", bev=0.003)
    b.torus("d_weld", (x, 0, zt + 0.002), 0.031, 0.006, n=16, m=6, mat=W, detail=True)

# ---------------- nameplate on a stand-off bracket bolted through the cladding, front
with at(b, frame((0.0, -RS * math.cos(math.pi / N), ZC), (0, -1, 0), (1, 0, 0))):
    b.box("plate_foot", (-0.2, -0.11, 0.0), (-0.11, 0.11, 0.012), mat=G, skip="-z")
    b.box("plate_arm", (-0.165, -0.07, 0.012), (-0.135, 0.07, 0.05), mat=G, skip="-z,+z")
    b.box("nameplate", (-0.19, -0.1, 0.05), (0.2, 0.1, 0.058), mat=G, bev=0.002)
    b.box("d_plate_in", (-0.02, -0.08, 0.058), (0.18, 0.08, 0.0596), mat=ST, detail=True, bev=0.001)
    for i in range(5): b.box("d_plate_line", (0.0, 0.052 - i * 0.026, 0.0596), (0.16 - 0.03 * (i % 2), 0.056 - i * 0.026, 0.0602), mat="dark", detail=True)
    for sx in (-0.008, 0.168):
        for sy in (-1, 1): b.rivet((sx, sy * 0.068, 0.0596), (0, 0, 1), r=0.006, mat="steel")
    for sy in (-1, 1):
        b.bolt((-0.155, sy * 0.085, 0.012), (0, 0, 1), r=0.011, mat="steel")
        b.bolt((-0.15, sy * 0.06, 0.058), (0, 0, 1), r=0.009, mat="steel")

# ---------------- grime: rust runs down the cladding below the top nozzles, drips under the joints, oil in the skid
eq.run(b, (-1.0, -0.33, ZC + RS * 0.78), (0, -1, 0), 0.55, 0.8, (AL,), i=2, strength=0.5)
eq.run(b, (1.0, 0.33, ZC + RS * 0.78), (0, 1, 0), 0.55, 0.8, (AL,), i=4, strength=0.5)
eq.run(b, (1.0, -0.33, ZC + RS * 0.78), (0, -1, 0), 0.45, 0.75, (AL,), i=3, strength=0.45)
eq.run(b, (XC0, 0.1, ZC + 0.25), (-1, 0, 0), 0.5, 0.8, (W,), i=1, strength=0.28)
eq.run(b, (1.75, -RB, ZC + 0.1), (0, -1, 0), 0.3, 0.5, (W,), i=0, strength=0.5)
eq.puddle(b, (XJ - 0.3, 0.0, ZD), 0.7, ("grey",), strength=0.7)
eq.puddle(b, (XT - 0.1, 0.05, ZD), 0.6, ("grey",), strength=0.6)

ALU = dict(tint=(0.62, 0.65, 0.68), value=0.9, sat=0.1, metal=0.65, rough=0.38, rust=0.14, dirt=0.55, edge=0.04, low=0.2, tile=2.0, dent=0.4)
close = dict(sheet="heat_exchanger_close1", shots=[
    dict(eye=(-4.6, 0.0, 0.8), at=(-2.1, 0.0, 0.8), lens=50), dict(eye=(-1.7, -2.1, 1.05), at=(-1.7, -0.6, 1.05), lens=50),
    dict(eye=(1.7, -2.1, 1.05), at=(1.7, -0.6, 1.05), lens=50), dict(eye=(-1.0, -1.5, 1.75), at=(-1.0, 0.0, 1.58), lens=50),
    dict(eye=(-1.0, -1.9, 0.5), at=(-1.0, -0.5, 0.42), lens=50), dict(eye=(0.3, -1.45, 0.95), at=(0.3, -0.5, 0.95), lens=50)])
eq.tail(b, HERE, HX, HY, H, size=2048, close=close,
        over={"lgrey": dict(tint=pw.tn(150, 154, 154), value=1.0, dirt=0.7, rust=0.5, edge=0.6, bias=-0.02), "alu": ("pipe", ALU),
              "alud": ("pipe", dict(ALU, tint=(0.36, 0.37, 0.38), edge=0.0)), "stainless": dict(value=0.72), "steel": dict(value=0.62, rust=0.75, dirt=0.6), "grey": dict(dirt=0.8, rust=0.5)},
        grunge={"alu": dict(streak=0.9, grime=0.6), "lgrey": dict(chips=0.7, streak=0.85), "alud": dict(streak=0.0, grime=0.2, scuff=0.0)},
        front=dict(minus_y="nameplate on its bracket, drain valve levers", minus_x="flat bolted channel cover", plus_x="dished bonnet", plus_y="plain cladding and bands"))
