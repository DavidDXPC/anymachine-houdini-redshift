import math
from .. import equipment as eq
from ..equipment import pw, V, T, at, frame, Matrix
from ..geometry import Mesh

def build():
    b = eq.new("hpu")
    HX, HY, H = 1.1, 0.7, 1.7
    BL, S = "blue", "stainless"
    ZT = 0.16                                  # drip tray rim
    TX0, TX1, TY, TZ0, TZ1 = -0.84, 0.99, 0.58, 0.06, 1.0      # tank
    AX = (1, 0, 0)

    # ---------------- drip tray: outer wall, rim, well
    b.box("tray", (-HX, -HY, 0), (HX, HY, ZT), mat=BL, skip="-z,+z", bev=0.006, bev_axes="z")
    W = 0.03
    b.box("tray_well", (-HX + W, -HY + W, 0.05), (HX - W, HY - W, ZT), mat=BL, skip="+z", flip=True)
    eq.quad(b, "rim", (-HX + 0.006, -HY, ZT), (1, 0, 0), (0, 1, 0), 2 * HX - 0.012, W, BL)
    eq.quad(b, "rim", (-HX + 0.006, HY - W, ZT), (1, 0, 0), (0, 1, 0), 2 * HX - 0.012, W, BL)
    eq.quad(b, "rim", (-HX, -HY + W, ZT), (1, 0, 0), (0, 1, 0), W, 2 * HY - 2 * W, BL)
    eq.quad(b, "rim", (HX - W, -HY + W, ZT), (1, 0, 0), (0, 1, 0), W, 2 * HY - 2 * W, BL)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.bolt((sx * (HX - 0.12), sy * HY, 0.08), (0, sy, 0), r=0.012, mat="steel")
    for sy in (-1, 1): b.weld((-HX + 0.03, sy * (HY - W + 0.0), 0.052), (HX - 0.03, sy * (HY - W), 0.052), mat=BL)

    # ---------------- tank body, top plate, feet, corner eyes
    b.box("tank", (TX0, -TY, TZ0), (TX1, TY, TZ1 - 0.03), mat=BL, skip="-z,+z", bev=0.008, bev_axes="z")
    b.box("tank_top", (TX0 - 0.02, -TY - 0.02, TZ1 - 0.03), (TX1 + 0.02, TY + 0.02, TZ1), mat=BL, bev=0.005)
    for x in (TX0 + 0.2, TX1 - 0.2):
        for sy in (-1, 1):
            b.box("tank_foot", (x - 0.09, sy * TY - (0.0 if sy > 0 else 0.07), 0.05), (x + 0.09, sy * TY + (0.07 if sy > 0 else 0.0), 0.075), mat=BL, skip="-z" + (",-y" if sy > 0 else ",+y"))
            b.cyl("foot_nut", (x, sy * (TY + 0.04), 0.075), (x, sy * (TY + 0.04), 0.095), 0.016, n=6, mat="steel", caps=(False, True))
    for sx, x in ((-1, TX0 - 0.02), (1, TX1 + 0.02)):
        for sy in (-1, 1):
            with at(b, frame((x, sy * (TY - 0.06), TZ1 - 0.015), (0, 0, 1), (sx, 0, 0))):      # lifting eye lying flat off the top plate
                b.ring_plate("eye", (0, 0, 0), (1, 0, 0), (0, 1, 0),
                             [(0, -0.045), (0.035, -0.045), (0.065, -0.03), (0.075, 0.0), (0.065, 0.03), (0.035, 0.045), (0, 0.045), (0, 0.0)],
                             [(0.02, -0.014), (0.035, -0.02), (0.05, -0.014), (0.056, 0.0), (0.05, 0.014), (0.035, 0.02), (0.02, 0.014), (0.014, 0.0)], -0.012, 0.012, mat=BL + "_t", skip_outer=(6, 7))
    for sy in (-1, 1):         # bolted seam down the tank sides and a row of bolts under the top plate (bake only)
        for k in range(9):
            b.bolt((TX0 + 0.12 + k * (TX1 - TX0 - 0.24) / 8, sy * TY, TZ1 - 0.075), (0, sy, 0), r=0.011, mat="steel")
        b.weld((0.1, sy * (TY + 0.001), TZ0 + 0.12), (0.1, sy * (TY + 0.001), TZ1 - 0.11), mat=BL, r=0.004)

    # ---------------- front face: inspection cover, sight glass, filters, junction box, return pipe
    YF = -TY
    b.box("cover", (-0.72, YF - 0.012, 0.3), (-0.3, YF, 0.62), mat=BL + "_t", bev=0.004, skip="+y")
    for i in range(5):
        for z in (0.325, 0.595): b.bolt((-0.69 + i * 0.09, YF - 0.012, z), (0, -1, 0), r=0.011, mat="steel")
    for z in (0.4, 0.46, 0.52):
        for x in (-0.695, -0.325): b.bolt((x, YF - 0.012, z), (0, -1, 0), r=0.011, mat="steel")
    XG = -0.08
    b.box("sight", (XG - 0.035, YF - 0.035, 0.42), (XG + 0.035, YF, 0.84), mat="steel", bev=0.006, skip="+y")
    b.box("d_sight_glass", (XG - 0.016, YF - 0.037, 0.46), (XG + 0.016, YF - 0.034, 0.8), mat="pipe", detail=True)
    b.box("d_sight_oil", (XG - 0.016, YF - 0.0375, 0.46), (XG + 0.016, YF - 0.0345, 0.63), mat="yellow", detail=True)
    for z in (0.44, 0.82): b.bolt((XG, YF - 0.035, z), (0, -1, 0), r=0.009, mat="steel")
    FXS = (0.2, 0.36)
    b.box("filter_head", (FXS[0] - 0.08, YF - 0.118, 0.84), (FXS[1] + 0.08, YF, 0.93), mat=S, bev=0.005, skip="+y")
    for x in FXS:
        b.lathe("filter", [(0.0, 0.5), (0.02, 0.5), (0.02, 0.52), (0.05, 0.535), (0.058, 0.56), (0.058, 0.8), (0.064, 0.8), (0.064, 0.84)], n=10, mat="pipe", at=(x, YF - 0.055, 0), phase=0.0)
        b.cyl("filter_ind", (x, YF - 0.055, 0.93), (x, YF - 0.055, 0.965), 0.018, n=6, mat="brass", caps=(False, True))
        b.cyl("d_band", (x, YF - 0.055, 0.69), (x, YF - 0.055, 0.7), 0.0605, n=16, mat="steel", caps=(False, False), detail=True)
    b.box("jbox", (0.66, YF - 0.09, 0.52), (0.86, YF, 0.76), mat="lgrey", bev=0.006, skip="+y")
    b.box("d_jbox_lid", (0.675, YF - 0.094, 0.535), (0.845, YF - 0.089, 0.745), mat="lgrey", detail=True, bev=0.002)
    for sx in (-1, 1):
        for sz in (-1, 1): b.bolt((0.76 + sx * 0.07, YF - 0.094, 0.64 + sz * 0.09), (0, -1, 0), r=0.006, mat="steel")
    pw.tube(b, "jcable", pw.route([(0.72, YF - 0.045, 0.52), (0.72, YF - 0.045, 0.3), (0.72, YF - 0.0, 0.3)], 0.04, k=2), 0.012, n=5, mat="rubber")
    pw.tube(b, "jcable", pw.route([(0.8, YF - 0.045, 0.76), (0.8, YF - 0.045, TZ1 + 0.06), (0.8, YF + 0.12, TZ1 + 0.06)], 0.04, k=2), 0.012, n=5, mat="rubber")
    YR = YF - 0.05
    pw.tube(b, "return", pw.route([(FXS[0] - 0.08, YR, 0.885), (-0.78, YR, 0.885), (-0.78, YR, 0.24), (-0.78, YF + 0.01, 0.24)], 0.04, k=2), 0.02, n=8, mat=S)
    for x in (-0.2, -0.55):
        b.box("clip", (x - 0.02, YR - 0.024, 0.86), (x + 0.02, YF, 0.91), mat="steel", skip="+y")
    b.box("clip", (-0.805, YR - 0.024, 0.52), (-0.755, YF, 0.56), mat="steel", skip="+y")
    with at(b, frame((-0.78, YF, 0.24), (0, -1, 0))): b.lathe("return_boss", [(0.045, 0.0), (0.045, 0.02), (0.022, 0.03)], n=8, mat=BL, phase=0.0)

    # ---------------- back face: drain valve, nameplate
    with at(b, frame((0.6, TY, 0.22), (0, 1, 0), (1, 0, 0))):
        b.lathe("drain", [(0.04, 0.0), (0.04, 0.012), (0.024, 0.012), (0.024, 0.04), (0.034, 0.045), (0.034, 0.085), (0.0, 0.085)], n=8, mat="steel", phase=0.0)
    b.box("drain_handle", (0.59, TY + 0.05, 0.255), (0.72, TY + 0.07, 0.267), mat="wheel", bev=0.003)
    with at(b, frame((-0.3, TY, 0.7), (0, 1, 0), (-1, 0, 0))):
        b.box("d_plate", (-0.11, -0.07, 0), (0.11, 0.07, 0.004), mat="steel", detail=True, bev=0.002)
        for sx in (-1, 1):
            for sy in (-1, 1): b.rivet((sx * 0.095, sy * 0.055, 0.004), (0, 0, 1), r=0.006, mat="steel")

    # ---------------- top: motor, bellhousing, pump
    YM, ZM, RM = -0.08, TZ1 + 0.275, 0.2
    with at(b, frame((0, YM, ZM), AX, (0, 0, 1))):       # local Z along +X
        b.lathe("motor", [(0.0, -0.8), (0.17, -0.8), (RM + 0.012, -0.77), (RM + 0.012, -0.64), (RM, -0.64), (RM, -0.2), (RM + 0.03, -0.2), (RM + 0.03, -0.16)], n=16, mat=BL, phase=0.0)
        for k in range(16):       # cooling fins (bake only)
            with at(b, eq.RZ(360 * (k + 0.5) / 16)): b.box("d_fin", (RM - 0.001, -0.006, -0.62), (RM + 0.0055, 0.006, -0.22), mat=BL, detail=True)
        for k in range(7):        # fan cowl slots
            b.box("d_slot", (-0.12 + k * 0.04 - 0.008, -0.11, -0.803), (-0.12 + k * 0.04 + 0.008, 0.11, -0.8), mat="dark", detail=True)
        b.lathe("bell", [(RM + 0.03, -0.16), (RM + 0.03, -0.13), (0.16, -0.13), (0.15, 0.03), (0.17, 0.03), (0.17, 0.06)], n=16, mat=BL, phase=0.0)
        pw.bolts(b, RM + 0.005, 8, 0.014, [(-0.2, -1)], False, "steel")
        b.lathe("pump", [(0.17, 0.06), (0.12, 0.06), (0.12, 0.2), (0.1, 0.22), (0.1, 0.3), (0.06, 0.31), (0.0, 0.31)], n=10, mat="green", phase=0.0)
        pw.bolts(b, 0.145, 6, 0.012, [(0.06, 1)], False, "steel")
        pw.bolts(b, 0.075, 4, 0.012, [(0.31, 1)], False, "steel")
    b.box("motor_tb", (-0.56, YM - 0.1, ZM + RM - 0.02), (-0.3, YM + 0.1, ZM + RM + 0.085), mat=BL, bev=0.008, skip="-z")
    b.box("d_tb_lid", (-0.55, YM - 0.09, ZM + RM + 0.084), (-0.31, YM + 0.09, ZM + RM + 0.09), mat=BL + "_t", detail=True)
    b.torus("motor_eye", (-0.2, YM, ZM + RM + 0.03), 0.028, 0.009, n=8, m=4, mat="steel")
    last_part = b.lo[-1]; last_part.transform(T(V((-0.2, YM, ZM + RM + 0.03))) @ eq.RX(90) @ T(V((0.2, -YM, -(ZM + RM + 0.03)))))
    for x in (-0.6, -0.26):       # motor feet on a bed plate
        for sy in (-1, 1):
            y0, y1 = sorted((YM + sy * 0.1, YM + sy * 0.24))
            b.box("motor_foot", (x - 0.05, y0, TZ1 + 0.03), (x + 0.05, y1, TZ1 + 0.065), mat=BL, bev=0.004, skip="-z")
            b.box("motor_leg", (x - 0.04, YM + sy * 0.1 - 0.02, TZ1 + 0.065), (x + 0.04, YM + sy * 0.1 + 0.02, ZM - 0.12), mat=BL, skip="-z,+z")
            b.cyl("nut", (x, YM + sy * 0.2, TZ1 + 0.065), (x, YM + sy * 0.2, TZ1 + 0.085), 0.016, n=6, mat="steel", caps=(False, True))
    b.box("bed", (-0.72, YM - 0.27, TZ1), (-0.14, YM + 0.27, TZ1 + 0.03), mat=BL, bev=0.004, skip="-z")
    b.box("bell_foot", (-0.1, YM - 0.14, TZ1), (-0.04, YM + 0.14, ZM - 0.1), mat=BL, skip="-z,+z")
    b.cyl("suction", (0.15, YM, TZ1), (0.15, YM, ZM - 0.1), 0.04, n=8, mat=S, caps=(False, False))
    b.lathe("suction_fl", [(0.065, TZ1), (0.065, TZ1 + 0.02), (0.042, TZ1 + 0.03)], n=8, mat=S, at=(0.15, YM, 0), phase=0.0)

    # ---------------- top: valve block with solenoids and levers (front right)
    VX0, VX1, VY0, VY1, VZ = 0.34, 0.74, -0.52, -0.3, TZ1 + 0.16
    b.box("vblock", (VX0, VY0, TZ1), (VX1, VY1, VZ), mat=S, bev=0.006, skip="-z")
    for i in range(4):
        x = VX0 + 0.06 + i * 0.093
        b.box("solenoid", (x - 0.03, VY0 + 0.03, VZ), (x + 0.03, VY1 - 0.03, VZ + 0.085), mat="black", bev=0.006, skip="-z")
        b.cyl("sol_plug", (x, -0.41, VZ + 0.085), (x, -0.41, VZ + 0.12), 0.016, n=6, mat="black", caps=(False, True))
        b.cyl("lever", (x, VY0, TZ1 + 0.1), (x, VY0 - 0.08, TZ1 + 0.15), 0.008, n=5, mat="steel", caps=(False, False))
        b.lathe("knob", [(0.0, -0.02), (0.017, -0.012), (0.017, 0.012), (0.0, 0.02)], n=6, mat="black", at=(x, VY0 - 0.088, TZ1 + 0.155), phase=0.0)
        for z in (TZ1 + 0.04, TZ1 + 0.12): b.bolt((x + 0.035, VY0, z), (0, -1, 0), r=0.007, mat="steel")
    b.box("vblock2", (VX1, VY0 + 0.03, TZ1), (VX1 + 0.14, VY1 - 0.03, TZ1 + 0.11), mat=S, bev=0.005, skip="-z,-x")
    b.cyl("relief", (VX1 + 0.07, -0.41, TZ1 + 0.11), (VX1 + 0.07, -0.41, TZ1 + 0.2), 0.022, n=6, mat="brass", caps=(False, True))
    b.lathe("gauge", [(0.0, -0.018), (0.045, -0.018), (0.045, 0.018), (0.0, 0.018)], n=10, mat="steel", at=(0, 0, 0), phase=0.0)
    b.lo[-1].transform(T(V((VX0 - 0.0 + 0.03, VY1 + 0.05, VZ + 0.12))) @ eq.RX(90))
    b.cyl("gauge_stem", (VX0 + 0.03, VY1 + 0.05, TZ1), (VX0 + 0.03, VY1 + 0.05, VZ + 0.08), 0.01, n=5, mat="steel", caps=(False, False))
    b.cyl("d_dial", (VX0 + 0.03, VY1 + 0.05 - 0.0185, VZ + 0.12), (VX0 + 0.03, VY1 + 0.05 - 0.02, VZ + 0.12), 0.038, n=14, mat="pipe", caps=(True, True), detail=True)

    # ---------------- top: accumulator bottles on a manifold, clamp band on two stays (back right)
    YA, RA, ZA0, ZA1 = 0.36, 0.088, TZ1 + 0.13, 1.62
    AXS = [0.26 + i * 0.2 for i in range(4)]
    b.box("manifold", (AXS[0] - 0.09, YA - 0.06, TZ1), (AXS[-1] + 0.09, YA + 0.06, TZ1 + 0.09), mat=S, bev=0.005, skip="-z")
    for x in AXS:
        b.lathe("accu", [(0.03, TZ1 + 0.09), (0.03, ZA0), (0.06, ZA0 + 0.025), (RA, ZA0 + 0.09), (RA, ZA1 - 0.1), (0.07, ZA1 - 0.04), (0.035, ZA1 - 0.005), (0.035, ZA1)], n=12, mat="black", at=(x, YA, 0), phase=0.0)
        b.lathe("accu_cap", [(0.035, ZA1), (0.024, ZA1), (0.024, ZA1 + 0.03), (0.032, ZA1 + 0.03), (0.032, H - 0.012), (0.02, H), (0.0, H)], n=6, mat="brass", at=(x, YA, 0), phase=0.0)
    ZC = 1.4
    b.box("clamp", (AXS[0] - RA - 0.02, YA - RA - 0.006, ZC - 0.03), (AXS[-1] + RA + 0.02, YA + RA + 0.006, ZC + 0.03), mat=S, skip="-z,+z", bev=0.01, bev_axes="z")
    for x in (AXS[0] - RA - 0.045, AXS[-1] + RA + 0.045):
        b.box("stay", (x - 0.015, YA - 0.02, TZ1), (x + 0.015, YA + 0.02, ZC + 0.03), mat=S, skip="-z")
    for x in [(a + c) / 2 for a, c in zip(AXS, AXS[1:])]:
        b.cyl("clamp_bolt", (x, YA - RA - 0.02, ZC), (x, YA + RA + 0.02, ZC), 0.012, n=6, mat="steel")

    # ---------------- top: steel pipes with nuts at the ends
    def pipe(name, pts, r=0.017, R=0.05, nuts=(True, True)):
        pp = pw.route(pts, R, k=3); pw.tube(b, name, pp, r, n=6, mat=S)
        for k, on in ((0, nuts[0]), (-1, nuts[1])):
            if not on: continue
            p = V(pts[k]); d = (V(pts[1]) - p).normalized() if k == 0 else (V(pts[-2]) - p).normalized()
            with at(b, frame(p, d)): b.lathe("union", [(r + 0.012, 0.0), (r + 0.012, 0.035), (r + 0.001, 0.045)], n=6, mat="steel", phase=0.0)

    pipe("pressure", [(0.22, YM, ZM + 0.1), (0.22, YM, ZM + 0.26), (0.44, YM, ZM + 0.26), (0.44, YM, TZ1 + 0.09), (0.44, VY1, TZ1 + 0.09)])
    pipe("to_accu", [(0.62, VY1, TZ1 + 0.06), (0.62, YA - 0.06, TZ1 + 0.06)], r=0.015)
    pipe("to_filter", [(VX0 + 0.06, VY0, TZ1 + 0.05), (VX0 + 0.06, YF - 0.055, TZ1 + 0.05), (VX0 + 0.06, YF - 0.055, 0.93)], r=0.015, R=0.04)
    pipe("to_accu2", [(VX1 + 0.14, -0.41, TZ1 + 0.05), (0.96, -0.41, TZ1 + 0.05), (0.96, 0.18, TZ1 + 0.05), (0.8, 0.18, TZ1 + 0.05), (0.8, YA - 0.06, TZ1 + 0.05)], r=0.012, R=0.03)
    pipe("tank_return", [(0.56, VY1, TZ1 + 0.12), (0.56, -0.12, TZ1 + 0.12), (0.56, -0.12, TZ1)], r=0.015, R=0.04)
    pipe("case_drain", [(0.26, YM + 0.1, ZM), (0.26, YM + 0.3, ZM), (0.26, YM + 0.3, TZ1)], r=0.012, R=0.04)
    pipe("back_run", [(AXS[0] - 0.09, YA, TZ1 + 0.045), (0.0, YA, TZ1 + 0.045), (0.0, YA, TZ1 + 0.3), (-0.6, YA, TZ1 + 0.3), (-0.6, YA, TZ1)], r=0.015)
    b.lathe("breather", [(0.05, TZ1), (0.05, TZ1 + 0.02), (0.035, TZ1 + 0.02), (0.035, TZ1 + 0.06), (0.055, TZ1 + 0.06), (0.055, TZ1 + 0.12), (0.0, TZ1 + 0.125)], n=10, mat="steel", at=(-0.3, 0.42, 0), phase=0.0)

    # ---------------- hose reels on the -X end
    ZRL, RR = 0.6, 0.27
    for sy in (-1, 1):
        yc = sy * 0.3
        with at(b, frame((TX0, yc, ZRL), (-1, 0, 0), (0, 0, 1))):       # local Z towards -X
            b.lathe("reel_hub", [(0.06, 0.0), (0.06, 0.07)], n=8, mat="steel", phase=0.0)
            b.lathe("reel_disc_a", [(0.06, 0.07), (RR, 0.07), (RR, 0.085), (0.21, 0.085)], n=12, mat="wheel", phase=0.0)
            # the outer side is an open spider (rim ring, hub, two bars), so the coiled hose shows as on the close-up sheet
            b.lathe("reel_hose", [(0.21, 0.085), (0.225, 0.1), (0.225, 0.225), (0.235, 0.235), (0.12, 0.235)], n=12, mat="rubber", phase=0.0)
            b.lathe("reel_rim", [(0.225, 0.222), (RR, 0.222), (RR, 0.245), (0.235, 0.245), (0.235, 0.235)], n=12, mat="wheel", phase=0.0)
            b.lathe("reel_hub", [(0.12, 0.235), (0.12, 0.25), (0.1, 0.26), (0.0, 0.26)], n=12, mat="wheel", phase=0.0)
            for ang in (35, 125):
                with at(b, eq.RZ(ang)):
                    for sg in (-1, 1):
                        x0, x1 = sorted((sg * 0.115, sg * 0.24)); b.box("reel_bar", (x0, -0.028, 0.2355), (x1, 0.028, 0.247), mat="wheel", skip="-z,-x,+x")
            for k in range(5): b.torus("d_coil_f", (0, 0, 0.2345), 0.135 + k * 0.021, 0.009, n=32, m=6, mat="rubber", detail=True)
            for k in range(7): b.torus("d_coil", (0, 0, 0.107 + k * 0.017), 0.222, 0.008, n=32, m=6, mat="rubber", detail=True)
            pw.bolts(b, 0.075, 5, 0.012, [(0.26, 1)], False, "steel")
        b.box("reel_brk", (TX0 - 0.07, yc - 0.2, ZRL - RR - 0.06), (TX0, yc + 0.2, ZRL - RR - 0.02), mat=BL, skip="+x")
        # hose tail from the reel down to its nozzle parked in the tray
        xh = TX0 - 0.157
        pw.tube(b, "hose_tail", pw.route([(xh, yc + sy * 0.215, ZRL), (xh, yc + sy * 0.215, 0.26), (xh, yc + sy * 0.1, 0.2), (xh, yc - sy * 0.05, 0.2)], 0.05, k=2), 0.016, n=6, mat="rubber", caps=(False, True))
        b.cyl("nozzle", (xh, yc - sy * 0.05, 0.2), (xh, yc - sy * 0.14, 0.2), 0.02, n=6, mat="steel")

    # ---------------- grime
    eq.run(b, (0.3, YF, 0.84), (0, -1, 0), 0.5, 0.7, (BL,), i=2, strength=0.55)
    eq.run(b, (-0.2, TY, TZ1 - 0.03), (0, 1, 0), 0.8, 0.9, (BL,), i=4, strength=0.4)
    eq.puddle(b, (0.3, -0.1, TZ1), 0.9, (BL,), strength=0.6)

    return b.lo + b.hi
