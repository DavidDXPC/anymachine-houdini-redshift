import math
from .. import equipment as eq
from ..equipment import pw, V, T, at, frame, Matrix
from ..geometry import Mesh

def build():
    b = eq.new("pipe_bolster")
    HX, HY, H = 3.0, 0.7, 1.2
    Yc = "yellow"
    PW = 0.12                       # post section
    ZB = 0.18                       # base top
    XP = 2.62                       # post centre
    RP = 0.11; PITCH = 0.228        # pipe radius, pitch across
    ZL = [ZB + 0.04 + RP + i * (2 * RP + 0.045) for i in range(3)]      # layer centres
    YS = [(i - 2) * PITCH for i in range(5)]
    XE = HX - 0.012                 # pipe body end (the protector stands 12 mm proud)
    N = 10

    # ---------------- base frame
    for sy in (-1, 1):
        y0, y1 = sorted((sy * HY, sy * (HY - 0.14)))
        b.box("beam", (-HX + 0.1, y0, 0.0), (HX - 0.1, y1, ZB), mat=Yc, bev=0.006, bev_axes="x", skip="-z,-x,+x")
        for x in (-0.75, 0.75):      # fork pockets (baked dark, with a rim)
            with at(b, frame((x, sy * HY, 0.085), (0, sy, 0), (1, 0, 0))):
                b.box("d_pocket", (-0.17, -0.045, -0.002), (0.17, 0.045, 0.0008), mat="dark", detail=True)
                for q in ((-0.19, -0.065, -0.17, 0.065), (0.17, -0.065, 0.19, 0.065), (-0.19, 0.045, 0.19, 0.065), (-0.19, -0.065, 0.19, -0.045)):
                    b.box("d_rim", (q[0], q[1], 0), (q[2], q[3], 0.005), mat=Yc, detail=True)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * HX, sx * (HX - 0.16)))
        b.box("end_beam", (x0, -HY, 0.0), (x1, HY, ZB), mat=Yc, bev=0.006, skip="-z")
        b.box("bolster", (sx * XP - 0.08, -HY + 0.14, ZB - 0.06), (sx * XP + 0.08, HY - 0.14, ZB + 0.04), mat=Yc, skip="-y,+y,-z")
    for x in (-1.5, 0.0, 1.5):
        b.box("cross", (x - 0.06, -HY + 0.14, 0.03), (x + 0.06, HY - 0.14, ZB - 0.02), mat=Yc, skip="-y,+y,-z")
    b.box("under", (-HX + 0.16, -HY + 0.14, 0.02), (HX - 0.16, HY - 0.14, 0.03), mat="void", skip="-x,+x,-y,+y,-z")

    # ---------------- bolster posts with gussets and lifting eyes
    ZPT = 1.06
    for sx in (-1, 1):
        for sy in (-1, 1):
            y0, y1 = sorted((sy * HY, sy * (HY - PW))); xc = sx * XP
            b.box("post", (xc - PW / 2, y0, ZB), (xc + PW / 2, y1, ZPT), mat=Yc, bev=0.006, bev_axes="z", skip="-z")
            pw.lug(b, "eye", (xc, sy * (HY - PW / 2), ZPT), (1, 0, 0), 0.055, H - ZPT, 0.04, 0.026, 0.08, 0.025, mat=Yc + "_t")
            for sg in (-1, 1):       # gusset each way along the beam
                b.prism("gusset", (xc + sg * PW / 2, sy * (HY - PW / 2), ZB), (sg, 0, 0), (0, 0, 1), [(0, 0), (0.26, 0), (0, 0.3)], -0.008, 0.008, mat=Yc + "_t", skip_side=(0, 2))
            for z in (0.34, 0.5, 0.66, 0.82):
                b.bolt((xc, sy * HY, z), (0, sy, 0), r=0.014, mat="steel")
            b.weld((xc - PW / 2, sy * HY, ZB + 0.002), (xc + PW / 2, sy * HY, ZB + 0.002), mat=Yc)
        for sy in (-1, 1):           # pad eye plate on the base corner
            b.box("d_pad", (sx * HX - (0.14 if sx > 0 else 0), sy * HY - (0.14 if sy > 0 else 0), ZB - 0.001), (sx * HX + (0.14 if sx < 0 else 0), sy * HY + (0.14 if sy < 0 else 0), ZB + 0.004), mat=Yc, detail=True)
            b.bolt((sx * (HX - 0.07), sy * (HY - 0.07), ZB + 0.004), (0, 0, 1), r=0.016, mat="steel")

    # ---------------- pipes: bodies where they can be seen (top layer, outer two of the others), protectors on every end
    CAPS = ("capgreen", "capred", "capblue")
    for li, z in enumerate(ZL):
        for yi, y in enumerate(YS):
            seen = li == 2 or yi in (0, 4)
            with at(b, frame((0, y, z), (1, 0, 0), (0, 0, 1)) @ eq.RZ(36 * ((li * 5 + yi) % 3) / 3)):
                if seen:
                    b.lathe("pipe", [(RP, -XE + 0.1), (RP, XE - 0.1)], n=N, mat="pipesteel", phase=0.0)
                    for k in range(3):
                        xs = -2.0 + 2.0 * k + 0.3 * ((yi + li) % 3 - 1)
                        b.lathe("d_band", [(RP + 0.0006, xs - 0.06), (RP + 0.0006, xs + 0.06)], n=N * 2, mat="pipesteel", detail=True, phase=0.0)
                for sg in (-1, 1):
                    prof = [(RP + 0.001, XE - 0.105), (RP + 0.009, XE - 0.1), (RP + 0.009, XE - 0.012), (RP - 0.004, HX), (RP - 0.03, HX), (RP - 0.045, HX - 0.02), (0.0, HX - 0.02)]
                    if sg < 0: prof = [(r, -x) for r, x in prof][::-1]
                    b.lathe("protector", prof, n=N, mat=CAPS[li], phase=0.0)
                    for k in range(4):      # moulded ribs on the protector (bake only)
                        xr = sg * (XE - 0.09 + 0.02 * k)
                        b.lathe("d_prib", [(RP + 0.0095, xr - 0.004), (RP + 0.012, xr), (RP + 0.0095, xr + 0.004)], n=N * 2, mat=CAPS[li], detail=True, phase=0.0)

    # ---------------- timber spacers between the layers and under the bottom layer
    for x in (-1.7, 0.0, 1.7):
        for li in range(3):
            z1 = ZL[li] - RP; z0 = z1 - 0.045 if li else ZB
            b.box("spacer", (x - 0.06, -HY + PW + 0.005, z0), (x + 0.06, HY - PW - 0.005, z1), mat="wood", skip="-z,+z" if li else "-z,+z")

    # ---------------- straps: up both sides and across the top, a ratchet buckle on the front
    YO = 2 * PITCH + RP; ZTOP = ZL[2] + RP
    for x in (-2.1, -0.85, 0.85, 2.1):
        t = 0.004; w = 0.025
        b.box("strap_top", (x - w, -YO - t, ZTOP), (x + w, YO + t, ZTOP + t), mat="steel_t", skip="-z")
        for sy in (-1, 1):
            y0, y1 = sorted((sy * YO, sy * (YO + t)))
            b.box("strap_side", (x - w, y0, ZB), (x + w, y1, ZTOP), mat="steel_t", skip="-z,+z,%sy" % ("-" if sy > 0 else "+"))
        b.box("buckle", (x - 0.04, -YO - 0.03, ZB + 0.1), (x + 0.04, -YO - t, ZB + 0.24), mat="steel", bev=0.004, skip="+y")
        b.cyl("buckle_pin", (x - 0.05, -YO - 0.018, ZB + 0.2), (x + 0.05, -YO - 0.018, ZB + 0.2), 0.012, n=6, mat="steel")
        b.box("anchor", (x - 0.05, -HY + 0.14 - 0.01, ZB - 0.07), (x + 0.05, -HY + 0.14, ZB), mat="steel", skip="+y,-z")

    # ---------------- grime
    eq.run(b, (-1.2, -HY, ZB), (0, -1, 0), 0.9, 0.2, (Yc,), i=1, strength=0.55)
    eq.run(b, (1.6, HY, ZB), (0, 1, 0), 0.9, 0.2, (Yc,), i=3, strength=0.55)
    eq.run(b, (0.3, -YO, ZL[2]), (0, -1, 0), 1.2, 0.8, ("pipesteel",), i=2, strength=0.4)
    eq.run(b, (-1.0, YO, ZL[2]), (0, 1, 0), 1.2, 0.8, ("pipesteel",), i=4, strength=0.4)
    eq.puddle(b, (1.2, 0.0, ZTOP), 0.9, ("pipesteel",), strength=0.4)

    return b.lo + b.hi
