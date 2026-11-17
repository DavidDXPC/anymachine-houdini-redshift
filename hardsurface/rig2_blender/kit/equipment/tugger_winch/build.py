# tugger_winch: air tugger winch.  1.6 (X) x 1.1 (Y) x 1.1 (Z), origin centre of the footprint on the floor.  The mesh
# guard faces -Y and up, the solid guard plate faces +Y; gearcase, air motor and levers at the +X end.
# Hand-modelled from sheets/tugger_winch_turn.png, _detail.png and _close1.png.
#   base frame on a flange plate with eight hold-down nuts; two arched, ribbed side frames with bearing covers and a
#   lifting eye each; the drum and its wire rope are seen through the guard, which is an OPAQUE hood here (cover): mesh
#   and rope are baked on it, front and top, with a solid plate on the back; arched gearcase with a round cover, air
#   motor across the end, valve chest, exhaust silencer, air pipe, control valve with its lever, the long brake lever.
#   blender -b --factory-startup -t 4 --python build.py [-- --nobake] [--size 1024] [--spp 24] [--noreview]
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import _eq as eq
from _eq import pw, V, T, at, frame
from mathutils import Matrix
b = eq.new("tugger_winch")
HX, HY, H = 0.8, 0.55, 1.1
ZB = 0.14                        # base top
ZC = 0.53                        # drum axis
RA, RG = 0.5, 0.486               # side frame arch, guard hood
XL0, XL1, XR0, XR1 = -0.76, -0.68, 0.18, 0.26       # side frames
O, Yw, G, ST = "orange", "yellow", "grey", "steel"


def arch(hw, zs, r, k=8):         # outline in (y, z): feet on ZB, upright to zs, half round of radius r = hw on top
    return [(-hw, ZB), (hw, ZB)] + [(hw * math.cos(math.pi * i / k), zs + r * math.sin(math.pi * i / k)) for i in range(k + 1)]


# ---------------- base: flange plate, frame, hold-down nuts, gussets
b.box("flange", (-HX, -HY, 0.0), (HX, HY, 0.03), mat=O, bev=0.005, skip="-z")
b.box("base", (-HX + 0.07, -HY + 0.07, 0.03), (HX - 0.07, HY - 0.07, ZB), mat=O, bev=0.008, skip="-z")
for sx in (-1, 1):
    for sy in (-1, 1):
        for fx in (1.0, 0.36):
            q = (sx * (HX - 0.035) * fx, sy * (HY - 0.035), 0.03)
            b.cyl("nut", q, (q[0], q[1], 0.062), 0.026, n=6, mat=ST, caps=(False, True))
            b.cyl("stud", (q[0], q[1], 0.062), (q[0], q[1], 0.078), 0.014, n=6, mat=ST, caps=(False, True))
            b.box("d_washer", (q[0] - 0.034, q[1] - 0.034, 0.029), (q[0] + 0.034, q[1] + 0.034, 0.035), mat=ST, detail=True)
    for y in (-0.3, 0.0, 0.3):
        b.prism("gusset", (sx * (HX - 0.07), y, 0.03), (sx, 0, 0), (0, 0, 1), [(0, 0), (0.06, 0), (0, 0.09)], -0.008, 0.008, mat=O + "_t", skip_side=(2,))
for sy in (-1, 1):
    for x in (-0.55, -0.1, 0.5):
        b.prism("gusset", (x, sy * (HY - 0.07), 0.03), (0, sy, 0), (0, 0, 1), [(0, 0), (0.06, 0), (0, 0.09)], -0.008, 0.008, mat=O + "_t", skip_side=(2,))
    b.weld((-HX + 0.08, sy * (HY - 0.07), 0.031), (HX - 0.08, sy * (HY - 0.07), 0.031), mat=O)

# ---------------- side frames (arched plates), lifting eyes
for x0, x1 in ((XL0, XL1), (XR0, XR1)):
    b.prism("frame", (0, 0, 0), (0, 1, 0), (0, 0, 1), arch(RA, ZC, RA), x0, x1, mat=O, caps=(True, True), bev=0.006, skip_side=(0,))
    pw.lug(b, "eye", ((x0 + x1) / 2, 0.0, ZC + RA - 0.006), (0, 1, 0), 0.07, H - ZC - RA + 0.006, 0.03, 0.018, 0.04, 0.03, mat=O + "_t")
