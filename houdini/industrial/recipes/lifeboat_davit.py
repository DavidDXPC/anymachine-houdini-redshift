import math
from .. import structural as lm, builder as hs, station as st, lifesaving as ls
from ..lifesaving import V, Z, F, obox, tube, polytube, sect, rect, Matrix
from ..geometry import Mesh

def build():
    b = lm.start("lifeboat_davit")
    G = ls.Grating(b)
    X, Y = V((1, 0, 0)), V((0, 1, 0))
    EX, DZ, WX = st.EDGE_X, st.DECK_Z, st.WALL_X
    HK = [st.hook_point_station(i) for i in (0, 1)]          # fore (+Y), aft (-Y)
    YF = HK[0].y; FX = HK[0].x                                 # frame planes y = +-YF; the falls hang at x = FX
    CX, CT = -1.85, 5.46                                       # davit column centre line and top
    AZ = CT + 0.14                                             # arm centre height (arm 0.20 x 0.28, sitting on the column)
    SR = 0.19; SC = V((FX - SR, 0, 5.70))                      # head sheave radius and centre (x, z)
    GX, GZ = -2.13, 5.27                                       # winch girder centre (0.22 x 0.30), behind the columns
    SHZ = 5.64                                                 # winch shaft height
    PX0, PX1, PY = EX, -0.95, 3.94                             # embarkation platform: deck edge to its outboard edge, half length
    GIRZ = 2.43                                                # base girder centre (0.26 deep, top flange under the grating)

    for sy in (-1, 1):
        y0 = sy * YF; hk = HK[0] if sy > 0 else HK[1]
        # ------------------------------------------------------------ base girder off the deck edge, end plate, knee brace to the wall
        sect(b, "base_girder", (EX + 0.02, y0, GIRZ), (PX1, y0, GIRZ), lm.isec(0.30, 0.26, 0.02, 0.014), Y, "wht", caps=(False, True))
        ME = F((EX, y0, GIRZ + 0.025), Y, Z)
        obox(b, "deck_plate", ME, (-0.2, -0.145, 0.0), (0.2, 0.145, 0.02), mat="wht", bev=0.004, skip="-z")
        lm.bolts(b, [ME @ V((px, pz, 0.02)) for px in (-0.165, 0.165) for pz in (-0.1, 0.0, 0.1)], X, r=0.017, h=0.014, mat="galv", real=True)
        for dy in (-0.07, 0.07):                           # web stiffeners at the end plate and under the column
            for xx in (EX + 0.16, CX):
                obox(b, "stiffener", F((xx, y0 + dy * 1.15, GIRZ), X, Z), (-0.006, -0.11, -0.065), (0.006, 0.11, 0.065), mat="wht", skip="-y,+y")
        A0 = V((-1.2, y0, GIRZ - 0.13)); B0 = V((WX + 0.02, y0, 0.5)); ax = (A0 - B0).normalized()
        sect(b, "knee_brace", B0 + ax * 0.16, A0 - ax * 0.12 - Z * 0.07, rect(0.14, 0.14), Y, "wht", caps=(True, True))
        for dy in (-0.085, 0.085):                         # pinned ends: cheek lugs on the girder and on the wall pad
            b.prism("brace_lug", A0 + Y * dy, X, Z, [(-0.26, 0.0), (0.16, 0.0), (0.1, -0.16), (-0.2, -0.2)], -0.01, 0.01, mat="wht")
            b.prism("brace_lug", B0 + Y * dy - X * 0.02, X, Z, [(0.0, -0.17), (0.28, 0.04), (0.2, 0.2), (0.0, 0.17)], -0.01, 0.01, mat="wht")
        for p in (A0 - ax * 0.05 - Z * 0.1, B0 + ax * 0.13):
            b.cyl("brace_pin", p - Y * 0.11, p + Y * 0.11, 0.022, n=8, mat="galv", caps=(True, True))
            for sg in (-1, 1): b.cyl("brace_pin_nut", p + Y * sg * 0.096, p + Y * sg * 0.118, 0.036, n=6, mat="galv", caps=(True, True))
        MW = F((WX, y0, 0.5), Y, Z)
        obox(b, "wall_pad", MW, (-0.2, -0.24, 0.0), (0.2, 0.24, 0.02), mat="wht", bev=0.004, skip="-z")
        lm.bolts(b, [MW @ V((px, pz, 0.02)) for px in (-0.155, 0.155) for pz in (-0.19, 0.19)], X, r=0.018, h=0.014, mat="galv", real=True)

        # ------------------------------------------------------------ davit frame: column on a bolted foot, arm, knee, head sheave
        MF = F((CX, y0, GIRZ + 0.13), X, Y)
        obox(b, "column_foot", MF, (-0.25, -0.165, 0.0), (0.25, 0.165, 0.025), mat="wht", bev=0.004, skip="-z")
        lm.bolts(b, [MF @ V((px, py, 0.025)) for px in (-0.205, 0.205) for py in (-0.115, 0.0, 0.115)], Z, r=0.017, h=0.016, mat="galv", real=True)
        sect(b, "column", (CX, y0, GIRZ + 0.155), (CX, y0, CT), rect(0.30, 0.24), X, "wht")
        for sx in (-1, 1):
            for dy in (-0.07, 0.07):
                b.prism("foot_gusset", V((CX + sx * 0.15, y0 + dy, GIRZ + 0.155)), X * sx, Z, [(0, 0), (0.085, 0), (0.085, 0.02), (0, 0.22)], -0.007, 0.007, mat="wht")
        AX0, AX1 = CX - 0.15, SC.x - SR - 0.04
        sect(b, "arm", (AX0, y0, AZ), (AX1, y0, AZ), rect(0.20, 0.28), Y, "wht", caps=(True, True))
        obox(b, "column_cap", F((CX, y0, CT), X, Y), (-0.17, -0.14, -0.012), (0.17, 0.14, 0.0), mat="wht", skip="+z")
        K0 = V((CX + 0.15, y0, 4.62)); K1 = V((-0.72, y0, CT)); ka = (K1 - K0).normalized()
        sect(b, "knee", K0 - ka * 0.03, K1 + ka * 0.03, rect(0.14, 0.12), Y, "wht")
        for sg in (-1, 1):                                 # cheek plates carrying the head sheave, bolted through the arm tip
            c = V((SC.x, y0 + sg * 0.11, SC.z))
            lm.grid_plate(b, "cheek", c, X, Z, [-0.42, -0.2, -0.05, 0.12, 0.25], [-0.2, -0.1, 0.1, 0.22], 0.02, mat="wht",
                          warp=lambda px, pz: (px, pz * (0.55 if px > 0.2 else 1.0)))
            lm.bolts(b, [c + Y * sg * 0.01 + X * px + Z * pz for px in (-0.36, -0.24) for pz in (-0.16, 0.0)], Y * sg, r=0.016, h=0.013, mat="galv", real=True)
            lm.spun(b, "sheave_boss", c + Y * sg * 0.01, Y * sg, [(0.075, 0), (0.075, 0.016), (0.045, 0.03), (0.0, 0.03)], n=12, mat="wht")
            lm.spun(b, "sheave_nut", c + Y * sg * 0.04, Y * sg, [(0.04, 0), (0.04, 0.03), (0.022, 0.03), (0.022, 0.05), (0.0, 0.05)], n=6, mat="galv")
            b.cyl("sheave_spacer", V((SC.x, y0 + sg * 0.045, SC.z)), V((SC.x, y0 + sg * 0.1, SC.z)), 0.045, n=10, mat="galv", caps=(False, False))
        lm.sheave(b, V((SC.x, y0, SC.z)), Y, SR, 0.08, mat="sheave", n=20, name="head_sheave", groove=0.03)
        kp = V((SC.x + 0.15, y0, SC.z + 0.105))
        b.cyl("rope_keeper", kp - Y * 0.1, kp + Y * 0.1, 0.012, n=6, mat="galv", caps=(False, False))
        lm.grid_plate(b, "lift_lug", V((-0.9, y0, AZ + 0.14 + 0.07)), X, Z, [-0.09, -0.035, 0.035, 0.09], [-0.07, -0.01, 0.045, 0.085], 0.02, holes=[(1, 1)], mat="wht",
                      warp=lambda px, pz: (px * (0.55 if pz > 0.08 else 1.0), pz))

        # ------------------------------------------------------------ fall: off the winch drum, over the arm and the head sheave, down to the hook
        T0 = V((GX, y0, SHZ + 0.165)); pts = [T0]
        for a in (90, 60, 30, 0): pts.append(V((SC.x + SR * math.cos(math.radians(a)), y0, SC.z + SR * math.sin(math.radians(a)))))
        zt = hk.z + 0.46; pts.append(V((FX, y0, zt)))
        polytube(b, "fall", pts, 0.011, n=6, mat="rope", caps=(False, False))
        lm.spun(b, "fall_socket", V((FX, y0, zt + 0.02)), -Z, [(0.016, 0), (0.03, 0.1), (0.03, 0.15), (0.0, 0.15)], n=8, mat="galv")
        for sg in (-1, 1): obox(b, "fall_clevis", F((FX, y0 + sg * 0.022, zt - 0.2), X, Z), (-0.03, -0.085, -0.006), (0.03, 0.085, 0.006), mat="galv")
        b.cyl("fall_pin", V((FX, y0 - 0.042, zt - 0.245)), V((FX, y0 + 0.042, zt - 0.245)), 0.014, n=6, mat="galv", caps=(True, True))
        lz0, lz1 = hk.z - 0.012, zt - 0.235; lc = (lz0 + lz1) / 2; lh = (lz1 - lz0) / 2 - 0.04
        ring = []
        for k in range(13):                                # long link: an oval ring, bearing in the hook at the bottom
            a = math.radians(90 + 30 * k); cx, sz = math.cos(a), math.sin(a)
            ring.append(V((FX + 0.04 * cx, y0, lc + (lh if sz > 0 else -lh) * (1 if abs(sz) > 1e-6 else 0) + 0.04 * sz)))
        polytube(b, "long_link", ring, 0.012, n=6, mat="galv", caps=(False, False))

        # ------------------------------------------------------------ winch girder joint, drum and its bearings on the cross shaft
        MJ = F((CX - 0.15, y0, GZ), -Y, Z)                 # flange plate on the back of the column, local z = -X
        obox(b, "girder_flange", MJ, (-0.17, -0.24, 0.0), (0.17, 0.24, 0.02), mat="wht", bev=0.004, skip="-z")
        lm.bolts(b, [MJ @ V((px, pz, 0.02)) for px in (-0.13, 0.13) for pz in (-0.2, 0.2)], -X, r=0.016, h=0.013, mat="galv", real=True)
        b.cyl("drum", V((GX, y0 - 0.13, SHZ)), V((GX, y0 + 0.13, SHZ)), 0.15, n=16, mat="rope", caps=(False, False))
        for k in range(8): lm.spun(b, "d_wrap", V((GX, y0 - 0.112 + k * 0.032, SHZ)), Y, None, n=16, mat="rope", detail=True, torus=(0.152, 0.016))
        for sg in (-1, 1):
            lm.spun(b, "drum_flange", V((GX, y0 + sg * 0.145, SHZ)), Y, [(0.05, -0.015), (0.21, -0.015), (0.21, 0.015), (0.05, 0.015), (0.05, -0.015)], n=16, mat="blue")
            yb = y0 + sg * 0.25
            obox(b, "bearing_base", F((GX, yb, GZ + 0.15), X, Y), (-0.13, -0.04, 0.0), (0.13, 0.04, 0.03), mat="blue", skip="-z")
            lm.spun(b, "bearing", V((GX, yb - 0.04, SHZ)), Y, [(0.04, 0), (0.085, 0), (0.085, 0.08), (0.04, 0.08)], n=10, mat="blue")
            obox(b, "bearing_web", F((GX, yb, GZ + 0.18), X, Y), (-0.075, -0.03, 0.0), (0.075, 0.03, SHZ - GZ - 0.18 - 0.05), mat="blue", skip="-z,+z")
            lm.bolts(b, [V((GX + sx * 0.1, yb, GZ + 0.18)) for sx in (-1, 1)], Z, r=0.014, h=0.012, mat="galv", real=True)

    # ---------------------------------------------------------------- winch girder, cross shaft, gearbox, motor, brake
    sect(b, "winch_girder", (GX, -YF - 0.2, GZ), (GX, YF + 0.2, GZ), rect(0.22, 0.30), X, "wht", caps=(True, True))
    b.cyl("shaft", V((GX, -YF - 0.36, SHZ)), V((GX, YF + 0.36, SHZ)), 0.032, n=8, mat="galv", caps=(True, True))
    for y in (-1.5, 1.5):                                   # steady bearings on the long shaft
        obox(b, "bearing_web", F((GX, y, GZ + 0.15), X, Y), (-0.07, -0.03, 0.0), (0.07, 0.03, SHZ - GZ - 0.15 - 0.05), mat="blue", skip="-z,+z")
        lm.spun(b, "bearing", V((GX, y - 0.04, SHZ)), Y, [(0.04, 0), (0.08, 0), (0.08, 0.08), (0.04, 0.08)], n=10, mat="blue")
    for y in (-0.62, 0.3):                                  # flanged couplings either side of the gearbox
        lm.spun(b, "coupling", V((GX, y, SHZ)), Y, [(0.035, 0), (0.085, 0), (0.085, 0.05), (0.035, 0.05)], n=12, mat="galv")
    obox(b, "winch_bed", F((GX, -0.1, GZ + 0.15), X, Y), (-0.2, -0.78, 0.0), (0.2, 0.98, 0.03), mat="blue", bev=0.004, skip="-z")
    lm.bolts(b, [V((GX + sx * 0.17, y, GZ + 0.18)) for sx in (-1, 1) for y in (-0.8, -0.3, 0.3, 0.8)], Z, r=0.014, h=0.012, mat="galv", real=True)
    obox(b, "gearbox", F((GX, -0.02, GZ + 0.18), X, Y), (-0.19, -0.2, 0.0), (0.19, 0.2, 0.52), mat="blue", bev=0.03, skip="-z")
    obox(b, "gearbox_cover", F((GX + 0.19, -0.02, SHZ), Y, Z), (-0.14, -0.16, 0.0), (0.14, 0.16, 0.012), mat="blue", skip="-z")
    for px in (-0.115, 0.0, 0.115):
        for pz in (-0.135, 0.135): b.bolt(V((GX + 0.202, -0.02 + px, SHZ + pz)), X, r=0.009, h=0.005, mat="galv")
    lm.spun(b, "motor", V((GX, 0.36, SHZ)), Y, [(0.09, 0.0), (0.135, 0.02), (0.135, 0.42), (0.145, 0.42), (0.145, 0.54), (0.11, 0.56), (0.0, 0.56)], n=14, mat="blue")
    for k in range(9): lm.spun(b, "d_fin", V((GX, 0.42 + k * 0.04, SHZ)), Y, None, n=14, mat="blue", detail=True, torus=(0.137, 0.009))
    obox(b, "motor_term", F((GX, 0.56, SHZ + 0.13), X, Y), (-0.07, -0.08, 0.0), (0.07, 0.08, 0.075), mat="blue", bev=0.008, skip="-z")
    obox(b, "motor_foot", F((GX, 0.57, GZ + 0.18), X, Y), (-0.14, -0.17, 0.0), (0.14, 0.17, SHZ - GZ - 0.18 - 0.1), mat="blue", skip="-z,+z")
    lm.spun(b, "brake_drum", V((GX, -0.5, SHZ)), Y, [(0.04, 0), (0.16, 0), (0.16, 0.11), (0.04, 0.11)], n=16, mat="dark")
    BP = V((GX - 0.12, -0.445, SHZ + 0.2)); BL = V((GX + 0.46, -0.445, 6.02))
    sect(b, "brake_lever", BP, BL, rect(0.03, 0.05), Y, "blue", caps=(True, True))
    b.cyl("brake_pivot", BP - Y * 0.05, BP + Y * 0.05, 0.022, n=8, mat="galv", caps=(True, True))
    obox(b, "brake_post", F((GX - 0.12, -0.445, GZ + 0.18), X, Y), (-0.03, -0.035, 0.0), (0.03, 0.035, SHZ + 0.2 - GZ - 0.18), mat="blue", skip="-z")
    bd = (BL - BP).normalized()
    obox(b, "brake_weight", F(BL - bd * 0.02, bd, Y), (-0.09, -0.07, -0.06), (0.09, 0.07, 0.06), mat="dark", bev=0.008)
    tube(b, "brake_rod", BP + bd * 0.12, V((GX + 0.0, -0.445, SHZ + 0.17)), 0.009, 5, "galv")

    # ---------------------------------------------------------------- embarkation platform: steel, grating, rails, chain, fenders
    ZB = DZ - 0.14                                           # centre of the 0.20 deep platform beams (top 0.04 under the grating top)
    sect(b, "plat_edge", (PX1 - 0.04, -PY, ZB), (PX1 - 0.04, PY, ZB), rect(0.08, 0.2), X, "wht", caps=(True, True))
    for sy in (-1, 1):
        sect(b, "plat_end", (EX + 0.02, sy * (PY - 0.04), ZB), (PX1 - 0.08, sy * (PY - 0.04), ZB), rect(0.08, 0.2), Y, "wht")
        ME = F((EX, sy * (PY - 0.04), ZB), Y, Z)
        obox(b, "plat_end_plate", ME, (-0.09, -0.13, 0.0), (0.09, 0.13, 0.015), mat="wht", skip="-z")
        lm.bolts(b, [ME @ V((px, pz, 0.015)) for px in (-0.065, 0.065) for pz in (-0.09, 0.09)], X, r=0.012, h=0.01, mat="galv", real=True)
    for y in (-1.53, 0.0, 1.53):
        sect(b, "plat_joist", (EX + 0.015, y, ZB), (PX1 - 0.08, y, ZB), lm.isec(0.12, 0.2, 0.012, 0.008), Y, "wht")
        ME = F((EX, y, ZB), Y, Z)
        obox(b, "plat_end_plate", ME, (-0.1, -0.13, 0.0), (0.1, 0.13, 0.015), mat="wht", skip="-z")
        lm.bolts(b, [ME @ V((px, pz, 0.015)) for px in (-0.075, 0.075) for pz in (-0.09, 0.09)], X, r=0.012, h=0.01, mat="galv", real=True)
    # grating at deck level, cut round the two column feet; a flat-bar banding on its outer edges
    CW0, CW1 = CX - 0.29, CX + 0.29; CY0, CY1 = YF - 0.2, YF + 0.2
    def gq(x0, x1, y0, y1): G.quad((x0, y0, DZ), (x1, y0, DZ), (x1, y1, DZ), (x0, y1, DZ))
    gq(CW1, PX1, -PY, PY); gq(PX0, CW1, -CY0, CY0)
    for sy in (-1, 1):
        ya, yb = sorted((sy * CY1, sy * PY)); gq(PX0, CW1, ya, yb)
        yc, yd = sorted((sy * CY0, sy * CY1)); gq(PX0, CW0, yc, yd)
        b.box("grate_band", (PX0, sy * PY - 0.004, DZ - 0.04), (PX1, sy * PY + 0.004, DZ), mat="galv")
    b.box("grate_band", (PX1 - 0.004, -PY, DZ - 0.04), (PX1 + 0.004, PY, DZ), mat="galv")
    RX = PX1 - 0.04; GAP = 0.72
    for sy in (-1, 1):
        lm.rail_run(b, [(EX + 0.06, sy * (PY - 0.04), DZ), (RX, sy * (PY - 0.04), DZ), (RX, sy * GAP, DZ)], mat="yel", n=6, name="plat_rail")
        for k, px in enumerate((RX, EX + 0.06)):            # post shoes bolted to the beams (bake: the bolts)
            obox(b, "rail_shoe", F((px, sy * (PY - 0.04), DZ), X, Y), (-0.06, -0.05, -0.002), (0.06, 0.05, 0.008), mat="yel", skip="-z")
        obox(b, "rail_shoe", F((RX, sy * GAP, DZ), X, Y), (-0.05, -0.06, -0.002), (0.05, 0.06, 0.008), mat="yel", skip="-z")
    for hz in (1.06, 0.56):                                   # safety chains across the boarding gap
        c0, c1 = V((RX, -GAP, DZ + hz)), V((RX, GAP, DZ + hz))
        polytube(b, "gap_chain", [c0 + (c1 - c0) * t - Z * 0.14 * 4 * t * (1 - t) for t in (0, 0.12, 0.3, 0.5, 0.7, 0.88, 1)], 0.009, n=4, mat="galv", caps=(False, False))
        for c in (c0, c1): lm.spun(b, "chain_eye", c, X, None, n=8, mat="galv", torus=(0.026, 0.007))
    for y in (-2.75, -1.3, 1.3, 2.75):                        # fender pads the boat's rubbing strake bears on
        obox(b, "fender_bracket", F((PX1, y, DZ - 0.02), Y, Z), (-0.1, -0.2, 0.0), (0.1, 0.24, 0.05), mat="wht", skip="-z")
        obox(b, "fender_pad", F((PX1 + 0.05, y, DZ - 0.01), Y, Z), (-0.09, -0.16, 0.0), (0.09, 0.2, 0.09), mat="rubber", bev=0.02, skip="-z")
        for pz in (-0.1, 0.14): b.bolt(V((PX1 + 0.14, y, DZ - 0.01 + pz)), X, r=0.012, h=0.004, mat="galv")

    # ---------------------------------------------------------------- gripe lashings: eye plate, slip hook, turnbuckle, wire to the boat's grab rail
    for yg in (1.25, -1.05):
        fr = st.frame(yg, 8, 0.5, 1); top = st.BOAT_M @ (fr[0] + fr[1] * 0.075)
        g0 = V((RX, yg, DZ - 0.04 + 0.0)) + V((0.0, 0, 0.045)); d = (top - g0).normalized()
        obox(b, "gripe_eye_plate", F((RX, yg, DZ - 0.04), X, Y), (-0.04, -0.07, 0.0), (0.04, 0.07, 0.012), mat="galv", skip="-z")
        lm.spun(b, "gripe_eye", g0, Y, None, n=8, mat="galv", torus=(0.03, 0.01))
        lm.spun(b, "gripe_hook", g0 + d * 0.055, X, None, n=8, mat="galv", torus=(0.03, 0.009))
        t0, t1 = g0 + d * 0.1, g0 + d * 0.36
        for o in (-1, 1):                                     # open-body turnbuckle: two side bars, end blocks, screw eyes
            s_ = d.cross(X).normalized() * o * 0.017
            tube(b, "turnbuckle_bar", t0 + d * 0.03 + s_, t1 - d * 0.03 + s_, 0.006, 4, "galv")
        for p in (t0, t1): b.cyl("turnbuckle_end", p + d * 0.015, p + d * 0.05 * (1 if p is t0 else -1) + d * (0.0 if p is t0 else 0.0), 0.02, n=6, mat="galv", caps=(True, True))
        tube(b, "turnbuckle_screw", t0 - d * 0.02, t0 + d * 0.1, 0.007, 5, "galv"); tube(b, "turnbuckle_screw", t1 - d * 0.1, t1 + d * 0.04, 0.007, 5, "galv")
        polytube(b, "gripe_wire", [t1 + d * 0.04, top - d * 0.04], 0.006, n=5, mat="rope", caps=(False, False))
        lm.spun(b, "gripe_top_hook", top - d * 0.022, Y, None, n=8, mat="galv", torus=(0.026, 0.008))

    # ---------------------------------------------------------------- control box on the forward column, conduit down to the deck
    MC = F((CX, YF - 0.12, DZ + 1.35), X, Z)                  # column face looking along -Y (towards the boarding gap)
    obox(b, "control_box", MC, (-0.1, -0.14, 0.0), (0.1, 0.14, 0.1), mat="grey", bev=0.008, skip="-z")
    obox(b, "d_lid", MC, (-0.085, -0.125, 0.1), (0.085, 0.125, 0.104), mat="grey", skip="-z", detail=True)
    nb = MC.to_3x3() @ Z
    for (px, pz, m, r) in ((-0.04, 0.07, "btn_g", 0.016), (0.04, 0.07, "btn_r", 0.016), (0.0, -0.04, "btn_r", 0.026)):
        b.cyl("d_button", MC @ V((px, pz, 0.1)), MC @ V((px, pz, 0.122)), r, n=12, mat=m, caps=(False, True), detail=True, bev=0.003)
        b.cyl("d_bezel", MC @ V((px, pz, 0.1)), MC @ V((px, pz, 0.108)), r * 1.35, n=12, mat="galv", caps=(False, True), detail=True)
    for sx in (-1, 1):
        for sz in (-1, 1): b.bolt(MC @ V((sx * 0.085, sz * 0.125, 0.1)), nb, r=0.006, h=0.004, mat="galv")
    cy = YF - 0.12 - 0.03
    polytube(b, "conduit", [(CX - 0.04, cy, DZ + 1.21), (CX - 0.04, cy, DZ + 0.06)], 0.012, n=5, mat="galv", caps=(False, False))
    polytube(b, "conduit", [(CX + 0.04, cy, DZ + 1.49), (CX + 0.04, cy, GZ - 0.2), (CX - 0.1, cy, GZ - 0.2), (CX - 0.19, cy, GZ + 0.0)], 0.012, n=5, mat="galv", caps=(False, False))
    for z in (DZ + 0.4, DZ + 0.9, DZ + 1.9, DZ + 2.4):
        obox(b, "d_clip", F((CX - 0.04 if z < DZ + 1.3 else CX + 0.04, YF - 0.12, z), X, Z), (-0.03, -0.012, 0.0), (0.03, 0.012, 0.046), mat="galv", detail=True)

    # ---------------------------------------------------------------- bake-only: weld beads at the main joints
    for sy in (-1, 1):
        y0 = sy * YF
        for sg in (-1, 1):
            b.weld((CX - 0.15, y0 + sg * 0.12, GIRZ + 0.155), (CX + 0.15, y0 + sg * 0.12, GIRZ + 0.155), r=0.006, mat="wht")
            b.weld((CX + sg * 0.15, y0 - 0.12, GIRZ + 0.155), (CX + sg * 0.15, y0 + 0.12, GIRZ + 0.155), r=0.006, mat="wht")
            b.weld((CX - 0.15, y0 + sg * 0.12, CT), (CX + 0.15, y0 + sg * 0.12, CT), r=0.006, mat="wht")
            b.weld((EX + 0.02, y0 + sg * 0.15, GIRZ - 0.13), (EX + 0.02, y0 + sg * 0.15, GIRZ + 0.13), r=0.005, mat="wht")


    # ---------------------------------------------------------------- stains (projected in the bake): grease under the sheaves and the winch, rust bleed below joints
    PM = ("wht", "blue", "yel", "grey")
    def stain(k, c, n, w, h, s_=0.8): b.decal("sn_0%d.png" % (k % 5), c, n, (0, 0, 1), w, h, kind="stain", mats=PM, depth=0.12, strength=s_)
    def blot(c, up, w, h, s_=0.8): b.decal("sn_05.png", c, (0, 0, 1), up, w, h, kind="stain", mats=PM, depth=0.1, strength=s_)
    for i, sy in enumerate((-1, 1)):
        y0 = sy * YF
        for sg in (-1, 1):
            stain(i + sg + 1, (SC.x - 0.22, y0 + sg * 0.1, AZ - 0.02), (0, sg, 0), 0.5, 0.36, 0.95)       # grease thrown off the head sheave, down the arm
            stain(i + sg + 3, (CX, y0 + sg * 0.12, 4.3), (0, sg, 0), 0.3, 1.5, 0.7)                        # runs down the column from the elbow
            stain(i + 3, (-1.2 + sg * 0.5, y0 + 0.15 * sg, GIRZ), (0, sg, 0), 0.4, 0.26, 0.7)             # base girder
        stain(i + 1, (CX + 0.15, y0, 3.9), (1, 0, 0), 0.24, 1.6, 0.75)
        stain(i, (CX - 0.15, y0, 4.4), (-1, 0, 0), 0.24, 1.3, 0.8)                                         # below the girder flange bolts
        blot((-0.9, y0, AZ + 0.14), (1, 0, 0), 1.6, 0.2, 0.75)                                             # the fall drips along the arm top
        blot((CX, y0, GIRZ + 0.155), (1, 0, 0), 0.6, 0.45, 0.8)                                            # round the column foot
    ROW = lambda n_: (n_)                                                # strips of streaks: one projector each (a material holds about thirty)
    for sg in (-1, 1): b.decal(ROW("gr_row.png"), (GX + sg * 0.11, 0, GZ - 0.01), (sg, 0, 0), (0, 0, 1), 6.6, 0.3, kind="stain", mats=PM, depth=0.12, strength=0.7)   # oil and grease down the winch girder
    blot((GX, -0.1, GZ + 0.18), (0, 1, 0), 0.4, 1.7, 0.85)
    b.decal(ROW("rr_row.png"), (PX1, 0, ZB), (1, 0, 0), (0, 0, 1), 7.6, 0.2, kind="stain", mats=PM, depth=0.12, strength=0.85)   # platform edge beam under posts and fenders


    return b.lo + b.hi
