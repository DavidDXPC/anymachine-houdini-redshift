import math
import numpy as np
from .. import airframe as H
from ..airframe import V, X, Y, Z, hs, lm, at, both, rot, tr, frame, fz, spun, rod, wing, ringloft, gridsurf, pchip
from ..structural import rect
from ..geometry import Mesh
from ..livery import paint_panels

def build():
    B, M, I = hs.Build("heli_body"), hs.Build("heli_mech"), hs.Build("heli_interior")
    B.tag = M.tag = I.tag = 1
    F = H.Fus()
    R_MAIN, ZH, NB = 5.7, 3.72, 5                       # main rotor radius, hub plane height, blades
    TR, R_TAIL = V((-7.15, -0.34, 3.30)), 1.05          # tail rotor centre (right-hand side) and radius
    DECK = V((0.5, 0.0, 0.0))                           # this origin on the helideck: deck-local (x, y) of the mast
    ZF = 0.80                                           # cabin floor

    # ================================================================= fuselage skin, liner, glass
    GLASS = F.build(B, I)
    F.skin_rivets(B, frames=[4.05, 3.85, 3.28, 2.82, 1.628, 0.55, -0.45, -1.6, -2.2, -2.8, -3.4, -4.0, -4.5, -5.0, -5.5, -6.0, -6.4],
                  stringers=[(H.RN["belt"], (3.85, -3.4)), (3, (4.05, -2.5)), (H.RN["top"] + 2, (2.44, -3.1)), (1, (3.85, -1.9)), (15, (1.64, -4.0))])

    # ================================================================= engine and gearbox cowling on the roof
    CK = [(1.80, 0.46, 0.10), (1.66, 0.64, 0.40), (1.30, 0.77, 0.64), (0.70, 0.80, 0.72), (0.0, 0.80, 0.72), (-1.10, 0.76, 0.68),
          (-1.80, 0.64, 0.56), (-2.50, 0.46, 0.36), (-3.20, 0.30, 0.16), (-3.55, 0.20, 0.07)]
    CX = [k[0] for k in CK]
    def cowl_pt(x, th):
        w = pchip(CX, [k[1] for k in CK], x); h = pchip(CX, [k[2] for k in CK], x); z0 = F.top(x).z - 0.16; e = 2 / 2.7
        c, s = math.cos(th), max(0.0, math.sin(th))
        return V((x, w * (1 if c > 0 else -1) * abs(c) ** e, z0 + h * s ** e))
    def cowl_pn(x, th):
        p = cowl_pt(x, th); a = cowl_pt(x + 2e-3, th) - cowl_pt(x - 2e-3, th); c = cowl_pt(x, th + 2e-3) - cowl_pt(x, th - 2e-3)
        return p, a.cross(c).normalized()
    CXS = [1.80, 1.73, 1.66, 1.48, 1.30, 1.0, 0.7, 0.35, 0.0, -0.4, -0.8, -1.1, -1.45, -1.8, -2.15, -2.5, -2.85, -3.2, -3.55]
    CTH = [math.pi * k / 16 for k in range(17)]
    gridsurf(B, "cowl", [[cowl_pt(x, t) for t in CTH] for x in CXS], "white", inside=(0, 0, 2.4))
    spun(B, "mast_fairing", (0.0, 0, 0), Z, [(0.46, 2.92), (0.40, 3.03), (0.24, 3.10), (0.15, 3.13), (0.0, 3.13)], n=18, mat="white")
    for sg in both(B):
        # intake: oval lip standing out of the cowling front, screen recessed in it
        p, n = cowl_pn(1.36, 0.46); d = (n * 0.8 + X * 0.6).normalized(); e1 = d.cross(Z).normalized(); p = p + d * 0.035
        spun(B, "intake_lip", p + d * 0.02, d, [(0.218, -0.13), (0.222, -0.02), (0.210, 0.03), (0.182, 0.035), (0.168, 0.0), (0.168, -0.045)], n=18, mat="orange", sx=1.32, e1=e1)
        spun(B, "intake_screen", p + d * 0.02, d, [(0.168, -0.045), (0.0, -0.045)], n=18, mat="mesh", sx=1.32, e1=e1)
        with at(frame(p + d * 0.02, e1, d), B):
            for u in np.linspace(-0.2, 0.2, 13): B.box("d_wire", (u - 0.003, -0.17, -0.046), (u + 0.003, 0.17, -0.040), mat="steel", detail=True)
            for u in np.linspace(-0.15, 0.15, 10): B.box("d_wire", (-0.22, u - 0.003, -0.046), (0.22, u + 0.003, -0.040), mat="steel", detail=True)
        # exhaust: heat-stained stainless pipe out of the cowling shoulder, angled out and up
        q = cowl_pt(-1.62, 0.62); ed = V((-0.74, 0.44, 0.50)).normalized()
        H.pipe(B, "exhaust", q - ed * 0.12, q + ed * 0.40, 0.145, wall=0.008, n=16, mat="exh", inner="soot")
        spun(B, "exhaust_collar", q + ed * 0.02, ed, [(0.20, -0.03), (0.20, 0.0), (0.150, 0.03)], n=16, mat="trim")
        # cooling louvres (bake-only slats) and riveted access panels on the cowling side
        for t in np.linspace(0.30, 0.78, 8):
            (p0, n0), (p1, n1) = cowl_pn(0.98, t), cowl_pn(0.60, t)
            B.cyl("d_louvre", p0 + n0 * 0.002, p1 + n1 * 0.002, 0.013, n=4, mat="soot", detail=True, phase=0.0)
        rv = []
        for (xa, xb, ta, tb) in ((0.45, -0.55, 0.22, 0.95), (-0.70, -1.35, 0.25, 0.80), (1.05, 0.52, 0.2, 0.9), (0.4, -0.4, 1.15, 1.5)):
            for k in range(int(abs(xa - xb) / 0.05) + 1):
                x = xa + (xb - xa) * k / int(abs(xa - xb) / 0.05)
                rv += [cowl_pn(x, ta), cowl_pn(x, tb)]
            for k in range(1, 12): rv += [cowl_pn(xa, ta + (tb - ta) * k / 12), cowl_pn(xb, ta + (tb - ta) * k / 12)]
        H.rivets(B, rv, r=0.0045)
        for (x, t) in ((0.3, 0.26), (-0.4, 0.26), (0.3, 0.9), (-0.4, 0.9), (-0.85, 0.3), (-1.2, 0.3)):       # quarter-turn latches
            p, n = cowl_pn(x, t)
            with at(fz(p, n), B): B.cyl("d_latch", (0, 0, -0.001), (0, 0, 0.004), 0.022, n=12, mat="trim", detail=True, caps=(False, True)); B.box("d_slot", (-0.016, -0.003, 0.004), (0.016, 0.003, 0.0055), mat="soot", detail=True)
        # hand holds and recessed foot steps up the side to the roof
        for x in (1.02, 0.25):
            p, n = F.side(x, 2.19)
            with at(fz(p, n), B):
                for u in (-0.09, 0.09): B.cyl("grab", (u, 0, -0.005), (u, 0, 0.045), 0.008, n=6, mat="trim", caps=(False, False))
                B.cyl("grab", (-0.098, 0, 0.045), (0.098, 0, 0.045), 0.008, n=6, mat="trim")
    # drive shaft cover along the top of the tail boom, hinged in sections
    sx = [-3.45, -4.0, -4.6, -5.2, -5.8, -6.35]
    for a, c in zip(sx, sx[1:]):
        B.cyl("shaft_cover", F.top(a) + Z * 0.035 - X * 0.004, F.top(c) + Z * 0.035 + X * 0.004, 0.085, n=10, mat="white", caps=(True, True), phase=0.0)
        for s_ in (-1, 1):
            for x in (a - 0.12, c + 0.12):
                p = F.top(x) + Z * 0.02 + Y * s_ * 0.083
                B.box("d_shaft_latch", (p.x - 0.03, p.y - 0.004, p.z - 0.012), (p.x + 0.03, p.y + 0.004, p.z + 0.012), mat="trim", detail=True)

    # ================================================================= tail: fin, stabiliser, ventral fin, bumper
    FIN = [((-6.18, 0, 2.16), (-7.22, 0, 2.02), 0.20), ((-6.40, 0, 2.75), (-7.30, 0, 2.75), 0.19), ((-6.72, 0, 3.50), (-7.44, 0, 3.50), 0.16),
           ((-7.00, 0, 4.14), (-7.56, 0, 4.14), 0.12), ((-7.08, 0, 4.24), (-7.52, 0, 4.24), 0.07)]
    wing(B, "fin", [(a, c, t, Y) for a, c, t in FIN], "white")
    wing(B, "ventral_fin", [((-6.25, 0, 2.02), (-7.05, 0, 2.02), 0.12, Y), ((-6.62, 0, 1.52), (-7.02, 0, 1.52), 0.07, Y), ((-6.72, 0, 1.46), (-6.98, 0, 1.46), 0.04, Y)], "white")
    lm.sweep(B, "tail_skid", [V((-6.62, 0, 1.56)), V((-6.80, 0, 1.36)), V((-7.02, 0, 1.26)), V((-7.16, 0, 1.27))], [(0.016, 0.03)] * 4, Y, n=6, mat="trim")
    B.box("skid_shoe", (-7.19, -0.035, 1.235), (-7.04, 0.035, 1.262), mat="seal", bev=0.006)
    spun(B, "beacon_base", (-7.30, 0, 4.24), Z, [(0.05, -0.01), (0.05, 0.02), (0.038, 0.025)], n=10, mat="trim")
    spun(B, "beacon", (-7.30, 0, 4.265), Z, [(0.036, 0), (0.038, 0.035), (0.028, 0.07), (0.0, 0.082)], n=10, mat="lampr")
    B.box("tail_light", (-7.565, -0.02, 4.10), (-7.535, 0.02, 4.16), mat="lampw", bev=0.004)
    wing(B, "fin_antenna", [((-6.83, 0, 3.82), (-6.98, 0, 3.80), 0.012, Z), ((-6.60, 0, 3.90), (-6.68, 0, 3.90), 0.008, Z)], "soot")
    for sg in both(B):
        wing(B, "stabiliser", [((-5.52, 0.10, 2.10), (-6.10, 0.10, 2.08), 0.075, Z), ((-5.60, 1.22, 2.10), (-6.08, 1.22, 2.09), 0.055, Z)], "orange", caps=(False, True))
        wing(B, "stab_endplate", [((-5.58, 1.235, 1.90), (-6.02, 1.235, 1.90), 0.012, Y), ((-5.52, 1.235, 2.10), (-6.12, 1.235, 2.10), 0.024, Y),
                                  ((-5.66, 1.235, 2.34), (-6.10, 1.235, 2.34), 0.012, Y)], "orange")
        H.rivets(B, [(V((-5.62 - 0.045 * k, y, 2.10 + 0.036 - 0.0004 * k)), Z) for y in (0.3, 0.75, 1.15) for k in range(9)], r=0.004, mat="orange")
        # whip and blade antennas, tie-down ring on the boom
        rod(B, "whip", F.top(-4.75) + Y * 0.16, F.top(-4.75) + Y * 0.19 + V((-0.12, 0, 0.55)), 0.005, mat="soot", n=5)
        p, n = F.pn(-4.4, 0.9)
        with at(fz(p, n), B): B.torus("boom_ring", (0, 0, 0.022), 0.028, 0.006, n=10, m=5, mat="trim"); B.box("boom_ring_pad", (-0.04, -0.03, -0.002), (0.04, 0.03, 0.006), mat="trim", bev=0.002, skip="-z")
    wing(B, "belly_antenna", [((1.12, 0, 0.57), (0.84, 0, 0.57), 0.035, Y), ((0.94, 0, 0.36), (0.82, 0, 0.36), 0.014, Y)], "white")
    rod(B, "belly_whip", (-1.0, 0.2, 0.57), (-1.06, 0.2, 0.30), 0.005, mat="soot", n=5)
    B.box("radalt", (-0.30, -0.12, 0.538), (0.0, 0.12, 0.552), mat="white", bev=0.004, skip="+z")
    for x in (-1.9, -2.6): rod(B, "drain_mast", F.pt(x, 0) + Z * 0.02, F.pt(x, 0) - Z * 0.10 - X * 0.03, 0.007, mat="trim", n=5)
    spun(B, "gps_dome", F.top(1.95) + V((0.25, 0, -0.01)), Z, [(0.17, 0), (0.17, 0.02), (0.145, 0.07), (0.08, 0.105), (0.0, 0.112)], n=14, mat="white")
    spun(B, "belly_beacon", (0.9, -0.3, 0.552), -Z, [(0.04, 0), (0.04, 0.03), (0.028, 0.06), (0.0, 0.068)], n=10, mat="lampr")

    # ================================================================= sponsons with flotation covers, nose float covers
    SXC, SHL, SY, SZ, SA, SC = -0.72, 1.32, 1.34, 0.78, 0.40, 0.22
    def sf(u): return max(0.12, (1 - abs(u) ** 4) ** 0.5)
    def lug_y(x): return SY + SA * sf((x - SXC) / SHL)
    LUGS = (0.30, -1.74)
    def sponson_ring(u, k=18):
        f = sf(u); a, c = SA * f, SC * (0.35 + 0.65 * f); e = 2 / 4.5; x = SXC + u * SHL
        return [V((x, SY + a * math.copysign(abs(math.cos(t)) ** e, math.cos(t)), SZ + c * math.copysign(abs(math.sin(t)) ** e, math.sin(t)))) for t in [2 * math.pi * i / k for i in range(k)]]
    for sg in both(B):
        ringloft(B, "sponson", [sponson_ring(u) for u in (1.0, 0.995, 0.97, 0.9, 0.75, 0.45, 0.0, -0.45, -0.75, -0.9, -0.97, -0.995, -1.0)], "navy")
        lm.plate(B, "float_cover", (SXC, SY + SA - 0.008, SZ), Y, X, 1.20, 0.27, 0.020, "float", lift=0.0)
        lm.bolts(B, [V((SXC + u, SY + SA + 0.012, SZ + w)) for u in np.linspace(-0.57, 0.57, 12) for w in (-0.115, 0.115)] + [V((SXC + u, SY + SA + 0.012, SZ + w)) for u in (-0.57, 0.57) for w in (-0.04, 0.04)], Y, r=0.009, h=0.005, mat="trim")
        spun(B, "nav_light", (SXC + 0.93 * SHL, SY + 0.19, SZ + 0.02), V((0.6, 0.8, 0)), [(0.045, 0), (0.045, 0.012), (0.034, 0.035), (0.0, 0.045)], n=10, mat="lampg" if sg > 0 else "lampr")
        B.cyl("d_fuel_cap", (SXC + 0.3, SY, SZ + SC - 0.001), (SXC + 0.3, SY, SZ + SC + 0.007), 0.06, n=16, mat="trim", detail=True, caps=(False, True))
        for nm, x in (("lug_f", LUGS[0]), ("lug_r", LUGS[1])):            # tie-down lugs with rings
            a = lug_y(x) - SY
            B.box(nm, (x - 0.05, SY + a - 0.01, SZ - 0.10), (x + 0.05, SY + a + 0.012, SZ - 0.02), mat="trim", bev=0.004, skip="-y")
            with at(tr(x, SY + a + 0.03, SZ - 0.075) @ rot("X", 90), B): B.torus(nm + "_ring", (0, 0, 0), 0.03, 0.007, n=10, m=5, mat="trim")
        # flotation cover low on the nose side, aft of the chin window
        p, n = F.side(2.72, 0.90)
        with at(fz(p, n), B):
            B.box("nose_float", (-0.24, -0.11, -0.004), (0.24, 0.11, 0.012), mat="float", bev=0.006, skip="-z")
            for u in np.linspace(-0.21, 0.21, 6):
                for w in (-0.085, 0.085): B.bolt((u, w, 0.012), Z, r=0.007, h=0.004, mat="trim")

    # ================================================================= doors: hinges, handles, sliding rail and track, wipers
    for sg in both(B):
        for z in (1.02, 1.78):                                              # cockpit door hinges on the forward edge
            p, n = F.side(2.434, z)
            with at(fz(p, n), B):
                B.box("hinge", (-0.045, -0.035, -0.002), (0.055, 0.035, 0.010), mat="trim", bev=0.003, skip="-z")
                B.cyl("hinge_pin", (0.0, -0.04, 0.012), (0.0, 0.04, 0.012), 0.008, n=6, mat="trim")
                for u in (-0.03, 0.04):
                    for w in (-0.02, 0.02): B.bolt((u, w, 0.010), Z, r=0.005, h=0.003, mat="trim")
        for (x, z, w) in ((1.80, 1.13, 0.15), (1.44, 1.16, 0.10)):          # flush pull handles: bezel, dark recess, bar
            p, n = F.side(x, z)
            with at(fz(p, n), B):
                B.box("handle_bezel", (-w / 2, -0.035, -0.002), (w / 2, 0.035, 0.005), mat="trim", bev=0.003, skip="-z")
                B.box("handle_well", (-w / 2 + 0.012, -0.022, 0.005), (w / 2 - 0.012, 0.022, 0.0056), mat="soot", skip="-z,-x,+x,-y,+y")
                B.box("handle_bar", (-w / 2 + 0.016, -0.004, 0.0056), (w / 2 - 0.016, 0.010, 0.013), mat="trim", bev=0.002, skip="-z")
        (p0, n0), (p1, n1) = F.side(1.62, 2.19), F.side(-2.45, 2.19)        # sliding door upper rail
        lm.sect(B, "door_rail", p0 + n0 * 0.022, p1 + n1 * 0.022, rect(0.04, 0.05), n0, "white", caps=(True, True))
        lm.sect(B, "door_rail_lip", p0 + n0 * 0.046 - Z * 0.03, p1 + n1 * 0.046 - Z * 0.03, rect(0.008, 0.03), n0, "trim", caps=(True, True))
        for x in (1.58, 0.55, -0.45, -1.45, -2.40):
            p, n = F.side(x, 2.19)
            with at(fz(p, n), B): B.box("rail_bracket", (-0.035, -0.045, -0.002), (0.035, 0.045, 0.012), mat="trim", bev=0.003, skip="-z")
        for x in (1.30, -0.22):                                             # roller carriages on the door top
            p, n = F.side(x, 2.105)
            with at(fz(p, n), B):
                B.box("carriage", (-0.06, -0.03, -0.002), (0.06, 0.07, 0.016), mat="trim", bev=0.004, skip="-z")
                for u in (-0.035, 0.035): B.bolt((u, 0.0, 0.016), Z, r=0.007, h=0.004, mat="trim")
        (p0, n0), (p1, n1) = F.side(1.56, 0.752), F.side(-2.40, 0.752)      # lower track and sill plate
        lm.sect(B, "door_track", p0 + n0 * 0.012, p1 + n1 * 0.012, rect(0.024, 0.03), n0, "trim", caps=(True, True))
        (p0, n0), (p1, n1) = F.side(1.52, 0.815), F.side(-0.43, 0.815)
        lm.sect(B, "sill_plate", p0 + n0 * 0.003, p1 + n1 * 0.003, rect(0.006, 0.045), n0, "trim", caps=(True, True))
        # windscreen wiper: pivot at the sill, arm, blade lying on the glass
        pv, nv = F.pn(3.50, F.row_th(3.50, H.RN["wb"]) + 0.42)
        a0, an = F.pn(3.02, 2.52); b0, bn = F.pn(2.96, 2.26); b1, bn1 = F.pn(3.06, 2.86)
        B.cyl("wiper_pivot", pv - nv * 0.005, pv + nv * 0.03, 0.014, n=8, mat="soot")
        rod(B, "wiper_arm", pv + nv * 0.028, a0 + an * 0.022, 0.006, mat="soot", n=5)
        lm.sect(B, "wiper_blade", b0 + bn * 0.012, b1 + bn1 * 0.012, rect(0.010, 0.016), (bn + bn1), "soot", caps=(True, True))
        # pitot tube on the nose side, static port, outside-air probe
        p, n = F.pn(3.98, 1.72); sd = n.cross(X).normalized()
        lm.sweep(B, "pitot", [p - n * 0.005, p + n * 0.075, p + n * 0.105 + X * 0.035, p + n * 0.11 + X * 0.12, p + n * 0.11 + X * 0.30], [(0.012, 0.012)] * 4 + [(0.007, 0.007)], sd, n=6, mat="trim")
        with at(fz(p, n), B):
            B.box("pitot_base", (-0.035, -0.03, -0.002), (0.045, 0.03, 0.006), mat="trim", bev=0.002, skip="-z")
            for u in (-0.025, 0.035):
                for w in (-0.02, 0.02): B.bolt((u, w, 0.006), Z, r=0.004, h=0.002, mat="trim")
        p, n = F.side(2.62, 1.14)
        with at(fz(p, n), B):
            B.cyl("d_static", (0, 0, -0.001), (0, 0, 0.002), 0.035, n=16, mat="trim", detail=True, caps=(False, True))
            for k in range(8): B.cyl("d_static_hole", (0.02 * math.cos(k * math.pi / 4), 0.02 * math.sin(k * math.pi / 4), 0.002), (0.02 * math.cos(k * math.pi / 4), 0.02 * math.sin(k * math.pi / 4), 0.0028), 0.003, n=6, mat="soot", detail=True, caps=(False, True))
    # landing light and taxi light under the nose
    for (c, r_) in (((3.42, 0.22, 0.60), 0.075), ((3.52, -0.20, 0.61), 0.05)):
        d = V((0.5, 0, -0.86)).normalized()
        spun(B, "light_can", c, d, [(r_ * 0.7, -0.06), (r_, -0.01), (r_, 0.06), (r_ * 0.92, 0.07)], n=12, mat="trim")
        spun(B, "light_lens", c, d, [(r_ * 0.92, 0.07), (r_ * 0.6, 0.082), (0.0, 0.086)], n=12, mat="lampw")

    # ================================================================= main rotor (object heli_rotor)
    M.tag = 1
    rod(M, "mast", (0, 0, 3.08), (0, 0, ZH - 0.06), 0.075, mat="steel", n=14)
    spun(M, "mast_collar", (0, 0, 3.10), Z, [(0.20, 0), (0.20, 0.03), (0.12, 0.07), (0.10, 0.12)], n=16, mat="hub")
    lm.bolts(M, [V((0.17 * math.cos(k * math.pi / 6), 0.17 * math.sin(k * math.pi / 6), 3.13)) for k in range(12)], Z, r=0.012, h=0.01, mat="steel", real=False)
    ZS = 3.30                                                               # swashplate: fixed ring, turning ring, servos, scissors
    spun(M, "swash_fixed", (0, 0, ZS), Z, [(0.11, -0.035), (0.26, -0.035), (0.28, -0.015), (0.28, 0.0), (0.11, 0.0)], n=18, mat="hub")
    spun(M, "swash_turning", (0, 0, ZS), Z, [(0.11, 0.012), (0.27, 0.012), (0.29, 0.03), (0.27, 0.05), (0.11, 0.05)], n=18, mat="hub")
    spun(M, "swash_ball", (0, 0, ZS), Z, [(0.075, -0.07), (0.115, -0.03), (0.115, 0.05), (0.075, 0.09)], n=14, mat="steel")
    for a in (90, 210, 330):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        M.cyl("servo", (0.25 * c, 0.25 * s, 3.06), (0.25 * c, 0.25 * s, 3.21), 0.042, n=10, mat="dark", bev=0.006)
        rod(M, "servo_rod", (0.25 * c, 0.25 * s, 3.21), (0.25 * c, 0.25 * s, ZS - 0.03), 0.016, mat="chrome", n=8, ends=0.022)
        M.box("servo_valve", (0.25 * c - 0.03, 0.25 * s - 0.03, 3.07), (0.25 * c + 0.03, 0.25 * s + 0.03, 3.13), mat="hub", bev=0.004, xf=tr(0.05 * c, 0.05 * s, 0))
        H.path(M, "servo_hose", [V((0.31 * c, 0.31 * s, 3.10)), V((0.37 * c, 0.37 * s, 3.14)), V((0.40 * c, 0.40 * s, 3.08)), V((0.40 * c, 0.40 * s, 3.02))], 0.008, 0.008, V((-s, c, 0)), "dark", n=5)
    rod(M, "fixed_scissor_a", (-0.25, 0.0, 3.10), (-0.36, 0.0, 3.19), 0.014, mat="hub", n=6, ends=0.02)
    rod(M, "fixed_scissor_b", (-0.36, 0.0, 3.19), (-0.26, 0.0, ZS - 0.02), 0.014, mat="hub", n=6, ends=0.02)
    spun(M, "hub", (0, 0, ZH), Z, [(0.075, -0.10), (0.17, -0.085), (0.20, -0.04), (0.20, 0.05), (0.165, 0.075)], n=20, mat="hub")
    spun(M, "hub_cap", (0, 0, ZH), Z, [(0.165, 0.075), (0.215, 0.085), (0.22, 0.115), (0.17, 0.19), (0.08, 0.225), (0.0, 0.232)], n=20, mat="hub")
    lm.bolts(M, [V((0.195 * math.cos(k * math.pi / 5), 0.195 * math.sin(k * math.pi / 5), ZH + 0.098)) for k in range(10)], Z, r=0.01, h=0.008, mat="steel")
    def droop(r): return -0.26 * ((r - 0.6) / (R_MAIN - 0.6)) ** 2
    def blade_frame(k): return tr(0, 0, ZH) @ rot("Z", 360.0 * k / NB)
    for k in range(NB):
        with at(blade_frame(k), M):
            M.box("yoke", (0.13, -0.075, -0.04), (0.40, 0.075, 0.04), mat="hub", bev=0.01)
            M.cyl("bearing", (0.335, 0, -0.062), (0.335, 0, 0.062), 0.082, n=14, mat="dark", bev=0.008)
            for s_ in (-1, 1):
                M.box("grip", (0.30, -0.09, s_ * 0.066 - 0.014), (0.74, 0.09, s_ * 0.066 + 0.014), mat="hub", bev=0.006)
                lm.bolts(M, [V((0.335, 0, s_ * 0.08))], Z * s_, r=0.03, h=0.016, mat="steel", real=True)
            M.box("grip_web", (0.44, -0.07, -0.052), (0.50, 0.07, 0.052), mat="hub", bev=0.006)
            M.box("cuff", (0.54, -0.105, -0.04), (0.84, 0.105, 0.04), mat="cuff", bev=0.012)
            for x in (0.60, 0.70):
                M.cyl("blade_bolt", (x, 0, -0.092), (x, 0, 0.092), 0.024, n=8, mat="steel", bev=0.004)
                for s_ in (-1, 1): M.cyl("blade_bolt_washer", (x, 0, s_ * 0.080), (x, 0, s_ * 0.086), 0.036, n=10, mat="steel")
            rod(M, "damper_body", (0.20, -0.17, 0.0), (0.42, -0.15, 0.0), 0.036, mat="dark", n=10)
            rod(M, "damper_rod", (0.42, -0.15, 0.0), (0.56, -0.135, 0.0), 0.016, mat="chrome", n=8, ends=0.022)
            M.box("damper_lug", (0.15, -0.20, -0.02), (0.22, -0.075, 0.02), mat="hub", bev=0.004)
            M.box("damper_lug2", (0.54, -0.15, -0.02), (0.60, -0.10, 0.02), mat="hub", bev=0.004)
            M.box("pitch_horn", (0.42, 0.09, -0.022), (0.49, 0.235, 0.022), mat="hub", bev=0.006)
            rod(M, "pitch_link", (0.455, 0.215, -0.01), (0.265 * math.cos(0.72), 0.265 * math.sin(0.72), ZS + 0.04 - ZH), 0.013, mat="steel", n=6, ends=0.02)
            # blade: root fairing, constant chord, tip bands, swept tip.  Leading edge towards +Y, drooping when stopped.
            def bs(r, ch, th, off=0.30): return ((r, ch * off, droop(r)), (r, -ch * (1 - off), droop(r)), th, Z)
            wing(M, "blade", [bs(0.80, 0.21, 0.07, 0.5), bs(1.02, 0.34, 0.052), bs(1.25, 0.40, 0.046), bs(2.8, 0.40, 0.044), bs(4.2, 0.40, 0.042), bs(5.22, 0.40, 0.040)], "blade")
            wing(M, "blade_tip_white", [bs(5.22, 0.40, 0.040), bs(5.40, 0.40, 0.039)], "tipw", caps=(False, False))
            wing(M, "blade_tip_yellow", [bs(5.40, 0.40, 0.039), bs(5.58, 0.38, 0.036, 0.26), bs(5.70, 0.24, 0.022, 0.05)], "tipy", caps=(False, True))
            M.box("trim_tab", (3.4, -0.31, droop(3.6) - 0.002), (3.9, -0.275, droop(3.6) + 0.002), mat="cuff")
            H.rivets(M, [(V((x, y, 0.041)), Z) for x in (0.57, 0.81) for y in (-0.08, -0.04, 0.0, 0.04, 0.08)], r=0.006, mat="cuff")

    # ================================================================= tail rotor and gearbox (object heli_mech)
    M.tag = 2
    M.cyl("tr_gearbox", (TR.x, -0.03, TR.z), (TR.x, -0.215, TR.z), 0.125, n=14, mat="gearbox", bev=0.012)
    M.box("tr_gearbox_in", (TR.x - 0.02, -0.19, TR.z - 0.36), (TR.x + 0.16, -0.04, TR.z + 0.02), mat="gearbox", bev=0.02)
    for k in range(7): M.box("d_fin", (TR.x - 0.11, -0.218, TR.z - 0.09 + 0.03 * k), (TR.x + 0.11, -0.03, TR.z - 0.082 + 0.03 * k), mat="gearbox", detail=True)
    M.cyl("d_sight", (TR.x + 0.16, -0.12, TR.z - 0.2), (TR.x + 0.167, -0.12, TR.z - 0.2), 0.025, n=12, mat="steel", detail=True, caps=(False, True))
    rod(M, "tr_shaft", (TR.x, -0.21, TR.z), (TR.x, TR.y + 0.1, TR.z), 0.034, mat="steel", n=10)
    rod(M, "tr_pitch_rod", (TR.x + 0.13, -0.18, TR.z - 0.30), (TR.x + 0.07, TR.y - 0.10, TR.z - 0.05), 0.010, mat="steel", n=6, ends=0.016)
    with at(frame(TR, X, -Y), M):
        spun(M, "tr_hub", (0, 0, 0), Z, [(0.045, -0.10), (0.085, -0.08), (0.095, -0.02), (0.095, 0.03), (0.06, 0.05), (0.0, 0.055)], n=14, mat="hub")
        spun(M, "tr_spider", (0, 0, 0.085), Z, [(0.02, -0.03), (0.075, -0.012), (0.075, 0.012), (0.0, 0.02)], n=8, mat="hub")
        for k in range(4):
            with at(rot("Z", 45 + 90 * k), M):
                M.box("tr_cuff", (0.07, -0.045, -0.026), (0.25, 0.045, 0.026), mat="hub", bev=0.008)
                for x in (0.15, 0.21): M.cyl("tr_bolt", (x, 0, -0.034), (x, 0, 0.034), 0.012, n=6, mat="steel")
                M.box("tr_horn", (0.10, 0.045, -0.012), (0.14, 0.10, 0.012), mat="hub", bev=0.004)
                rod(M, "tr_link", (0.12, 0.085, 0.0), (0.055, 0.045, 0.085), 0.007, mat="steel", n=5, ends=0.011)
                def ts(r, ch, th): return ((r, ch * 0.32, 0), (r, -ch * 0.68, 0), th, Z)
                wing(M, "tr_blade", [ts(0.22, 0.12, 0.03), ts(0.34, 0.20, 0.026), ts(0.84, 0.20, 0.022)], "blade")
                wing(M, "tr_tip_white", [ts(0.84, 0.20, 0.022), ts(0.93, 0.20, 0.021)], "tipw", caps=(False, False))
                wing(M, "tr_tip_yellow", [ts(0.93, 0.20, 0.021), ts(1.02, 0.19, 0.019), ts(R_TAIL, 0.13, 0.012)], "tipy", caps=(False, True))

    # ================================================================= landing gear, chocks under it
    def wheel(b, c, r, hw, n=22):
        """Tyre and two-piece bolted hub about the Y axis at c (outboard = +Y)."""
        spun(b, "tyre", c, Y, [(r * 0.56, -hw * 0.80), (r * 0.80, -hw), (r * 0.955, -hw * 0.86), (r, -hw * 0.50), (r, hw * 0.50), (r * 0.955, hw * 0.86), (r * 0.80, hw), (r * 0.56, hw * 0.80)], n=n, mat="tyre")
        spun(b, "hub_out", c, Y, [(r * 0.56, hw * 0.80), (r * 0.50, hw * 0.55), (r * 0.26, hw * 0.50), (r * 0.20, hw * 0.92), (0.0, hw * 0.95)], n=n, mat="wheel")
        spun(b, "hub_in", c, Y, [(0.0, -hw * 0.70), (r * 0.50, -hw * 0.62), (r * 0.56, -hw * 0.80)], n=n, mat="wheel")
        lm.bolts(b, [V(c) + V((r * 0.38 * math.cos(k * math.pi / 4), hw * 0.52, r * 0.38 * math.sin(k * math.pi / 4))) for k in range(8)], Y, r=r * 0.045, h=r * 0.04, mat="steel")
        for g in (-0.5, 0.0, 0.5):                                         # tread grooves, bake-only dark bands
            spun(b, "d_groove", V(c) + Y * (hw * g), Y, [(r + 0.0015, -0.006), (r + 0.0015, 0.006)], n=n, mat="soot", detail=True)
    WM, RM, WN, RN_ = V((-0.90, 1.52, 0.26)), 0.26, V((3.00, 0.115, 0.19)), 0.19
    for sg in both(M):
        wheel(M, WM, RM, 0.10)
        lm.sect(M, "trailing_arm", (-0.30, 1.36, 0.53), (WM.x, 1.36, WM.z), rect(0.075, 0.095), Y, "gear", caps=(True, True))
        M.cyl("arm_pivot", (-0.30, 1.30, 0.53), (-0.30, 1.42, 0.53), 0.05, n=10, mat="steel")
        M.box("pivot_bracket", (-0.38, 1.285, 0.49), (-0.22, 1.435, 0.62), mat="gear", bev=0.01, skip="+z")
        M.cyl("axle", (WM.x, 1.31, WM.z), (WM.x, 1.445, WM.z), 0.04, n=10, mat="steel")
        M.cyl("axle_nut", (WM.x, 1.29, WM.z), (WM.x, 1.31, WM.z), 0.05, n=6, mat="steel")
        M.cyl("oleo_case", (-0.58, 1.36, 0.80), (-0.69, 1.36, 0.535), 0.055, n=12, mat="gear")
        M.cyl("oleo_gland", (-0.685, 1.36, 0.545), (-0.70, 1.36, 0.51), 0.062, n=12, mat="steel")
        rod(M, "oleo_piston", (-0.69, 1.36, 0.53), (-0.78, 1.36, 0.37), 0.032, mat="chrome", n=12)
        M.box("oleo_lug", (-0.83, 1.33, 0.33), (-0.74, 1.39, 0.40), mat="gear", bev=0.008)
        M.cyl("brake_disc", (WM.x, 1.418, WM.z), (WM.x, 1.432, WM.z), 0.135, n=18, mat="steel")
        M.box("brake_caliper", (WM.x - 0.07, 1.39, WM.z + 0.07), (WM.x + 0.07, 1.455, WM.z + 0.16), mat="dark", bev=0.01)
        H.path(M, "brake_line", [V((WM.x, 1.40, WM.z + 0.16)), V((-0.80, 1.40, 0.50)), V((-0.66, 1.41, 0.62)), V((-0.60, 1.42, 0.78))], 0.006, 0.006, Y, "dark", n=5)
        # nose wheels (twin)
        wheel(M, WN, RN_, 0.058, n=18)
        # boarding step under the cabin door: tread on two arms
        M.box("step_tread", (1.02, 1.13, 0.385), (1.52, 1.37, 0.41), mat="alu", bev=0.004)
        for k in range(7): M.box("d_step_rib", (1.03, 1.15 + 0.033 * k, 0.41), (1.51, 1.158 + 0.033 * k, 0.414), mat="alu", detail=True)
        for x in (1.05, 1.49):
            lm.sect(M, "step_arm", (x, 1.04, 0.63), (x, 1.15, 0.40), rect(0.012, 0.045), X, "alu", caps=(True, True))
            M.cyl("step_pivot", (x - 0.012, 1.045, 0.625), (x + 0.012, 1.045, 0.625), 0.02, n=8, mat="steel")
        # chocks fore and aft of the main wheel, joined by a rope
        for nm, O, ol in (("chock_f", (WM.x + 0.185, 1.65, 0), [(0, 0), (0.21, 0), (0.15, 0.13), (0.035, 0.13)]), ("chock_r", (WM.x - 0.185, 1.65, 0), [(-0.035, 0.13), (-0.15, 0.13), (-0.21, 0), (0, 0)])):
            b_tag = M.tag; M.tag = 3; M.prism(nm, O, X, Z, ol, 0.0, 0.26, mat="chock", bev=0.012); M.tag = b_tag
        M.tag = 3; H.path(M, "chock_rope", [V((WM.x + 0.30, 1.67, 0.06)), V((WM.x + 0.24, 1.72, 0.012)), V((WM.x, 1.76, 0.012)), V((WM.x - 0.24, 1.72, 0.012)), V((WM.x - 0.30, 1.67, 0.06))], 0.009, 0.009, Z, "rope", n=5); M.tag = 2
    M.cyl("nose_case", (3.0, 0, 0.68), (3.0, 0, 0.42), 0.058, n=12, mat="gear")
    M.cyl("nose_collar", (3.0, 0, 0.40), (3.0, 0, 0.455), 0.074, n=12, mat="steel", bev=0.006)
    rod(M, "nose_piston", (3.0, 0, 0.42), (3.0, 0, 0.25), 0.034, mat="chrome", n=12)
    M.box("nose_fork", (2.945, -0.05, 0.14), (3.055, 0.05, 0.27), mat="gear", bev=0.012)
    M.cyl("nose_axle", (3.0, -0.185, WN.z), (3.0, 0.185, WN.z), 0.026, n=8, mat="steel")
    rod(M, "scissor_up", (3.065, 0, 0.43), (3.19, 0, 0.34), 0.016, mat="gear", n=6, ends=0.022)
    rod(M, "scissor_lo", (3.19, 0, 0.34), (3.065, 0, 0.245), 0.016, mat="gear", n=6, ends=0.022)
    for s_ in (-1, 1): M.box("tow_lug", (3.05, s_ * 0.06 - 0.008, 0.16), (3.10, s_ * 0.06 + 0.008, 0.215), mat="gear", bev=0.003)
    H.path(M, "nose_hose", [V((2.96, 0.05, 0.27)), V((2.93, 0.07, 0.36)), V((2.94, 0.06, 0.46)), V((2.95, 0.05, 0.60))], 0.006, 0.006, Y, "dark", n=5)
    M.tag = 3
    for nm, O, ol in (("nchock_f", (WN.x + 0.125, 0.19, 0), [(0, 0), (0.16, 0), (0.115, 0.10), (0.03, 0.10)]), ("nchock_r", (WN.x - 0.125, 0.19, 0), [(-0.03, 0.10), (-0.115, 0.10), (-0.16, 0), (0, 0)])):
        M.prism(nm, O, X, Z, ol, 0.0, 0.38, mat="chock", bev=0.01)

    # ================================================================= tie-downs (object heli_tiedown): straps, blade socks and ropes
    DR = [V((5.3 * math.cos(a), 5.3 * math.sin(a), 0.0)) - DECK for a in [math.pi / 8 + k * math.pi / 4 for k in range(8)]]   # deck tie-down points in this frame
    def near(p): return min(DR, key=lambda d: (d - V((p[0], p[1], 0))).length)
    def strap(p0, p1, name="strap"):
        """Ratchet strap from an aircraft ring p0 to a deck point p1: hook, webbing, ratchet, webbing, hook and deck ring."""
        p0, p1 = V(p0), V(p1) + Z * 0.035; d = (p1 - p0).normalized(); side = d.cross(Z).normalized(); up = side.cross(d)
        pr = p0 + (p1 - p0) * 0.36
        H.path(M, name, H.sag(p0 + d * 0.09, pr - d * 0.07, 0.006, 3), 0.024, 0.003, side, "strap")
        H.path(M, name, H.sag(pr + d * 0.07, p1 - d * 0.10, 0.012, 5), 0.024, 0.003, side, "strap")
        for q, sgn in ((p0, 1), (p1, -1)):
            lm.sweep(M, name + "_hook", [q + d * sgn * 0.10, q + d * sgn * 0.035, q - d * sgn * 0.012 + up * 0.012, q - d * sgn * 0.02 + up * 0.04], [(0.007, 0.007)] * 4, side, n=5, mat="steel")
        with at(frame(pr, d, up), M):
            for s_ in (-1, 1): M.box(name + "_ratchet_side", (-0.07, s_ * 0.03 - 0.002, -0.012), (0.07, s_ * 0.03 + 0.002, 0.022), mat="steel")
            M.cyl(name + "_ratchet_drum", (0.0, -0.032, 0.004), (0.0, 0.032, 0.004), 0.013, n=8, mat="steel")
            M.box(name + "_ratchet_handle", (-0.01, -0.027, 0.02), (0.11, 0.027, 0.03), mat="dark", bev=0.003)
        with at(tr(p1 - Z * 0.035), M): M.torus(name + "_deck_ring", (0, 0, 0.012), 0.05, 0.011, n=12, m=5, mat="steel")
    for sg in (1, -1):
        for x in LUGS:
            p0 = V((x, sg * (lug_y(x) + 0.06), SZ - 0.085))
            strap(p0, near((x + (0.9 if x > 0 else -0.6), sg * 4.9)))
    SOCK_TO = {0: V((3.085, 0, 0.19)), 1: V((LUGS[0], lug_y(LUGS[0]) + 0.05, SZ - 0.07)), 4: V((LUGS[0], -lug_y(LUGS[0]) - 0.05, SZ - 0.07)), 2: V((-4.40, 0.33, 1.72)), 3: V((-4.40, -0.33, 1.72))}
    for k in range(NB):
        T = blade_frame(k)
        with at(T, M):
            M.box("blade_sock", (5.26, -0.31, droop(5.5) - 0.045), (5.73, 0.135, droop(5.5) + 0.045), mat="sock", bev=0.03)
            M.box("sock_tab", (5.30, -0.16, droop(5.5) - 0.085), (5.36, -0.10, droop(5.5) - 0.04), mat="sock", bev=0.004)
        a = T @ V((5.33, -0.13, droop(5.5) - 0.085)); c = SOCK_TO[k]
        H.path(M, "sock_rope", H.sag(a, c, 0.05, 6), 0.007, 0.007, (c - a).cross(Z).normalized(), "rope", n=5)
    for sg in (1, -1):                                                     # pitot covers with streamers
        p, n = F.pn(3.98, 1.72, sg); q = p + n * 0.11 + X * 0.22
        M.cyl("pitot_cover", q - X * 0.06, q + X * 0.09, 0.017, n=8, mat="sock", bev=0.004)
        H.path(M, "pitot_streamer", [q - X * 0.02 - Z * 0.015, q - X * 0.03 - Z * 0.09, q - X * 0.02 - Z * 0.17, q - X * 0.035 - Z * 0.25], 0.011, 0.002, X, "sock")

    # ================================================================= interior: seats, cockpit
    def seat(x, y, mat, pilot=False):
        with at(tr(x, y, ZF), I):
            for s_ in (-1, 1):
                I.box("seat_leg", (-0.17, s_ * 0.19 - 0.012, 0), (0.17, s_ * 0.19 + 0.012, 0.03), mat="trim")
                lm.sect(I, "seat_strut", (-0.16, s_ * 0.19, 0.03), (0.0, s_ * 0.19, 0.28), rect(0.02, 0.02), Y, "trim")
                lm.sect(I, "seat_strut", (0.16, s_ * 0.19, 0.03), (0.0, s_ * 0.19, 0.28), rect(0.02, 0.02), Y, "trim")
            I.box("seat_pan", (-0.22, -0.225, 0.27), (0.24, 0.225, 0.39), mat=mat, bev=0.03)
            with at(tr(-0.20, 0, 0.37) @ rot("Y", -11), I):
                hgt = 0.66 if pilot else 0.60
                I.box("seat_back", (-0.05, -0.225, 0.0), (0.05, 0.225, hgt), mat=mat, bev=0.03)
                I.box("headrest", (-0.045, -0.13, hgt - 0.01), (0.055, 0.13, hgt + 0.19), mat=mat, bev=0.03)
                I.box("seat_shell", (-0.062, -0.235, 0.02), (-0.05, 0.235, hgt - 0.04), mat="trim", skip="+x")
                for s_ in (-1, 1): I.box("harness", (0.050, s_ * 0.085 - 0.024, 0.06), (0.056, s_ * 0.085 + 0.024, hgt - 0.02), mat="harness", skip="-x")
                I.box("buckle", (0.050, -0.04, 0.03), (0.066, 0.04, 0.10), mat="trim", bev=0.006, skip="-x")
            for s_ in (-1, 1): I.box("lap_belt", (0.02, s_ * 0.13 - 0.024, 0.39), (0.12, s_ * 0.13 + 0.024, 0.396), mat="harness", skip="-z")
            if pilot:
                for s_ in (-1, 1): I.box("armrest", (-0.16, s_ * 0.25 - 0.025, 0.52), (0.14, s_ * 0.25 + 0.025, 0.55), mat="trim", bev=0.008)
    for y in (-0.5, 0.5): seat(2.30, y, "seatg", True)
    for x, ys in ((1.02, (-0.68, -0.20, 0.56)), (0.18, (-0.68, -0.20, 0.56)), (-0.68, (-0.74, -0.25, 0.25, 0.74))):
        for y in ys: seat(x, y, "seatb")
    I.box("glareshield", (2.90, -0.84, 1.40), (3.30, 0.84, 1.45), mat="panel", bev=0.015)
    I.box("instrument_panel", (3.02, -0.80, 0.98), (3.12, 0.80, 1.41), mat="panel", bev=0.01, skip="+z")
    for (y0, y1) in ((-0.74, -0.50), (-0.47, -0.23), (0.23, 0.47), (0.50, 0.74)):
        I.box("display", (3.012, y0, 1.13), (3.02, y1, 1.36), mat="screen", skip="+x")
        I.box("d_bezel", (3.016, y0 - 0.012, 1.118), (3.02, y1 + 0.012, 1.372), mat="panel", detail=True)
    for k in range(3): I.cyl("d_standby", (3.02, 0.0, 1.15 + 0.075 * k), (3.012, 0.0, 1.15 + 0.075 * k), 0.03, n=14, mat="screen", detail=True, caps=(False, True))
    for y in np.linspace(-0.7, 0.7, 15):
        if abs(y) > 0.2: I.box("d_knob", (3.008, y - 0.012, 1.03), (3.02, y + 0.012, 1.055), mat="trim", detail=True)
    I.box("pedestal", (2.42, -0.15, ZF), (3.05, 0.15, 1.00), mat="panel", bev=0.012, skip="-z")
    I.box("pedestal_riser", (2.86, -0.15, 1.0), (3.05, 0.15, 1.06), mat="panel", bev=0.008, skip="-z")
    for kx in range(9):
        for ky in range(5):
            I.box("d_switch", (2.47 + 0.042 * kx, -0.105 + 0.05 * ky, 1.0), (2.495 + 0.042 * kx, -0.08 + 0.05 * ky, 1.008 + 0.004 * ((kx + ky) % 3)), mat="trim" if (kx * 3 + ky) % 4 else "harness", detail=True)
    I.box("overhead_panel", (2.02, -0.22, 2.20), (2.52, 0.22, 2.27), mat="panel", bev=0.01)
    for s_ in (-1, 1):
        lm.sect(I, "engine_lever", (2.30, s_ * 0.05, 2.20), (2.36, s_ * 0.05, 2.08), rect(0.016, 0.03), Y, "trim", caps=(False, True))
        I.box("lever_knob", (2.34, s_ * 0.05 - 0.018, 2.05), (2.385, s_ * 0.05 + 0.018, 2.09), mat="panel", bev=0.006)
    I.box("rotor_brake", (2.12, 0.12, 2.12), (2.16, 0.16, 2.20), mat="harness", bev=0.004)
    for kx in range(8):
        for ky in range(6): I.cyl("d_breaker", (2.06 + 0.055 * kx, -0.19 + 0.045 * ky + (0.11 if ky > 2 else 0) * 0, 2.20), (2.06 + 0.055 * kx, -0.19 + 0.045 * ky, 2.193), 0.008, n=6, mat="trim", detail=True, caps=(False, True))
    for y in (-0.5, 0.5):
        lm.sweep(I, "cyclic", [V((2.66, y, ZF)), V((2.64, y, 0.98)), V((2.58, y, 1.12)), V((2.56, y, 1.20))], [(0.014, 0.014)] * 4, Y, n=6, mat="trim")
        I.box("cyclic_grip", (2.525, y - 0.022, 1.18), (2.585, y + 0.022, 1.31), mat="panel", bev=0.01)
        I.box("cyclic_boot", (2.60, y - 0.05, ZF), (2.72, y + 0.05, ZF + 0.05), mat="panel", bev=0.015, skip="-z")
        lm.sect(I, "collective", (2.10, y + 0.31, ZF + 0.06), (2.52, y + 0.31, 1.06), rect(0.028, 0.028), Y, "trim", caps=(True, True))
        I.box("collective_head", (2.49, y + 0.28, 1.03), (2.60, y + 0.34, 1.13), mat="panel", bev=0.01)
        I.box("collective_base", (2.04, y + 0.27, ZF), (2.18, y + 0.35, ZF + 0.09), mat="panel", bev=0.01, skip="-z")
        for s_ in (-1, 1):
            I.box("pedal", (2.94, y + s_ * 0.13 - 0.045, ZF + 0.10), (2.96, y + s_ * 0.13 + 0.045, ZF + 0.24), mat="trim", bev=0.004)
            lm.sect(I, "pedal_arm", (2.95, y + s_ * 0.13, ZF + 0.12), (3.02, y + s_ * 0.13, ZF + 0.0), rect(0.02, 0.012), Y, "trim")
    I.box("cabin_step_strip", (1.50, -1.02, ZF), (1.58, 1.02, ZF + 0.006), mat="trim", skip="-z")
    for x in (0.6, -0.25, -1.1):                                             # ceiling light bars
        I.box("cabin_light", (x - 0.12, -0.05, 2.375), (x + 0.12, 0.05, 2.39), mat="lampw", skip="+z")



    glass = Mesh()
    for face in GLASS:
        glass.faces.new([glass.verts.new(p) for p in face])
    B._obj(glass, "window_glass", "glass")
    B.lo = paint_panels(B.lo)
    for build, assembly in ((B,"body"), (M,"mechanics"), (I,"interior")):
        for part in build.lo + build.hi:
            part.material = "window_glass" if part.name == "window_glass" else assembly + "_" + part.material
    return B.lo + M.lo + I.lo + B.hi + M.hi + I.hi
