import math
from .. import lighting as lkit
from ..lighting import T, R, V, X, Y, Z, Matrix


def define(F):
    b = F.part("helideck_lights/perimeter", 0.11)
    b.lathe("disc", [(0.1, 0), (0.1, 0.008), (0.08, 0.013), (0.06, 0.03), (0.042, 0.032)], n=12, mat="stainless")
    b.lathe("lens", [(0.042, 0.032), (0.031, 0.04), (0, 0.043)], n=12, mat="lit_heli_green")
    for k in range(8):
        a = math.radians(k * 45 + 22.5); F.bolt((math.cos(a) * 0.09, math.sin(a) * 0.09, 0.0105), (0, 0.2, 1), r=0.006, h=0.003)
    for k in range(6):
        a = math.radians(k * 60); F.bolt((math.cos(a) * 0.051, math.sin(a) * 0.051, 0.031), Z, r=0.004, h=0.002, hexa=False)
    for r, z in ((0.036, 0.0364), (0.027, 0.0404), (0.018, 0.0413), (0.009, 0.0421)): b.torus("d_ring", (0, 0, z), r, 0.0024, n=12, m=4, mat="lit_heli_green", detail=True)

    b = F.part("helideck_lights/circle", 0.27)
    L = 0.25
    for sy in (-1, 1):
        b.strip("edge", (-L, 0, 0), (2 * L, 0, 0), (0, sy, 0), Z, [(0.04, 0), (0.034, 0.01), (0.016, 0.012)], mat="stainless")
    for sx in (-1, 1):
        x0 = min(sx * L, sx * 0.2)
        b.strip("land", (x0, -0.016, 0.012), (0.05, 0, 0), Y, Z, [(0, 0), (0.032, 0)], mat="stainless")
    b.strip("leds", (-0.2, -0.016, 0.012), (0.4, 0, 0), Y, Z, [(0, 0), (0.032, 0)], mat="lit_heli_yellow")
    b.prism("ends", (-L, 0, 0), Y, Z, [(-0.04, 0), (0.04, 0), (0.034, 0.01), (0.016, 0.012), (-0.016, 0.012), (-0.034, 0.01)], 0, 2 * L, mat="stainless", skip_side=(0, 1, 2, 3, 4, 5))
    b.box("d_window", (-0.198, -0.0145, 0.0115), (0.198, 0.0145, 0.0128), mat="dgrey", detail=True)
    for k in range(8):
        x = -0.1575 + k * 0.045
        b.lathe("d_led", [(0.011, 0.0125), (0.009, 0.0155), (0, 0.017)], n=10, mat="lit_heli_yellow", at=(x, 0, 0), detail=True)
    for sx in (-1, 1): F.bolt((sx * 0.226, 0, 0.012), Z, r=0.006, h=0.002, hexa=False)

    b = F.part("helideck_lights/edge_flood", 0.12)
    b.box("foot", (-0.07, -0.06, 0), (0.07, 0.06, 0.01), mat="grey", skip="-z")
    b.box("pedestal", (-0.03, -0.03, 0.01), (0.03, 0.03, 0.11), mat="grey", skip="-z,+z")
    b.box("head", (-0.08, -0.05, 0.11), (0.08, 0.06, 0.24), mat="grey", skip="-y")
    q = [(-0.08, -0.065), (0.08, -0.065), (0.08, 0.065), (-0.08, 0.065)]; qi = [(-0.064, -0.049), (0.064, -0.049), (0.064, 0.049), (-0.064, 0.049)]
    b.ring_plate("bezel", (0, -0.062, 0.175), X, Z, q, qi, -0.012, 0, mat="grey", back=False)
    b.strip("lens", (-0.064, -0.051, 0.126), (0.128, 0, 0), Z, (0, -1, 0), [(0, 0), (0.098, 0)], mat="lit_heli_flood")
    b.box("hood", (-0.084, -0.15, 0.24), (0.084, 0.06, 0.246), mat="grey")
    for sx in (-1, 1):
        b.prism("cheek", (sx * 0.082, 0, 0), Y, Z, [(-0.062, 0.24), (-0.15, 0.24), (-0.062, 0.13)], -0.002, 0.002, mat="grey", skip_side=(2,))
        b.cyl("d_pivot", (sx * 0.079, 0.005, 0.15), (sx * 0.09, 0.005, 0.15), 0.013, n=10, mat="stainless", detail=True)
        for sy in (-1, 1): F.bolt((sx * 0.052, sy * 0.042, 0.01), Z, r=0.006, h=0.004)
    for k in range(9): b.box("d_flute", (-0.062 + k * 0.014, -0.0535, 0.128), (-0.062 + k * 0.014 + 0.009, -0.05, 0.222), mat="lit_heli_flood", detail=True)
    F.gland((0.08, 0.03, 0.135), X, r=0.012, L=0.026)
    F.tube("cable", [(0.104, 0.03, 0.135), (0.13, 0.03, 0.135), (0.13, 0.03, 0)], 0.0065, n=4, mat="black", bend=0.025, seg=1)
    F.plate((0, 0.06, 0.175), (0, 1, 0), Z, w=0.05, h=0.029, mats=("grey",), img="decal_plate_c.png")

    below = [dict(at=[0, 0, 0], dir=[0, 0, -1], note="fed from below through the deck; no surface cable")]
    F.obj("helideck_lights", "helideck_perimeter", [("helideck_lights/perimeter", None)], mount="deck", origin="bottom centre",
          light_at=[0, 0, 0.06], light_dir=None, suggested=dict(kelvin=None, rgb=[0.04, 1.0, 0.32], power=0.25, lumens=150, spot_deg=None, range_m=4, note="upper hemisphere only"),
          cable_ends=below)
    F.obj("helideck_lights", "helideck_circle", [("helideck_lights/circle", None)], mount="deck", origin="bottom centre, long side X",
          light_at=[0, 0, 0.04], light_dir=[0, 0, 1], suggested=dict(kelvin=None, rgb=[1.0, 0.78, 0.04], power=0.2, lumens=120, spot_deg=160, range_m=3, shape="line 0.36 m along X"),
          cable_ends=below)
    F.obj("helideck_lights", "helideck_edge_flood", [("helideck_lights/edge_flood", None)], mount="deck", origin="bottom centre of the foot, throws to -Y",
          light_at=[0, -0.07, 0.175], light_dir=[0, -0.9848, -0.1736], suggested=dict(kelvin=4000, rgb=[1.0, 0.93, 0.80], power=2.0, lumens=3000, spot_deg=100, range_m=14, note="hooded: nothing above the horizontal"),
          cable_ends=[dict(at=[0.13, 0.03, 0], dir=[0, 0, -1])])