# outer face of the -X frame: bearing cover with its nuts, ribs
with at(b, frame((XL0, 0, ZC), (-1, 0, 0), (0, -1, 0))):      # local X = -Y, local Y = up, local Z = out
    b.lathe("cover", [(0.17, 0.0), (0.17, 0.024), (0.115, 0.024), (0.105, 0.04), (0.0, 0.04)], n=16, mat=O, phase=0.0)
    pw.bolts(b, 0.142, 8, 0.016, [(0.024, 1)], True, ST)
    b.cyl("d_nipple", (0, 0, 0.04), (0, 0, 0.046), 0.012, n=6, mat=ST, caps=(False, True), detail=True)
    for sg in (-1, 1):
        x0, x1 = sorted((sg * 0.17, sg * 0.45))
        b.box("rib", (x0, -0.135, 0.0), (x1, -0.105, 0.025), mat=O + "_t", skip="-z")
        with at(b, Matrix.Rotation(math.radians(-90 - sg * 38), 4, "Z")):
            b.box("rib", (0.17, -0.015, 0.0), (0.5, 0.015, 0.025), mat=O + "_t", skip="-z,+x")
    b.box("rib", (-0.015, 0.17, 0.0), (0.015, 0.44, 0.025), mat=O + "_t", skip="-z")
    b.box("rib", (-0.45, -0.41, 0.0), (0.45, -0.38, 0.025), mat=O + "_t", skip="-z")
    for a in range(0, 181, 20):   # rim bolts round the arch (bake only)
        b.bolt((0.46 * math.cos(math.radians(a)), 0.46 * math.sin(math.radians(a)), 0.0), (0, 0, 1), r=0.009, mat=ST)

# ---------------- guard hood between the frames: mesh on the front and top (opaque: the drum and rope are baked behind
# it), solid plate on the back, a solid kick band low on the front
W = XR0 - XL1
KS = 8
P = lambda a: V((XL1, RG * math.cos(math.radians(a)), ZC + RG * math.sin(math.radians(a))))
segs = [(V((XL1, -RG, 0.32)), V((XL1, -RG, ZC)))] + [(P(180 - 180 * i / KS), P(180 - 180 * (i + 1) / KS)) for i in range(KS)] + [(V((XL1, RG, ZC)), V((XL1, RG, ZB)))]
for i, (p, q) in enumerate(segs):
    ey = (q - p); h = ey.length; ey = ey / h; n = V((1, 0, 0)).cross(ey)
    mesh = i <= 6
    if mesh:
        backs = [(0, W, 0, h, "rope"), (0.0, 0.035, 0, h, O), (W - 0.035, W, 0, h, O)]
        eq.grid_panel(b, p, (1, 0, 0), ey, W, h, pitch=0.048, bw=0.007, mesh=Yw + "_t", backs=backs)
        with at(b, frame(p, n, (1, 0, 0))):
            for j in range(1, 40):   # the rope turns behind the mesh
                u = 0.04 + (W - 0.08) * j / 40; b.box("d_turn", (u - 0.003, 0, 0.0009), (u + 0.003, h, 0.0013), mat="void", skip="-z,-y,+y", detail=True)
    else:
        eq.quad(b, "guard_back", p, (1, 0, 0), ey, W, h, Yw)
    with at(b, frame(p, n, (1, 0, 0))):
        for u0 in (0.0, W - 0.055):   # hoop bands at the two ends
            b.box("band", (u0, 0, 0.0), (u0 + 0.055, h, 0.012), mat=Yw, skip="-z,-y,+y")
        if i in (0, 1, 4, 7, 9): b.box("d_bar", (0.055, -0.02, 0.0004), (W - 0.055, 0.02, 0.005), mat=Yw, detail=True, bev=0.002)
        if not mesh:
            for u in (0.1, W / 2, W - 0.1): b.bolt((u, h * 0.5, 0.0), (0, 0, 1), r=0.008, mat=ST)
eq.quad(b, "guard_kick", (XL1, -RG, ZB), (1, 0, 0), (0, 0, 1), W, 0.32 - ZB, Yw)
b.box("d_bar", (XL1 + 0.055, -RG - 0.005, 0.3), (XR0 - 0.055, -RG, 0.34), mat=Yw, detail=True, bev=0.002)
for x in (XL1 + 0.16, XR0 - 0.16):      # hinges on the back, at the top of the solid plate
    b.box("hinge", (x - 0.05, 0.3, ZC + 0.375), (x + 0.05, 0.36, ZC + 0.415), mat=Yw + "_t", bev=0.004, skip="-z")
for u in (0.1, W / 2, W - 0.1): b.bolt((XL1 + u, -RG, 0.22), (0, -1, 0), r=0.008, mat=ST)

# ---------------- gearcase at the +X end: arched case, round cover, pedestal ribs
XG = 0.56
b.prism("gearcase", (0, 0, 0), (0, 1, 0), (0, 0, 1), arch(0.36, 0.5, 0.36), XR1, XG, mat=O, caps=(False, True), bev=0.008, skip_side=(0,))
with at(b, frame((XG, -0.15, 0.52), (1, 0, 0), (0, 1, 0))):
    b.lathe("gear_cover", [(0.16, 0.0), (0.16, 0.022), (0.1, 0.022), (0.09, 0.034), (0.0, 0.034)], n=14, mat=O, phase=0.0)
    pw.bolts(b, 0.132, 8, 0.013, [(0.022, 1)], True, ST)
for y in (-0.3, 0.3):
    b.prism("case_rib", (XG, y, ZB), (1, 0, 0), (0, 0, 1), [(0, 0), (0.14, 0), (0, 0.22)], -0.012, 0.012, mat=O + "_t", skip_side=(2,))

