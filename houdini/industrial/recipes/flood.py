import math
from .. import lighting as lkit
from ..lighting import T, R, V, X, Y, Z, Matrix

PZ, TILT = 0.215, 25
HM = T((0, 0, PZ)) @ R(TILT, "X")          # head frame in the unit: pivot at the head centre
LIGHT = HM @ V((0, -0.05, 0)); AIM = HM.to_3x3() @ V((0, -1, 0))
POLE = 4.0; PT = 0.016 + POLE

def r4(values):
    return [round(x,4) for x in values]


def define(F):
    b = F.part("flood/unit", 0.2)
    b.box("strap", (-0.18, -0.03, 0), (0.18, 0.03, 0.008), mat="galv", skip="-z")
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 0.18, sx * 0.172))
        b.box("cheek", (x0, -0.03, 0.008), (x1, 0.03, 0.25), mat="galv", skip="-z")
        F.bolt((sx * 0.11, 0, 0.008), Z, r=0.008, mat="galv")
    F.xf(HM)
    q = [(-0.15, -0.15), (0.15, -0.15), (0.15, 0.15), (-0.15, 0.15)]; qi = [(-0.118, -0.118), (0.118, -0.118), (0.118, 0.118), (-0.118, 0.118)]
    b.ring_plate("bezel", (0, -0.07, 0), X, Z, q, qi, -0.025, 0, mat="dgrey")
    b.strip("lens", (-0.118, -0.049, -0.118), (0.236, 0, 0), Z, (0, -1, 0), [(0, 0), (0.236, 0)], mat="lit_flood")
    b.box("body", (-0.135, -0.045, -0.135), (0.135, 0.045, 0.135), mat="dgrey", skip="-y")
    for k in range(8):                  # fins over the back and the top
        x = -0.105 + k * 0.03
        b.prism("fin", (x, 0, 0), Y, Z, [(-0.035, 0.135), (0.045, 0.135), (0.045, -0.125), (0.075, -0.125), (0.075, 0.158), (-0.035, 0.158)], -0.004, 0.004, mat="dgrey", skip_side=(0, 1))
    for sx in (-1, 1):
        b.cyl("pivot", (sx * 0.135, 0, 0), (sx * 0.192, 0, 0), 0.017, n=6, mat="stainless", caps=(False, True))
        b.cyl("d_boss", (sx * 0.134, 0, 0), (sx * 0.15, 0, 0), 0.034, n=12, mat="dgrey", detail=True)
        for z in (-0.1, -0.07, 0.07, 0.1):   # side fins, bake only
            b.box("d_sfin", (sx * 0.134 - 0.006, -0.03, z - 0.004), (sx * 0.134 + 0.006, 0.04, z + 0.004), mat="dgrey", detail=True)
    for sx in (-1, 0, 1):
        for sz in (-1, 0, 1):
            if sx or sz: F.bolt((sx * 0.134, -0.07, sz * 0.134), (0, -1, 0), r=0.007)
    F.gland((0, 0.045, -0.085), (0, 1, 0), r=0.0105, L=0.03)
    F.decal("decal_flood.png", (0, -0.049, 0), (0, -1, 0), Z, 0.236, 0.236, kind="label", mats=("lit_flood",), depth=0.01)
    F.plate((0.06, 0, -0.135), (0, 0, -1), (0, -1, 0), w=0.06, h=0.035, mats=("dgrey",), img="decal_plate_b.png")
    g = HM @ V((0, 0.073, -0.085)); u = HM.to_3x3() @ V((0, 1, 0))
    F.xf()
    F.tube("cable", [g, g + u * 0.035, (0, 0.05, 0.05), (0, 0.05, 0)], 0.0065, n=4, mat="black", bend=0.03, seg=1)
    b.cyl("d_grommet", (0, 0.05, 0), (0, 0.05, 0.008), 0.012, n=8, mat="black", detail=True)

    b = F.part("flood/pole_1m", 0.07)
    b.cyl("pole", (0, 0, 0), (0, 0, 1), 0.057, n=8, mat="pole", caps=(False, False))

    b = F.part("flood/pole_foot", 0.22)             # base plate, gussets, junction box at 1 m, conduit into the deck
    b.box("base", (-0.16, -0.16, 0), (0.16, 0.16, 0.016), mat="galv", skip="-z")
    for k in range(4):
        a = math.radians(k * 90 + 45); c, s = math.cos(a), math.sin(a)
        b.prism("gusset", (0, 0, 0.016), (c, s, 0), Z, [(0.05, 0), (0.15, 0), (0.05, 0.13)], -0.004, 0.004, mat="galv", skip_side=(0, 2))
    for sx in (-1, 1):
        for sy in (-1, 1): F.bolt((sx * 0.125, sy * 0.125, 0.016), Z, r=0.013, h=0.012, mat="galv")
    b.box("jbox", (-0.065, -0.13, 0.92), (0.065, -0.05, 1.08), mat="grey", skip="+y")
    F.gland((0, -0.09, 0.92), (0, 0, -1), r=0.014, L=0.028)
    F.tube("conduit", [(0, -0.09, 0.895), (0, -0.09, 0.28), (0, -0.21, 0.14), (0, -0.21, 0)], 0.0125, n=5, mat="galv", bend=0.07, seg=1)
    for sx in (-1, 1):
        for z in (0.935, 1.065): F.bolt((sx * 0.05, -0.13, z), (0, -1, 0), r=0.005)
    b.cyl("d_weld", (0, 0, 0.016), (0, 0, 0.024), 0.064, n=16, mat="galv", detail=True)

    b = F.part("flood/pole_top", 0.22)              # cap plate for one unit
    b.box("cap", (-0.2, -0.07, 0), (0.2, 0.07, 0.012), mat="galv")
    b = F.part("flood/crossarm", 0.64)
    b.box("arm", (-0.62, -0.06, 0), (0.62, 0.06, 0.06), mat="galv")
    b.box("d_saddle", (-0.075, -0.064, -0.002), (0.075, 0.064, 0.064), mat="galv", detail=True)
    for sx in (-1, 1): F.bolt((sx * 0.05, -0.064, 0.03), (0, -1, 0), r=0.01, mat="galv")

    b = F.part("flood/rail_clamp", 0.22)            # origin on top of the top rail (rail along X)
    b.box("clamp", (-0.05, -0.04, -0.066), (0.05, 0.04, 0.012), mat="galv", skip="-z")
    b.cyl("riser", (0, 0, 0.012), (0, 0, 0.2), 0.021, n=6, mat="pole", caps=(False, False))
    b.box("top", (-0.2, -0.07, 0.2), (0.2, 0.07, 0.212), mat="galv")
    b.cyl("tail", (0, -0.05, 0.2), (0, -0.05, -0.03), 0.0065, n=4, mat="black", caps=(False, True))
    for sx in (-1, 1):
        for sy in (-1, 1): F.bolt((sx * 0.033, sy * 0.027, 0.012), Z, r=0.007, mat="galv")

    sug = dict(kelvin=2100, rgb=[1.0, 0.52, 0.14], power=8.0, lumens=24000, spot_deg=110, range_m=30)
    F.obj("flood", "flood_head", [("flood/unit", None)], mount="deck", origin="centre of the stirrup base (any flat surface: deck, beam top, bracket)",
          light_at=r4(LIGHT), light_dir=r4(AIM), suggested=sug, cable_ends=[dict(at=[0, 0.05, 0], dir=[0, 0, -1])])
    pole = [("flood/pole_foot", None)] + [("flood/pole_1m", T((0, 0, 0.016 + k))) for k in range(4)]
    cend = [dict(at=[0, -0.21, 0], dir=[0, 0, -1], note="conduit from the junction box enters the deck")]
    U1 = T((0, 0, PT + 0.012))
    F.obj("flood", "flood_pole", pole + [("flood/pole_top", T((0, 0, PT))), ("flood/unit", U1)], mount="deck", origin="bottom centre of the base plate",
          light_at=r4(U1 @ LIGHT), light_dir=r4(AIM), suggested=sug, cable_ends=cend)
    us = [T((sx * 0.42, 0, PT + 0.06)) @ R(sx * -20, "Z") for sx in (-1, 1)]
    F.obj("flood", "flood_pole_pair", pole + [("flood/crossarm", T((0, 0, PT)))] + [("flood/unit", u) for u in us], mount="deck", origin="bottom centre of the base plate",
          light_at=r4(us[0] @ LIGHT), light_dir=r4(us[0].to_3x3() @ AIM), suggested=sug, cable_ends=cend,
          lights=[dict(at=r4(u @ LIGHT), dir=r4(u.to_3x3() @ AIM)) for u in us])
    UR = T((0, 0, 0.212)) @ R(180, "Z")
    F.obj("flood", "flood_rail", [("flood/rail_clamp", None), ("flood/unit", UR)], mount="rail",
          origin="top of the handrail top rail, over a post; rail along X, lens to +Y (deck side)",
          light_at=r4(UR @ LIGHT), light_dir=r4(UR.to_3x3() @ AIM), suggested=dict(sug, power=5.0, lumens=15000),
          cable_ends=[dict(at=[0, -0.05, -0.03], dir=[0, 0, -1], note="tail ends on the clamp / handrail post")])
