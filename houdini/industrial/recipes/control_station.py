import math
from .. import equipment as eq
from ..equipment import pw, V, T, at, frame, Matrix
from ..geometry import Mesh

def build():
    b = eq.new("control_station")
    HX, HY, H = 0.6, 0.3, 2.0
    G, S = "lgrey", "stainless"
    ZB = 0.02                       # base plate top
    YB = HY - 0.024                 # back panel front face
    PX0, PX1 = 0.46, 0.56           # post
    PY0 = 0.03                      # post front
    CX, CY0, CY1, CZ0, CZ1 = 0.44, -0.215, PY0, 1.0, 1.8      # cabinet body
    YD = CY0 - 0.026                # door face

    # ---------------- base plate, anchor bolts
    b.box("base", (-HX, -HY, 0), (HX, HY, ZB), mat=G, bev=0.004, skip="-z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            q = (sx * (HX - 0.045), sy * (HY - 0.05), ZB)
            b.cyl("nut", q, (q[0], q[1], ZB + 0.022), 0.02, n=6, mat="steel", caps=(False, True))
            b.cyl("d_stud", (q[0], q[1], ZB + 0.02), (q[0], q[1], ZB + 0.034), 0.01, n=8, mat="steel", caps=(False, True), detail=True)
            b.cyl("d_washer", (q[0], q[1], ZB - 0.001), (q[0], q[1], ZB + 0.003), 0.03, n=12, mat="steel", caps=(False, True), detail=True)

    # ---------------- back panel (closed, deck to canopy), posts, gussets
    ZP = 1.9
    b.box("back", (-PX1, YB, ZB), (PX1, HY - 0.012, ZP), mat=G, skip="-z,+z")
    for x0, x1 in ((-PX1, -PX1 + 0.05), (-0.025, 0.025), (PX1 - 0.05, PX1)):      # flat-bar stiffeners on the back
        b.box("back_rib", (x0, HY - 0.012, ZB), (x1, HY, ZP), mat=G, skip="-z,+z,-y", bev=0.003, bev_axes="z")
    for z in (0.98, ZP - 0.04):
        b.box("back_rail", (-PX1 + 0.05, HY - 0.012, z - 0.03), (-0.025, HY - 0.002, z + 0.03), mat=G, skip="-x,+x,-y")
        b.box("back_rail", (0.025, HY - 0.012, z - 0.03), (PX1 - 0.05, HY - 0.002, z + 0.03), mat=G, skip="-x,+x,-y")
    for sx in (-1, 1):
        x0, x1 = sorted((sx * PX0, sx * PX1))
        b.box("post", (x0, PY0, ZB), (x1, YB, ZP), mat=G, skip="-z,+z,+y", bev=0.006, bev_axes="z")
        # front gusset and side foot gusset
        xm = sx * (PX0 + PX1) / 2
        b.prism("gusset", (xm, PY0, ZB), (0, -1, 0), (0, 0, 1), [(0, 0), (0.3, 0), (0.3, 0.03), (0, 0.72)], -0.006, 0.006, mat=G + "_t", skip_side=(0, 3))
        b.weld((xm - sx * 0.007, PY0 - 0.001, ZB + 0.01), (xm - sx * 0.007, PY0 - 0.001, ZB + 0.7), mat=G)
        b.weld((x0, PY0 + 0.01, ZB + 0.002), (x0, YB - 0.01, ZB + 0.002), mat=G)
        # bolted splice strap between post and back panel at mid height (bake only)
        for z in (0.62, 1.34):
            b.box("d_strap", (sx * (PX0 - 0.09), YB - 0.004, z - 0.045), (sx * PX0, YB + 0.001, z + 0.045), mat=G, detail=True, bev=0.002)
            b.bolt((sx * (PX0 - 0.045), YB - 0.004, z), (0, -1, 0), r=0.011, mat="steel")
    for z in (0.62, 1.34):       # rivet line across the back of the panel, and the panel joint
        for i in range(7): b.cyl("bolt", (-0.48 + i * 0.16, HY - 0.012, z), (-0.48 + i * 0.16, HY, z), 0.012, n=6, mat="steel", caps=(False, True), r1=0.011)
    b.box("d_joint", (-PX1 + 0.01, HY - 0.013, 0.975), (PX1 - 0.01, HY - 0.0105, 0.985), mat="dark", detail=True)

    # ---------------- cabinet: body, door with a folded edge, gasket line, seam welds
    b.box("cabinet", (-CX, CY0, CZ0), (CX, CY1, CZ1), mat=S, bev=0.006, skip="+y")
    XD0, XD1 = -CX + 0.035, CX - 0.035
    b.box("door", (XD0, YD, CZ0 + 0.03), (XD1, CY0, CZ1 - 0.03), mat=S, bev=0.006, skip="+y")
    b.box("d_gasket", (-CX + 0.03, CY0 - 0.004, CZ0 + 0.025), (CX - 0.03, CY0 + 0.001, CZ1 - 0.025), mat="dark", detail=True)
    for q in ((XD0 + 0.012, CZ0 + 0.042, XD1 - 0.012, CZ0 + 0.05), (XD0 + 0.012, CZ1 - 0.05, XD1 - 0.012, CZ1 - 0.042), (XD0 + 0.012, CZ0 + 0.042, XD0 + 0.02, CZ1 - 0.042), (XD1 - 0.02, CZ0 + 0.042, XD1 - 0.012, CZ1 - 0.042)):
        b.box("d_press", (q[0], YD - 0.0025, q[1]), (q[2], YD + 0.001, q[3]), mat=S, detail=True, bev=0.002)
    for x in (-CX + 0.012, CX - 0.012):
        b.weld((x, CY0 - 0.001, CZ0 + 0.02), (x, CY0 - 0.001, CZ1 - 0.02), r=0.003, mat=S)
    b.bolt((CX, -0.05, CZ0 + 0.06), (1, 0, 0), r=0.008, mat="brass")
    # window: rubber gasket frame with rounded corners, glass set back in it, a dim display behind
    WX0, WX1, WZ0, WZ1 = -0.2, 0.12, 1.47, 1.7
    wc = ((WX0 + WX1) / 2, (WZ0 + WZ1) / 2); wh = ((WX1 - WX0) / 2, (WZ1 - WZ0) / 2)


    def rrect(hw, hh, r):
        out = []
        for cx, cz, a0 in ((hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180), (hw - r, -hh + r, 270)):
            out += [(cx + r * math.cos(math.radians(a0 + a)), cz + r * math.sin(math.radians(a0 + a))) for a in (0, 45, 90)]
        return out


    b.ring_plate("window_gasket", (wc[0], YD, wc[1]), (1, 0, 0), (0, 0, 1), rrect(wh[0] + 0.032, wh[1] + 0.032, 0.035), rrect(wh[0], wh[1], 0.014), 0.0, 0.011, mat="rubber", back=False)
    eq.quad(b, "window", (WX0 - 0.002, YD - 0.003, WZ0 - 0.002), (1, 0, 0), (0, 0, 1), WX1 - WX0 + 0.004, WZ1 - WZ0 + 0.004, "glass")
    b.box("d_screen", (WX0 + 0.03, YD - 0.0038, WZ0 + 0.03), (WX1 - 0.03, YD - 0.003, WZ1 - 0.03), mat="liquid", detail=True)
    for i in range(5): b.box("d_scr_line", (WX0 + 0.045, YD - 0.0044, WZ1 - 0.06 - i * 0.028), (WX1 - 0.05 - 0.04 * (i % 2), YD - 0.0038, WZ1 - 0.05 - i * 0.028), mat="black", detail=True)
    # lamps and push buttons with tag plates, emergency stop on a yellow disc
    ZL = 1.24
    for i, m in enumerate(("lampg", "lampg", "lampy", "lampr", "black")):
        x = -0.3 + i * 0.09
        with at(b, frame((x, YD, ZL), (0, -1, 0))):
            b.lathe("bezel", [(0.027, 0.0), (0.027, 0.006), (0.021, 0.011)], n=10, mat="steel", phase=0.0)
            b.lathe("lamp", [(0.018, 0.009), (0.018, 0.02), (0.012, 0.026), (0.0, 0.027)], n=10, mat=m, phase=0.0)
        b.box("d_tagplate", (x - 0.024, YD - 0.002, ZL + 0.04), (x + 0.024, YD + 0.001, ZL + 0.062), mat="steel", detail=True, bev=0.001)
        b.box("d_tagline", (x - 0.016, YD - 0.0026, ZL + 0.049), (x + 0.016, YD - 0.002, ZL + 0.054), mat="black", detail=True)
    XE = 0.26
    with at(b, frame((XE, YD, ZL), (0, -1, 0))):
        b.lathe("estop_disc", [(0.06, 0.0), (0.06, 0.005), (0.03, 0.006)], n=12, mat="yellow", phase=0.0)
        b.lathe("estop", [(0.03, 0.006), (0.03, 0.02), (0.042, 0.023), (0.042, 0.038), (0.03, 0.048), (0.0, 0.05)], n=10, mat="lampr", phase=0.0)
        b.torus("d_estop_ring", (0, 0, 0.0052), 0.046, 0.0025, n=24, m=6, mat="black", detail=True)
    # D handle and two quarter-turn latches (right), two lift-off hinges (left)
    XH = XD1 - 0.055
    pw.tube(b, "handle", pw.route([(XH, YD, 1.52), (XH, YD - 0.045, 1.52), (XH, YD - 0.045, 1.32), (XH, YD, 1.32)], 0.018, k=2), 0.009, n=6, mat=S)
    for z in (1.52, 1.32):
        b.cyl("handle_boss", (XH, YD, z), (XH, YD - 0.007, z), 0.019, n=8, mat=S, caps=(False, True))
    for z in (CZ0 + 0.14, CZ1 - 0.14):
        with at(b, frame((XD1 - 0.03, YD, z), (0, -1, 0), (1, 0, 0))):
            b.lathe("latch", [(0.022, 0.0), (0.022, 0.007), (0.017, 0.01), (0.0, 0.01)], n=10, mat="steel", phase=0.0)
            b.box("d_latch_slot", (-0.014, -0.003, 0.0096), (0.014, 0.003, 0.0106), mat="black", detail=True)
            b.torus("d_latch_ring", (0, 0, 0.0005), 0.027, 0.002, n=20, m=6, mat="black", detail=True)
    for z in (1.16, 1.62):
        b.box("hinge_leaf_body", (-CX + 0.003, CY0 - 0.005, z - 0.045), (XD0 - 0.003, CY0, z + 0.045), mat=S, skip="+y", bev=0.002)
        b.box("hinge_block", (XD0 - 0.02, YD + 0.003, z - 0.045), (XD0 - 0.003, CY0 - 0.005, z + 0.045), mat=S, skip="+y,-y")
        b.box("hinge_leaf_door", (XD0 + 0.002, YD - 0.005, z - 0.045), (XD0 + 0.042, YD, z + 0.045), mat=S, skip="+y", bev=0.002)
        b.cyl("hinge_barrel", (XD0 - 0.008, YD - 0.004, z - 0.05), (XD0 - 0.008, YD - 0.004, z + 0.05), 0.011, n=8, mat="steel")
        for dz in (-0.017, 0.017):
            with at(b, T(V((XD0 - 0.008, YD - 0.004, z + dz)))): b.lathe("d_knuckle", [(0.0114, -0.0015), (0.0114, 0.0015)], n=16, mat="black", detail=True, phase=0.0)
        for dz in (-0.028, 0.028):
            b.bolt((XD0 + 0.024, YD - 0.005, z + dz), (0, -1, 0), r=0.005, h=0.003, mat="steel")
            b.bolt((-CX + 0.017, CY0 - 0.005, z + dz), (0, -1, 0), r=0.005, h=0.003, mat="steel")
    for sx in (-1, 1):          # cabinet fixing lugs on the posts
        for z in (CZ0 + 0.08, CZ1 - 0.08):
            b.box("fix", (sx * CX - (0.0 if sx > 0 else 0.03), CY1 - 0.05, z - 0.03), (sx * CX + (0.03 if sx > 0 else 0.0), CY1, z + 0.03), mat=S, skip="+y" + (",-x" if sx > 0 else ",+x"))
            b.bolt((sx * (CX + 0.015), CY1 - 0.05, z), (0, -1, 0), r=0.008, mat="steel")
    b.box("d_tag", (-0.09, YD - 0.002, 1.74), (0.09, YD + 0.001, 1.765), mat="black", detail=True)
    b.box("d_tag_in", (-0.08, YD - 0.0026, 1.746), (0.03, YD - 0.002, 1.759), mat="steel", detail=True)

    # ---------------- cable glands under the cabinet, conduits down to the deck in saddle clamps on three strut rails
    YC = -0.06
    CON = ((-0.11, 0.019), (0.0, 0.023), (0.11, 0.019))
    for x, r in CON:
        with at(b, frame((x, YC, 0), (0, 0, 1), (1, 0, 0))):
            b.lathe("gland", [(r + 0.002, CZ0 - 0.115), (r + 0.013, CZ0 - 0.11), (r + 0.013, CZ0 - 0.078), (r + 0.006, CZ0 - 0.074), (r + 0.006, CZ0 - 0.04), (r + 0.018, CZ0 - 0.04), (r + 0.018, CZ0 - 0.01), (r + 0.01, CZ0 - 0.006), (r + 0.01, CZ0)], n=6, mat="steel", phase=0.0)
            for k in range(4): b.lathe("d_thread", [(r + 0.0064, CZ0 - 0.07 + k * 0.008), (r + 0.0078, CZ0 - 0.067 + k * 0.008), (r + 0.0064, CZ0 - 0.064 + k * 0.008)], n=12, mat="steel", detail=True, phase=0.0)
            b.lathe("deck_gland", [(r + 0.02, ZB), (r + 0.02, ZB + 0.012), (r + 0.012, ZB + 0.014), (r + 0.012, ZB + 0.045), (r + 0.001, ZB + 0.06)], n=6, mat="steel", phase=0.0)
        pw.tube(b, "conduit", [(x, YC, ZB + 0.05), (x, YC, CZ0 - 0.11)], r, n=8, mat="galv")
        for z in (0.36, 0.68):       # couplings on the conduit (bake only)
            with at(b, T(V((x, YC, z)))): b.lathe("d_coupling", [(r + 0.0005, -0.022), (r + 0.004, -0.019), (r + 0.004, 0.019), (r + 0.0005, 0.022)], n=12, mat="steel", detail=True, phase=0.0)
    with at(b, frame((0.24, YC + 0.02, 0), (0, 0, 1), (1, 0, 0))):      # a spare entry with a blanking plug; a small gland with an earth cable
        b.lathe("plug", [(0.0, CZ0 - 0.012), (0.016, CZ0 - 0.012), (0.016, CZ0)], n=6, mat="steel", phase=0.0)
    pw.tube(b, "earth", pw.route([(-0.24, YC + 0.02, CZ0 - 0.04), (-0.24, YC + 0.02, CZ0 - 0.2), (-0.24, YB - 0.012, CZ0 - 0.34), (-0.24, YB - 0.012, 0.5)], 0.05, k=2), 0.007, n=4, mat="rubber", caps=(False, True))
    with at(b, frame((-0.24, YC + 0.02, 0), (0, 0, 1), (1, 0, 0))):
        b.lathe("gland_s", [(0.008, CZ0 - 0.05), (0.014, CZ0 - 0.046), (0.014, CZ0 - 0.02), (0.018, CZ0 - 0.02), (0.018, CZ0)], n=6, mat="steel", phase=0.0)
    for z in (0.2, 0.52, 0.84):
        b.box("rail", (-0.2, YC + 0.018, z - 0.02), (0.2, YC + 0.045, z + 0.02), mat="galv", skip="-x,+x")
        for k in range(5): b.box("d_rail_slot", (-0.17 + k * 0.08, YC + 0.0176, z - 0.007), (-0.13 + k * 0.08, YC + 0.0184, z + 0.007), mat="dark", detail=True)
        for sx in (-1, 1):
            b.box("rail_arm", (sx * 0.2 - 0.015, YC + 0.018, z - 0.02), (sx * 0.2 + 0.015, YB, z + 0.02), mat="galv", skip="+y")
        for x, r in CON:      # saddle clamp: a strap over the conduit with an ear and a bolt each side
            b.box("clamp", (x - r - 0.004, YC - r - 0.004, z - 0.012), (x + r + 0.004, YC + 0.018, z + 0.012), mat="steel", skip="+y", bev=0.006, bev_axes="z")
            for sx in (-1, 1):
                x0, x1 = sorted((x + sx * (r + 0.004), x + sx * (r + 0.022)))
                b.box("clamp_ear", (x0, YC + 0.014, z - 0.012), (x1, YC + 0.018, z + 0.012), mat="steel", skip="+y,%sx" % ("-" if sx > 0 else "+"))
                b.bolt((x + sx * (r + 0.013), YC + 0.014, z), (0, -1, 0), r=0.005, h=0.004, mat="steel")

    # ---------------- sunshade canopy: sloping top, cheeks, back wall, front drip lip
    ZF = H - 0.15                   # top of the canopy at the front
    b.prism("canopy", (0, 0, 0), (0, 1, 0), (0, 0, 1), [(HY, H - 0.012), (HY, H), (-HY, ZF), (-HY, ZF - 0.012)], -HX, HX, mat=G, bev=0.0)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * HX, sx * (HX - 0.008)))
        b.prism("cheek", (0, 0, 0), (0, 1, 0), (0, 0, 1), [(HY, ZP - 0.12), (HY, H - 0.012), (-HY, ZF - 0.012), (-HY, ZF - 0.06), (PY0 - 0.05, ZP - 0.12)], x0, x1, mat=G, skip_side=(1,))
    b.box("canopy_back", (-HX + 0.008, HY - 0.008, ZP - 0.12), (HX - 0.008, HY, H - 0.012), mat=G, skip="-x,+x,+z")
    b.box("drip", (-HX + 0.008, -HY, ZF - 0.06), (HX - 0.008, -HY + 0.008, ZF - 0.012), mat=G, skip="-x,+x,+z")
    b.box("canopy_rail", (-PX1, PY0, ZP - 0.05), (PX1, YB, ZP), mat=G, skip="-x,+x,+y,+z")
    b.box("gutter", (-CX - 0.01, CY0 - 0.045, CZ1), (CX + 0.01, CY1, CZ1 + 0.012), mat=S, skip="+y,-z", bev=0.003, bev_axes="x")
    for sx in (-1, 1):          # sunshade brackets: two angle cleats from each post to its cheek, a flat stay from the post to the front edge, bolts
        x0, x1 = sorted((sx * PX1, sx * (HX - 0.008)))
        for y in (0.07, 0.21):
            b.box("shade_cleat", (x0, y - 0.03, ZP - 0.1), (x1, y + 0.03, ZP - 0.094), mat=G + "_t", skip="-x,+x")
            xa, xb = sorted((sx * PX1, sx * (PX1 + 0.006)))
            b.box("shade_cleat_v", (xa, y - 0.03, ZP - 0.094), (xb, y + 0.03, ZP - 0.04), mat=G + "_t", skip="-z,%sx" % ("-" if sx > 0 else "+"))
            b.bolt((sx * HX, y, ZP - 0.075), (sx, 0, 0), r=0.009, mat="steel")
        pw.bar(b, "shade_stay", (sx * 0.51, PY0, 1.66), (sx * 0.51, -HY + 0.03, ZF - 0.055), pw.P_box(0.035, 0.006), up=(0, 0, 1), mat=G + "_t")
        for y in (-0.2, 0.0, 0.2): b.bolt((sx * (HX - 0.03), y, H - (HY - y) * 0.25 - 0.0005), (0, -0.24, 0.97), r=0.009, mat="steel")
    for x in (-0.3, 0.0, 0.3): b.bolt((x, 0.2, H - (HY - 0.2) * 0.25 - 0.0005), (0, -0.24, 0.97), r=0.009, mat="steel")
    for sx in (-1, 1):
        for z in (0.3, 0.9, 1.5):
            x = sx * PX1; b.cyl("bolt", (x - sx * 0.002, 0.16, z), (x + sx * 0.012, 0.16, z), 0.013, n=6, mat="steel", caps=(sx < 0, sx > 0))

    # ---------------- grime
    eq.run(b, (0.0, YB, CZ0), (0, -1, 0), 0.5, 0.9, (G,), i=2, strength=0.45)
    eq.run(b, (0.2, HY, 1.3), (0, 1, 0), 0.5, 1.2, (G,), i=4, strength=0.35)
    eq.puddle(b, (0.0, -0.1, ZB), 0.6, (G,), strength=0.5)
    eq.run(b, (0.1, YD, 1.2), (0, -1, 0), 0.5, 0.2, (S,), i=1, strength=0.3)
    eq.run(b, (-0.3, YD, CZ1 - 0.03), (0, -1, 0), 0.25, 0.6, (S,), i=3, strength=0.25)

    return b.lo + b.hi