# ---------------- air motor across the end, valve chest, silencer, air pipe, control valve and lever
XM, ZM = 0.68, 0.5
b.box("chest", (XG, -0.2, ZM - 0.11), (XM + 0.1, -0.02, ZM + 0.11), mat=O, bev=0.008, skip="-x")
with at(b, frame((XM, -0.02, ZM), (0, 1, 0), (1, 0, 0))):
    b.lathe("motor", [(0.118, 0.0), (0.118, 0.03), (0.105, 0.03), (0.105, 0.36), (0.112, 0.36), (0.112, 0.4), (0.09, 0.43), (0.0, 0.43)], n=12, mat=G, phase=0.0)
    pw.bolts(b, 0.085, 6, 0.011, [(0.43, 1)], False, ST)
    for i in range(6): b.lathe("d_band", [(0.1052, 0.07 + i * 0.05), (0.109, 0.074 + i * 0.05), (0.109, 0.086 + i * 0.05), (0.1052, 0.09 + i * 0.05)], n=12, mat=G, detail=True, phase=0.0)
b.box("motor_foot", (XM - 0.08, 0.06, ZB), (XM + 0.08, 0.3, ZM - 0.09), mat=O + "_t", skip="-z,+z")
with at(b, T(V((XM + 0.04, -0.11, 0.0)))):
    b.lathe("silencer", [(0.018, ZM - 0.11), (0.018, 0.36), (0.042, 0.35), (0.042, 0.2), (0.03, 0.185), (0.0, 0.185)][::-1], n=8, mat=ST, phase=0.0)
pts = pw.route([(XM - 0.04, -0.11, ZM + 0.11), (XM - 0.04, -0.11, 0.78), (XM - 0.04, 0.2, 0.78), (XM - 0.04, 0.2, ZM + 0.1)], 0.05, k=2)
pw.tube(b, "air_pipe", pts, 0.022, n=6, mat=ST)
for p, a in (((XM - 0.04, -0.11, ZM + 0.11), (0, 0, 1)), ((XM - 0.04, 0.2, ZM + 0.1), (0, 0, 1)), ((XM - 0.04, 0.04, 0.78), (0, 1, 0))):
    b.cyl("union", V(p), V(p) + V(a) * 0.04, 0.032, n=6, mat=ST)
b.box("valve", (XM - 0.03, -0.34, ZM - 0.02), (XM + 0.09, -0.2, ZM + 0.1), mat=G, bev=0.006, skip="+y")
pw.tube(b, "ctl_lever", [(XM + 0.03, -0.27, ZM + 0.1), (XM + 0.03, -0.3, 0.84)], 0.012, n=5, mat=ST)
kn = lambda c, r: [(r * math.sin(math.pi * i / 6), c - r * math.cos(math.pi * i / 6)) for i in range(7)]
with at(b, T(V((XM + 0.03, -0.3, 0.0)))): b.lathe("knob", kn(0.865, 0.03), n=8, mat="black", phase=0.0)

# ---------------- brake lever on the +X side frame: pivot, quadrant, lever, knob (the top of the box)
PV = V((XR1 + 0.05, -0.38, 0.62)); TP = V((XR1 + 0.19, -0.38, H - 0.07))
b.cyl("pivot", (XR0 + 0.02, PV.y, PV.z), (XR1 + 0.1, PV.y, PV.z), 0.055, n=10, mat=O, caps=(False, True))
b.cyl("pivot_pin", (XR1 + 0.1, PV.y, PV.z), (XR1 + 0.115, PV.y, PV.z), 0.022, n=6, mat=ST, caps=(False, True))
pw.bar(b, "brake_lever", PV + V((0.03, 0, 0)), TP, pw.P_box(0.03, 0.045), up=(1, 0, 0), mat=O + "_t")
with at(b, T(V((TP.x, TP.y, 0.0)))): b.lathe("knob", kn(H - 0.036, 0.036), n=8, mat="black", phase=0.0)

# ---------------- grease and grime
eq.run(b, (XL0, 0.0, ZC - 0.15), (-1, 0, 0), 0.35, 0.4, (O,), i=2, strength=0.6)
eq.run(b, (XG, -0.15, 0.38), (1, 0, 0), 0.3, 0.3, (O,), i=1, strength=0.6)
eq.puddle(b, (0.66, 0.0, ZB), 0.3, (O,), strength=0.6)
eq.run(b, (-0.25, RG, ZC), (0, 1, 0), 0.5, 0.4, (Yw,), i=4, strength=0.4)

eq.tail(b, HERE, HX, HY, H, size=1024, over={"grey": dict(tint=pw.tn(84, 104, 122)), "rope": dict(value=0.42, tint=(1.0, 0.9, 0.78))},
        front=dict(minus_y="mesh guard over the drum, brake lever and control valve at the right", plus_y="solid yellow guard plate", plus_x="gearcase, air motor, levers", minus_x="ribbed side frame with bearing cover"))
