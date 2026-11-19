import math
from .. import equipment as eq
from ..equipment import pw, V, T, at, frame, Matrix
from ..geometry import Mesh

def build():
    b = eq.new("chem_skid")
    HX, HY, H = 1.6, 0.8, 2.0
    BL, S, PL = "blue", "stainless", "lgrey"
    ZB = 0.28                 # base top
    PW = 0.12                 # post / rail section
    ZR0, ZR1 = 1.74, 1.82     # top rail
    XP = (-HX + PW / 2, -0.5, 0.56, HX - PW / 2)      # post centres along X
    TANKS = ((-1.49, -0.56), (-0.44, 0.50))
    TY, TZ0, TZ1 = 0.675, 0.29, 1.735

    # ---------------- bunded base: body, lip, fork pockets (baked), corner chafe plates
    b.box("base", (-HX, -HY, 0), (HX, HY, ZB), mat=BL, bev=0.008, skip="-z")
    for sy in (-1, 1):
        for xc in (-0.62, 0.62):
            y = sy * HY
            with at(b, frame((xc, y, 0.12), (0, sy, 0), (1 if sy < 0 else -1, 0, 0))):
                b.box("d_pocket", (-0.17, -0.055, -0.002), (0.17, 0.055, 0.0012), mat="dark", detail=True)
                for x0, x1, y0, y1 in ((-0.2, 0.2, 0.055, 0.075), (-0.2, 0.2, -0.075, -0.055), (-0.2, -0.17, -0.055, 0.055), (0.17, 0.2, -0.055, 0.055)):
                    b.box("d_pocket_rim", (x0, y0, 0), (x1, y1, 0.005), mat=BL, detail=True)
        b.weld((-HX + 0.02, sy * (HY + 0.001), ZB - 0.07), (HX - 0.02, sy * (HY + 0.001), ZB - 0.07), mat=BL, r=0.004)
    for sx in (-1, 1):
        b.weld((sx * (HX + 0.001), -HY + 0.02, ZB - 0.07), (sx * (HX + 0.001), HY - 0.02, ZB - 0.07), mat=BL, r=0.004)
        for sy in (-1, 1):
            for q in ((sx * (HX - 0.18), sy * HY, 0.06, (0, sy, 0)), (sx * HX, sy * (HY - 0.18), 0.06, (sx, 0, 0))):
                b.bolt(q[:3], q[3], r=0.014, mat="steel")

    # ---------------- frame: posts, top rails, lugs
    for i, x in enumerate(XP):
        for sy in (-1, 1):
            y = sy * (HY - PW / 2)
            b.box("post", (x - PW / 2, y - PW / 2, ZB), (x + PW / 2, y + PW / 2, ZR0), mat=BL, skip="-z,+z", bev=0.006, bev_axes="z")
            b.box("d_foot", (x - PW / 2 - 0.025, y - PW / 2 - 0.0, ZB - 0.001), (x + PW / 2 + 0.025, y + PW / 2, ZB + 0.008), mat=BL, detail=True)
    for sy in (-1, 1):
        y = sy * (HY - PW / 2)
        b.box("rail_x", (-HX, y - PW / 2, ZR0), (HX, y + PW / 2, ZR1), mat=BL, bev=0.006, bev_axes="x", skip="-x,+x")
    for sx in (-1, 1):
        x = sx * (HX - PW / 2)
        b.box("rail_y", (x - PW / 2, -HY, ZR0), (x + PW / 2, HY, ZR1), mat=BL, bev=0.006, bev_axes="y")
        for sy in (-1, 1):
            pw.lug(b, "lug", (sx * (HX - 0.14), sy * (HY - PW / 2), ZR1 - 0.004), (1, 0, 0), 0.1, H - ZR1 + 0.004, 0.055, 0.036, H - ZR1 - 0.085, 0.03, mat=BL + "_t")
    for x in (XP[1], XP[2]):      # cross rails over the tanks
        b.box("rail_c", (x - PW / 2, -HY + PW, ZR0), (x + PW / 2, HY - PW, ZR1), mat=BL, skip="-y,+y")

    # ---------------- plate panels: both ends, and the back of the pump bay
    for sx in (-1,):
        x0, x1 = sorted((sx * (HX - 0.02), sx * (HX - 0.03)))
        b.box("end_plate", (x0, -HY + PW, ZB), (x1, HY - PW, ZR0), mat=PL, skip="-y,+y,-z,+z" + (",-x" if sx > 0 else ",+x"))
        xf = sx * (HX - 0.02)
        for sy in (-1, 1):
            for k in range(6):
                z = ZB + 0.12 + k * (ZR0 - ZB - 0.24) / 5; b.rivet((xf, sy * (HY - PW - 0.035), z), (sx, 0, 0), r=0.011, mat="steel")
        b.box("d_seam", (xf - 0.001, -HY + PW, 1.085), (xf + 0.002 * sx, HY - PW, 1.093), mat="dark", detail=True)
    b.box("kerb_f", (XP[2] + PW / 2, -HY, ZB), (XP[3] - PW / 2, -HY + 0.03, ZB + 0.06), mat=BL, skip="-x,+x,-z")
    b.box("kerb_e", (HX - 0.03, -HY + PW, ZB), (HX, HY - PW, ZB + 0.06), mat=BL, skip="-y,+y,-z")
    b.box("back_plate", (XP[2] + PW / 2, HY - 0.03, ZB), (XP[3] - PW / 2, HY - 0.02, ZR0), mat=PL, skip="-x,+x,-z,+z")
    for x in (XP[2] + PW / 2 + 0.035, XP[3] - PW / 2 - 0.035):
        for k in range(6):
            z = ZB + 0.12 + k * (ZR0 - ZB - 0.24) / 5
            b.rivet((x, HY - 0.02, z), (0, 1, 0), r=0.011, mat="steel"); b.rivet((x, HY - 0.03, z), (0, -1, 0), r=0.011, mat="steel")
    b.box("d_seam", (XP[2] + PW / 2, HY - 0.021, 1.085), (XP[3] - PW / 2, HY - 0.018, 1.093), mat="dark", detail=True)

    # ---------------- tanks
    for ti, (x0, x1) in enumerate(TANKS):
        xc = (x0 + x1) / 2
        b.box("tank", (x0, -TY, TZ0), (x1, TY, TZ1), mat=S, bev=0.012, skip="-z")
        for sy in (-1, 1):       # feet, panel seam and stiffening crease (bake only)
            for xx in (x0 + 0.12, x1 - 0.12):
                b.box("tank_foot", (xx - 0.05, sy * TY - (0.05 if sy > 0 else 0), ZB), (xx + 0.05, sy * TY + (0.05 if sy < 0 else 0), TZ0 + 0.03), mat=S, skip="-z,+z" + (",-y" if sy > 0 else ",+y"))
            b.box("d_tseam", (x0 + 0.015, sy * TY - 0.002, 0.98), (x1 - 0.015, sy * TY + 0.002, 0.99), mat=S, detail=True)
            b.weld((xc, sy * (TY + 0.001), TZ0 + 0.03), (xc, sy * (TY + 0.001), TZ1 - 0.03), mat=S, r=0.003)
        for sy in (-1, 1):       # pressed panel: a raised rim round each face (bake only)
            with at(b, frame((xc, sy * TY, (TZ0 + TZ1) / 2), (0, sy, 0), (1 if sy < 0 else -1, 0, 0))):
                hw, hh = (x1 - x0) / 2 - 0.05, (TZ1 - TZ0) / 2 - 0.06
                for q in ((-hw, hh - 0.03, hw, hh), (-hw, -hh, hw, -hh + 0.03), (-hw, -hh, -hw + 0.03, hh), (hw - 0.03, -hh, hw, hh)):
                    b.box("d_press", (q[0], q[1], -0.001), (q[2], q[3], 0.004), mat=S, detail=True, bev=0.003)
                for u in (-hw + 0.015, 0.0, hw - 0.015):
                    for v in (-hh + 0.015, hh - 0.015): b.rivet((u, v, 0.004), (0, 0, 1), r=0.008, mat="steel")
                if sy < 0:           # blank label plate and blank hazard diamond
                    b.box("d_label", (-hw + 0.1, hh - 0.36, 0.0), (-hw + 0.42, hh - 0.16, 0.003), mat="steel", detail=True, bev=0.002)
                    for u, v in ((-hw + 0.115, hh - 0.345), (-hw + 0.405, hh - 0.345), (-hw + 0.115, hh - 0.175), (-hw + 0.405, hh - 0.175)): b.rivet((u, v, 0.003), (0, 0, 1), r=0.005, mat="steel")
                    with at(b, T(V((0.14, hh - 0.27, 0))) @ eq.RZ(45)):
                        b.box("d_diamond", (-0.1, -0.1, 0.0), (0.1, 0.1, 0.003), mat="paintw", detail=True, bev=0.002)
                        for u, v in ((-0.085, -0.085), (0.085, 0.085), (-0.085, 0.085), (0.085, -0.085)): b.rivet((u, v, 0.003), (0, 0, 1), r=0.005, mat="steel")
        # level gauge on the front: glass tube between two valve blocks, the liquid showing in the lower part
        xg, yg, zg0, zg1 = x1 - 0.075, -TY - 0.035, 0.56, 1.5; zl = zg0 + (zg1 - zg0) * (0.55 if ti == 0 else 0.38)
        for z in (zg0, zg1):
            b.box("gauge_blk", (xg - 0.028, yg - 0.026, z - 0.03), (xg + 0.028, -TY, z + 0.03), mat="steel", bev=0.004, skip="+y")
        pw.tube(b, "gauge_liquid", [(xg, yg, zg0 + 0.03), (xg, yg, zl)], 0.015, n=6, mat="lampy", side=(0, 1, 0))
        pw.tube(b, "gauge_glass", [(xg, yg, zl), (xg, yg, zg1 - 0.03)], 0.015, n=6, mat="glass", side=(0, 1, 0))
        for z in (zg0 + 0.3, zg1 - 0.3): b.box("d_gauge_clip", (xg - 0.02, yg - 0.016, z - 0.01), (xg + 0.02, -TY, z + 0.01), mat="steel", detail=True)
        # manway lid with nuts and two handles, a vent, a level stub
        with at(b, T(V((xc, 0.05, 0)))):
            b.lathe("lid", [(0.25, TZ1 - 0.002), (0.25, TZ1 + 0.03), (0.23, TZ1 + 0.03), (0.23, TZ1 + 0.036), (0.25, TZ1 + 0.036), (0.25, TZ1 + 0.07), (0.19, TZ1 + 0.085), (0.0, TZ1 + 0.09)], n=16, mat=S, phase=0.0)
            pw.bolts(b, 0.225, 12, 0.014, [(TZ1 + 0.07, 1)], True, "steel")
            for yy in (-0.08, 0.08): pw.tube(b, "lid_handle", [(-0.07, yy, TZ1 + 0.08), (-0.07, yy, TZ1 + 0.13), (0.07, yy, TZ1 + 0.13), (0.07, yy, TZ1 + 0.08)], 0.01, n=4, mat="steel", phase=0.5)
        b.lathe("vent", [(0.035, TZ1 - 0.002), (0.035, TZ1 + 0.09), (0.05, TZ1 + 0.09), (0.05, TZ1 + 0.125), (0.0, TZ1 + 0.13)], n=8, mat=S, at=(x0 + 0.14, 0.5, 0), phase=0.0)
        b.lathe("stub", [(0.028, TZ1 - 0.002), (0.028, TZ1 + 0.06), (0.04, TZ1 + 0.06), (0.04, TZ1 + 0.085), (0.0, TZ1 + 0.085)], n=8, mat=S, at=(x1 - 0.14, 0.5, 0), phase=0.0)
        # drain tap low on the front
        xt, zt = x1 - 0.2, TZ0 + 0.12
        with at(b, frame((xt, -TY, zt), (0, -1, 0), (1, 0, 0))):
            b.lathe("tap", [(0.05, 0.0), (0.05, 0.014), (0.028, 0.014), (0.028, 0.035), (0.04, 0.04), (0.04, 0.08), (0.03, 0.085), (0.03, 0.098), (0.0, 0.098)], n=8, mat=S, phase=0.0)
        b.cyl("tap_stem", (xt, -TY - 0.06, zt + 0.035), (xt, -TY - 0.06, zt + 0.07), 0.012, n=6, mat="steel", caps=(False, True))
        b.box("tap_handle", (xt - 0.015, -TY - 0.072, zt + 0.066), (xt + 0.13, -TY - 0.048, zt + 0.078), mat="cblue", bev=0.003)
        eq.run(b, (xt, -TY, zt), (0, -1, 0), 0.22, 0.3, (S, BL), i=1, strength=0.6) if ti == 0 else None

    # header pipe over the tanks, down into the pump bay (suction)
    ZH = 1.93 - 0.03
    c0, c1 = (TANKS[0][0] + TANKS[0][1]) / 2, (TANKS[1][0] + TANKS[1][1]) / 2
    YHd = -0.42
    pts = pw.route([(c0, YHd, TZ1 - 0.01), (c0, YHd, ZH), (0.78, YHd, ZH), (0.78, YHd, 0.62)], 0.07, k=3)
    pw.tube(b, "header", pts, 0.028, n=8, mat=S)
    pts = pw.route([(c1, YHd, TZ1 - 0.01), (c1, YHd, ZH - 0.058)], 0.05, k=2)
    pw.tube(b, "header_t", pts, 0.028, n=8, mat=S)
    for x in (c0, c1):
        b.lathe("header_boss", [(0.045, TZ1 - 0.002), (0.045, TZ1 + 0.05), (0.03, TZ1 + 0.06)], n=8, mat=S, at=(x, YHd, 0), phase=0.0)
    for x in (-0.5, 0.56):
        with at(b, frame((x, YHd, ZH), (1, 0, 0), (0, 0, 1))):
            b.lathe("union", [(0.03, -0.035), (0.042, -0.03), (0.042, 0.03), (0.03, 0.035)], n=6, mat="steel", phase=0.0)
        b.box("header_clip", (x - 0.02, YHd - 0.012, ZR1 - 0.002), (x + 0.02, YHd + 0.012, ZH - 0.026), mat="steel", skip="-z,+z")

    # ---------------- pump bay: two dosing pumps on pedestals, suction manifold, discharge lines, control box
    YPM = -0.2
    PXS = (0.86, 1.26)
    SC = 1.3
    for i, xp in enumerate(PXS):
      with at(b, T(V((xp, YPM, ZB))) @ eq.Matrix.Scale(SC, 4) @ T(V((-xp, -YPM, -ZB)))):
        b.box("pedestal", (xp - 0.13, YPM - 0.26, ZB), (xp + 0.13, YPM + 0.3, ZB + 0.1), mat=BL, bev=0.005, skip="-z")
        zc = ZB + 0.1 + 0.13
        with at(b, frame((xp, YPM, zc), (0, 1, 0), (0, 0, 1))):       # motor along +Y, pump head towards -Y
            b.lathe("motor", [(0.0, -0.05), (0.07, -0.05), (0.07, -0.02), (0.105, -0.02), (0.105, 0.2), (0.11, 0.2), (0.11, 0.29), (0.07, 0.3), (0.0, 0.3)], n=12, mat="green", phase=0.0)
            for k in range(12):          # cooling fins (bake only)
                a = 2 * math.pi * k / 12
                with at(b, eq.RZ(math.degrees(a))): b.box("d_fin", (0.1, -0.004, 0.0), (0.112, 0.004, 0.19), mat="green", detail=True)
            b.lathe("gearbox", [(0.085, -0.19), (0.085, -0.05)], n=8, mat=S, phase=0.5)
            b.lathe("head", [(0.0, -0.275), (0.06, -0.275), (0.075, -0.26), (0.095, -0.26), (0.095, -0.19), (0.0, -0.19)], n=10, mat=S, phase=0.0)
            pw.bolts(b, 0.078, 6, 0.012, [(-0.26, -1)], True, "steel")
        b.box("motor_tb", (xp - 0.05, YPM + 0.04, zc + 0.095), (xp + 0.05, YPM + 0.16, zc + 0.15), mat="green", bev=0.005, skip="-z")
        for sx in (-1, 1): b.box("motor_foot", (xp + sx * 0.1 - 0.02, YPM, ZB + 0.1), (xp + sx * 0.1 + 0.02, YPM + 0.2, zc - 0.06), mat="green", skip="-z,+z")
        yh = YPM - 0.225
        # check valves above and below the head
        b.lathe("valve_lo", [(0.022, ZB + 0.105), (0.032, ZB + 0.11), (0.032, zc - 0.06)], n=6, mat="steel", at=(xp, yh, 0), phase=0.0)
        b.lathe("valve_hi", [(0.032, zc + 0.06), (0.032, zc + 0.15), (0.02, zc + 0.16)], n=6, mat="steel", at=(xp, yh, 0), phase=0.0)
    for i, xp in enumerate(PXS):
        # discharge: up, back to the plate, along to the tank
        xd = xp; yh = YPM - 0.225 * SC; zc = ZB + 0.23 * SC
        pts = pw.route([(xd, yh, zc + 0.15 * SC), (xd, yh, 0.98 + i * 0.12), (xd, 0.62, 0.98 + i * 0.12), (xd, 0.62, 1.52 + i * 0.08), (XP[2] - 0.07, 0.62, 1.52 + i * 0.08)], 0.06, k=2)
        pw.tube(b, "discharge", pts, 0.017, n=6, mat=S)
        eq.puddle(b, (xp, YPM - 0.1, ZB), 0.5, (BL,), strength=0.55) if i == 0 else None
    for i, xp in enumerate(PXS):      # ball valve with a blue lever on each discharge riser
        yh = YPM - 0.225 * SC; zv = 0.84 + i * 0.1
        b.lathe("dis_valve", [(0.018, zv - 0.05), (0.03, zv - 0.04), (0.03, zv + 0.04), (0.018, zv + 0.05)], n=6, mat="steel", at=(xp, yh, 0), phase=0.0)
        b.box("dis_lever", (xp - 0.01, yh - 0.14, zv - 0.008), (xp + 0.01, yh - 0.025, zv + 0.008), mat="cblue", bev=0.003, skip="+y")
    # pulsation dampener and pressure gauge teed off the second discharge line, the dial towards the open end (+X)
    XD, YD, ZD = 1.4, 0.3, 0.98 + 0.12
    pw.tube(b, "damp_line", pw.route([(PXS[1], YD, ZD), (XD, YD, ZD), (XD, YD, 1.2)], 0.05, k=2), 0.017, n=6, mat=S)
    b.lathe("dampener", [(0.02, 1.19), (0.035, 1.2), (0.06, 1.23), (0.06, 1.4), (0.045, 1.44), (0.02, 1.46), (0.02, 1.56)], n=10, mat=S, at=(XD, YD, 0), phase=0.0)
    b.lathe("damp_nut", [(0.03, 1.5), (0.03, 1.535)], n=6, mat="steel", at=(XD, YD, 0), phase=0.0, cap_top=True)
    with at(b, frame((XD - 0.02, YD, 1.62), (1, 0, 0), (0, 0, 1))):
        b.lathe("pgauge", [(0.062, 0.0), (0.066, 0.005), (0.066, 0.05), (0.058, 0.05), (0.058, 0.044), (0.0, 0.044)], n=12, mat="steel", phase=0.0, cap_bot=True)
        b.lathe("d_dial", [(0.056, 0.0445), (0.0, 0.0455)], n=16, mat="paintw", detail=True, phase=0.0)
        b.box("d_needle", (-0.004, -0.004, 0.0455), (0.045, 0.004, 0.0475), mat="black", detail=True)
        for k in range(9):
            with at(b, eq.RZ(-30 + k * 30)): b.box("d_tick", (0.042, -0.002, 0.0455), (0.053, 0.002, 0.0468), mat="black", detail=True)
    # suction manifold along the pump heads from the header drop
    pts = pw.route([(0.78, YHd, 0.66), (0.78, YHd, ZB + 0.07), (PXS[1] + 0.05, YHd, ZB + 0.07)], 0.05, k=2)
    pw.tube(b, "suction", pts, 0.022, n=6, mat=S, caps=(False, True))
    with at(b, frame((0.78, YHd, 0.72), (0, 0, 1), (1, 0, 0))):
        b.lathe("iso_valve", [(0.03, -0.07), (0.045, -0.06), (0.045, 0.06), (0.03, 0.07)], n=8, mat=S, phase=0.0)
    b.box("iso_handle", (0.78 - 0.012, YHd - 0.16, 0.71), (0.78 + 0.012, YHd - 0.04, 0.73), mat="cblue", bev=0.003)
    # tubing wall on the side of the second tank, seen from the open end: two strut rails, a relief loop with its valve,
    # a calibration column with a blue-levered valve, a line across to the discharge side
    XW = TANKS[1][1]
    for z in (0.92, 1.46):
        b.box("wall_strut", (XW, -0.56, z - 0.022), (XW + 0.035, 0.56, z + 0.022), mat="steel", skip="-x")
    XT_ = XW + 0.075
    pw.tube(b, "relief", pw.route([(XT_, -0.2, ZB + 0.02), (XT_, -0.2, 1.56), (XT_, 0.42, 1.56), (XT_, 0.42, 1.12)], 0.06, k=2), 0.017, n=6, mat=S)
    b.lathe("relief_valve", [(0.02, 1.0), (0.034, 1.01), (0.034, 1.12), (0.026, 1.13)], n=6, mat="steel", at=(XT_, 0.42, 0), phase=0.0, cap_bot=True)
    b.lathe("relief_cap", [(0.024, 0.93), (0.024, 1.0)], n=6, mat="cred", at=(XT_, 0.42, 0), phase=0.0, cap_bot=True)
    for z in (0.62, 1.2):
        b.lathe("union", [(0.018, z - 0.03), (0.03, z - 0.022), (0.03, z + 0.022), (0.018, z + 0.03)], n=6, mat="steel", at=(XT_, -0.2, 0), phase=0.0)
    pw.tube(b, "cal_line", pw.route([(XT_, 0.12, ZB + 0.02), (XT_, 0.12, 0.5)], 0.04, k=2), 0.017, n=6, mat=S)
    b.lathe("cal_column", [(0.017, 0.5), (0.03, 0.51), (0.03, 0.56), (0.045, 0.565), (0.045, 0.6)], n=8, mat="steel", at=(XT_, 0.12, 0), phase=0.0)
    b.lathe("cal_liquid", [(0.04, 0.6), (0.04, 0.78)], n=8, mat="lampy", at=(XT_, 0.12, 0), phase=0.0)
    b.lathe("cal_glass", [(0.04, 0.78), (0.04, 1.0)], n=8, mat="glass", at=(XT_, 0.12, 0), phase=0.0)
    b.lathe("cal_top", [(0.045, 1.0), (0.045, 1.035), (0.03, 1.04), (0.0, 1.04)], n=8, mat="steel", at=(XT_, 0.12, 0), phase=0.0)
    b.box("cal_lever", (XT_ + 0.02, 0.11, 0.525), (XT_ + 0.13, 0.13, 0.541), mat="cblue", bev=0.003, skip="-x")
    pw.tube(b, "cross_line", pw.route([(XT_, -0.42, 1.34), (XT_, -0.42, 1.46 + 0.05), (XT_ + 0.02, 0.6, 1.46 + 0.05)], 0.05, k=2), 0.014, n=5, mat=S)
    for y, z in ((-0.2, 0.92), (-0.2, 1.46), (0.42, 1.46), (0.12, 0.92)):
        b.box("d_wclip", (XW + 0.035, y - 0.03, z - 0.012), (XT_ + 0.02, y + 0.03, z + 0.012), mat="steel", detail=True)
    # post base plates with their bolts (bake only)
    for x in XP:
        for sy in (-1, 1):
            for dx in (-1, 1): b.bolt((x + dx * (PW / 2 + 0.01), sy * (HY - PW / 2), ZB + 0.008), (0, 0, 1), r=0.009, mat="steel")
    # strut rail on the back plate with clips for the discharge lines
    b.box("strut", (XP[2] + PW / 2, 0.66, 1.26), (XP[3] - PW / 2, HY - 0.03, 1.31), mat="steel", skip="-x,+x,+y")
    for xp in PXS: b.box("strut_clip", (xp - 0.03, 0.6, 1.27), (xp + 0.03, 0.66, 1.3), mat="steel", skip="+y")
    # control box on the front, hung from the top rail
    BX0, BX1, BY0, BY1, BZ0, BZ1 = 0.98, 1.42, -HY + 0.012, -HY + 0.2, 1.2, 1.68
    b.box("cbox", (BX0, BY0 + 0.022, BZ0), (BX1, BY1, BZ1), mat=S, bev=0.006)
    b.box("cbox_door", (BX0 + 0.025, BY0, BZ0 + 0.025), (BX1 - 0.025, BY0 + 0.022, BZ1 - 0.025), mat=S, bev=0.005, skip="+y")
    for z in (BZ0 + 0.09, BZ1 - 0.09):       # quarter-turn latches on the right, lift-off hinges on the left
        b.cyl("cbox_latch", (BX1 - 0.055, BY0, z), (BX1 - 0.055, -HY, z), 0.02, n=8, mat="steel", caps=(False, True))
        b.box("d_latch_slot", (BX1 - 0.07, -HY - 0.0015, z - 0.003), (BX1 - 0.04, -HY + 0.0005, z + 0.003), mat="black", detail=True)
        b.box("cbox_hinge", (BX0 + 0.004, -HY, z - 0.045), (BX0 + 0.03, BY0 + 0.012, z + 0.045), mat="steel", bev=0.004, bev_axes="z", skip="+y")
        b.box("d_hinge_gap", (BX0 + 0.003, -HY - 0.001, z - 0.004), (BX0 + 0.031, -HY + 0.001, z + 0.004), mat="black", detail=True)
    b.box("d_door_plate", (BX0 + 0.14, BY0 - 0.003, BZ1 - 0.15), (BX0 + 0.3, BY0 + 0.001, BZ1 - 0.08), mat="steel", detail=True, bev=0.002)
    for x in (BX0 + 0.22, BX0 + 0.42 - 0.1):      # spare glands with flexible conduit down to the base
        b.lathe("cgland", [(0.016, BZ0 - 0.035), (0.022, BZ0 - 0.03), (0.022, BZ0)], n=6, mat="steel", at=(x, BY1 - 0.07, 0), phase=0.0)
        pw.tube(b, "conduit", pw.route([(x, BY1 - 0.07, BZ0 - 0.03), (x, BY1 - 0.07, 1.0), (x, 0.7, 1.0), (x, 0.7, ZB)], 0.07, k=2), 0.012, n=5, mat="steel")
    for x in (BX0 + 0.06, BX1 - 0.06):
        b.box("cbox_hanger", (x - 0.02, BY1 - 0.03, BZ1), (x + 0.02, BY1 - 0.022, ZR0), mat=BL + "_t", skip="-z,+z")
        b.box("cbox_stay", (x - 0.02, BY1, BZ0 + 0.1), (x + 0.02, BY1 + 0.012, BZ0 + 0.14), mat=BL + "_t")
    for i, xp in enumerate(PXS):      # cables from the box to the motors
        x0 = BX0 + 0.12 + i * 0.2
        b.lathe("cgland", [(0.016, BZ0 - 0.035), (0.022, BZ0 - 0.03), (0.022, BZ0)], n=6, mat="steel", at=(x0, BY1 - 0.07, 0), phase=0.0)
        pts = pw.route([(x0, BY1 - 0.07, BZ0 - 0.03), (x0, BY1 - 0.07, 0.86), (xp, YPM + 0.13, 0.86), (xp, YPM + 0.13, ZB + 0.38 * SC)], 0.08, k=2)
        pw.tube(b, "cable", pts, 0.011, n=5, mat="rubber")

    # ---------------- grime
    eq.run(b, (0.3, -HY, ZB), (0, -1, 0), 0.7, 0.26, (BL,), i=3, strength=0.5)
    eq.run(b, (-1.0, -TY, TZ1), (0, -1, 0), 0.5, 1.2, (S,), i=2, strength=0.3)
    eq.run(b, (0.1, TY, TZ1), (0, 1, 0), 0.5, 1.3, (S,), i=4, strength=0.3)
    eq.run(b, (-HX + 0.02, -0.1, ZR0), (-1, 0, 0), 0.6, 1.3, (PL,), i=0, strength=0.4)
    eq.run(b, (1.1, HY - 0.02, ZR0), (0, 1, 0), 0.5, 1.2, (PL,), i=3, strength=0.4)

    return b.lo + b.hi
