import math
from .. import equipment as eq
from ..equipment import pw, V, T, at, frame, Matrix
from ..geometry import Mesh

def build():
    b = eq.new("cable_reel")
    HX, HY, H = 0.95, 0.6, 1.9
    ZC, RF = 1.0, 0.9                 # axle height, flange radius
    YA, YB = -0.30, 0.42              # cable between the flanges
    FT = 0.03                         # flange plate
    BH = 0.16                         # base beam height
    N = 32
    Yw, G, LG, ST = "yellow", "grey", "lgrey", "steel"


    def side(sg):      # frame with local Z along the axle, pointing out of the reel on side sg
        return frame((0, 0, ZC), (0, sg, 0), (1, 0, 0))


    # ---------------- cable: one lathe, a ridge a turn
    TURNS = 14; p = (YB - YA) / TURNS
    prof = []
    for i in range(TURNS):
        prof += [(0.836, YA + i * p), (0.85, YA + (i + 0.5) * p)]
    prof += [(0.836, YB)]
    with at(b, side(1)):
        b.lathe("cable", prof, n=N, mat="rubber", phase=0.0)

    # ---------------- flanges: plate, rim ring, hub, ribs
    for sg, yin in ((1, YB), (-1, -YA)):
        z0, z1 = yin, yin + FT
        with at(b, side(sg)):
            b.lathe("flange", [(0.82, z0), (RF, z0), (RF, z1 + 0.02), (RF - 0.045, z1 + 0.02), (RF - 0.045, z1), (0.24, z1), (0.24, z1 + 0.03), (0.07, z1 + 0.03)], n=N, mat=LG, phase=0.0)
            for k in range(12):
                with at(b, Matrix.Rotation(math.radians(15 + 30 * k), 4, "Z")):
                    b.box("rib", (0.235, -0.022, z1), (RF - 0.04, 0.022, z1 + 0.022), mat=LG + "_t", skip="-z,-x,+x")
                    b.weld((0.26, 0.024, z1 + 0.001), (RF - 0.06, 0.024, z1 + 0.001), mat=LG)
            pw.bolts(b, 0.19, 8, 0.02, [(z1 + 0.03, 1)], False, ST)
            pw.bolts(b, 0.3, 12, 0.014, [(z1, 1)], False, ST, ph=0.0)
            b.lathe("boss", [(0.12, z1 + 0.03), (0.12, z1 + 0.05), (0.07, z1 + 0.05)], n=12, mat=LG, phase=0.0)

    # ---------------- axle and pillow blocks
    YF = (0.53, -0.41)                # A-frame planes (+Y, -Y)
    b.cyl("axle", (0, -0.47, ZC), (0, HY, ZC), 0.05, n=10, mat=ST, caps=(False, True))
    for yc in YF:
        b.box("pillow", (-0.13, yc - 0.045, ZC - 0.1), (0.13, yc + 0.045, ZC - 0.02), mat=Yw, bev=0.006, skip="-z")
        b.cyl("bearing", (0, yc - 0.05, ZC), (0, yc + 0.05, ZC), 0.1, n=12, mat=G, caps=(True, True))
        for sx in (-1, 1): b.bolt((sx * 0.105, yc, ZC - 0.02), (0, 0, 1), r=0.012, mat=ST)
    b.cyl("d_cap", (0, HY - 0.0005, ZC), (0, HY + 0.003, ZC), 0.03, n=10, mat=ST, caps=(False, True), detail=True)

    # ---------------- stand: base frame, floor plate, A-frames
    b.box("beam", (-HX, 0.44, 0), (HX, HY, BH), mat=Yw, bev=0.008, bev_axes="x", skip="-z")
    b.box("beam", (-HX, -HY, 0), (HX, -0.34, BH), mat=Yw, bev=0.008, bev_axes="x", skip="-z")
    for sx in (-1, 1):
        x0, x1 = sorted((sx * HX, sx * (HX - 0.12)))
        b.box("cross", (x0, -0.34, 0), (x1, 0.44, BH), mat=Yw, bev=0.008, bev_axes="y", skip="-z,-y,+y")
        for y in (-0.5, 0.52):
            b.bolt((sx * (HX - 0.07), y, BH), (0, 0, 1), r=0.02, h=0.012, mat=ST)
            b.box("d_washer", (sx * (HX - 0.07) - 0.045, y - 0.045, BH - 0.001), (sx * (HX - 0.07) + 0.045, y + 0.045, BH + 0.004), mat=ST, detail=True)
    b.box("floor", (-HX + 0.12, -0.34, 0), (HX - 0.12, 0.44, 0.03), mat="deck", skip="-z,-x,+x,-y,+y")
    for yc in YF:
        O = (0, yc, 0); ex, ey = (1, 0, 0), (0, 0, 1)
        b.prism("leg", O, ex, ey, [(0.66, BH), (0.9, BH), (0.14, ZC - 0.1), (-0.06, ZC - 0.1)], -0.04, 0.04, mat=Yw, caps=(True, True))
        b.prism("leg", O, ex, ey, [(-0.9, BH), (-0.66, BH), (0.06, ZC - 0.1), (-0.14, ZC - 0.1)], -0.04, 0.04, mat=Yw, caps=(True, True))
        b.box("tie", (-0.5, yc - 0.03, 0.42), (0.5, yc + 0.03, 0.52), mat=Yw, skip="-x,+x")
        b.box("apex", (-0.16, yc - 0.045, ZC - 0.2), (0.16, yc + 0.045, ZC - 0.1), mat=Yw, bev=0.006, skip="+z")
        for sx in (-1, 1):
            b.box("foot", (sx * 0.79 - 0.14, yc - 0.07, BH), (sx * 0.79 + 0.14, yc + 0.07, BH + 0.016), mat=Yw, bev=0.004, skip="-z")
            for dx in (-0.1, 0.1): b.bolt((sx * 0.79 + dx, yc + (0.055 if yc > 0 else -0.055), BH + 0.016), (0, 0, 1), r=0.011, mat=ST)

    # ---------------- chocks: full-width wedges under the reel, hazard stripes on their outer faces
    for sx in (-1, 1):
        out = [(0.46, 0.03), (0.84, 0.03), (0.84, 0.44), (0.75, 0.44)]
        if sx < 0: out = [(-x, z) for x, z in out][::-1]
        b.prism("chock", (0, 0, 0), (1, 0, 0), (0, 0, 1), out, -YB, -YA, mat=Yw, caps=(True, True))
        for k in range(5):
            y = YA + 0.04 + k * 0.15
            with at(b, frame((sx * 0.84, y + 0.03, 0.235), (sx, 0, 0), (0, 1, 0)) @ Matrix.Rotation(math.radians(55), 4, "Z")):
                b.box("d_stripe", (-0.03, -0.24, 0.0003), (0.03, 0.24, 0.001), mat="black", skip="-z", detail=True)

    # ---------------- drive on the -Y side: shelf, gearbox on the axle, motor along +X, junction box, conduit
    YG0, YG1 = -HY, -0.46
    b.box("shelf", (-0.12, -HY, 0.76), (0.72, -0.455, 0.82), mat=Yw, bev=0.005, bev_axes="x")
    b.prism("gusset", (0, -0.5, 0), (1, 0, 0), (0, 0, 1), [(0.25, 0.76), (0.3, 0.62), (0.7, 0.76)], -0.03, 0.03, mat=Yw + "_t", caps=(True, True), skip_side=(2,))
    b.box("gearbox", (-0.1, YG0, 0.82), (0.26, YG1, 1.17), mat=G, bev=0.012)
    for x in (-0.06, 0.22):
        for z in (0.87, 1.12): b.bolt((x, YG0, z), (0, -1, 0), r=0.012, mat=ST)
    b.cyl("d_cover", (0, YG0 + 0.0005, ZC), (0, YG0 - 0.004, ZC), 0.085, n=16, mat=G, caps=(False, True), detail=True)
    ym = -0.51
    with at(b, frame((0.26, ym, ZC), (1, 0, 0), (0, 0, 1))):
        b.lathe("motor", [(0.06, 0.0), (0.06, 0.05), (0.082, 0.05), (0.082, 0.34), (0.088, 0.34), (0.088, 0.42), (0.07, 0.435), (0.0, 0.435)], n=12, mat=G, phase=0.0)
        for i in range(13):
            z = 0.07 + i * 0.02; b.lathe("d_fin", [(0.0822, z), (0.0865, z + 0.002), (0.0865, z + 0.007), (0.0822, z + 0.009)], n=12, mat=G, detail=True, phase=0.0)
    b.box("foot_m", (0.35, -0.585, 0.82), (0.57, -0.455, 0.93), mat=G + "_t", skip="-z,+z")
    b.box("term", (0.39, -0.565, ZC + 0.07), (0.53, -0.475, ZC + 0.125), mat=G, bev=0.006, skip="-z")
    b.box("jbox", (0.45, -0.535, 0.3), (0.63, -0.45, 0.52), mat=LG, bev=0.006, skip="+y")
    for sx in (-1, 1):
        for sz in (0.325, 0.495): b.bolt((0.54 + sx * 0.07, -0.535, sz), (0, -1, 0), r=0.008, mat=ST)
    pw.tube(b, "conduit", [(0.56, -0.49, 0.52), (0.56, -0.49, 0.76)], 0.016, n=6, mat="rubber")
    pw.tube(b, "conduit", [(0.52, -0.49, 0.3), (0.52, -0.49, 0.2), (0.62, -0.49, 0.2), (0.62, -0.49, BH)], 0.016, n=6, mat="rubber", side=(0, 1, 0))

    # ---------------- grease and grime
    eq.run(b, (0.0, YB + FT, ZC - 0.12), (0, 1, 0), 0.4, 0.75, (LG,), i=2, strength=0.55)
    eq.run(b, (0.0, YA - FT, ZC - 0.3), (0, -1, 0), 0.4, 0.6, (LG,), i=4, strength=0.55)
    eq.run(b, (0.0, YG0, 0.82), (0, -1, 0), 0.3, 0.5, (Yw + "_t", Yw), i=1, strength=0.6)
    eq.puddle(b, (0.1, 0.05, 0.03), 0.7, ("deck",), strength=0.7)

    return b.lo + b.hi
