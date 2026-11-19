import math
from .. import lighting as lkit
from ..lighting import T, R, V, X, Y, Z, Matrix

FY = -0.10                     # front of the box

def define(F):
    b = F.part("escape_route/sign", 0.32)
    for sx in (-1, 1): b.box("channel", (sx * 0.2 - 0.02, -0.02, 0.0), (sx * 0.2 + 0.02, 0, 0.3), mat="galv", skip="+y")
    b.box("box", (-0.3, FY, 0), (0.3, -0.02, 0.3), mat="grey", skip="-y,+y")
    q = [(-0.3, -0.15), (0.3, -0.15), (0.3, 0.15), (-0.3, 0.15)]; qi = [(-0.25, -0.105), (0.25, -0.105), (0.25, 0.105), (-0.25, 0.105)]
    b.ring_plate("frame", (0, FY, 0.15), X, Z, q, qi, -0.008, 0, mat="grey", back=False, skip_outer=(0, 1, 2, 3))
    b.strip("face", (-0.25, FY + 0.008, 0.045), (0.5, 0, 0), Z, (0, -1, 0), [(0, 0), (0.21, 0)], mat="lit_escape_sign")
    for z in (0.085, 0.15, 0.215):
        F.tube("guard_h", [(-0.275, FY, z), (-0.275, FY - 0.03, z), (0.275, FY - 0.03, z), (0.275, FY, z)], 0.0045, n=3, mat="stainless", bend=0.018, seg=1)
    for sx in (-1, 1):
        b.cyl("guard_v", (sx * 0.14, FY - 0.0265, 0.06), (sx * 0.14, FY - 0.0265, 0.24), 0.0045, n=3, mat="stainless", caps=(True, True))
    F.gland((-0.15, -0.06, 0.3), Z, r=0.014, L=0.03)
    F.tube("cable", [(-0.15, -0.06, 0.328), (-0.15, -0.06, 0.37), (-0.15, 0, 0.37)], 0.007, n=4, mat="black", bend=0.035, seg=2)
    # bake only
    for k in range(7):
        for z in (0.021, 0.279): F.bolt((-0.27 + k * 0.09, FY, z), (0, -1, 0), r=0.006)
    for z in (0.085, 0.15, 0.215):
        for sx in (-1, 1): F.bolt((sx * 0.275, FY, z), (0, -1, 0), r=0.008, h=0.003, hexa=False)
    for sx in (-1, 1):
        for z in (0.04, 0.26): F.bolt((sx * 0.2, -0.02, z), (0, -1, 0), r=0.006, mat="galv")
    F.decal("decal_exit.png", (0, FY + 0.008, 0.15), (0, -1, 0), Z, 0.44, 0.22, kind="label", mats=("lit_escape_sign",), depth=0.01)
    F.plate((0.12, -0.06, 0.3), Z, Y, w=0.06, h=0.034, mats=("grey",), img="decal_plate_c.png")

    b = F.part("escape_route/strip", 0.52)
    for sy in (-1, 1):
        b.strip("edge", (-0.5, 0, 0), (1.0, 0, 0), (0, sy, 0), Z, [(0.025, 0), (0.021, 0.008), (0.016, 0.008)], mat="stainless")
    b.strip("glow", (-0.5, -0.016, 0.008), (1.0, 0, 0), Y, Z, [(0, 0), (0.032, 0)], mat="lit_escape_strip")
    b.prism("ends", (-0.5, 0, 0), Y, Z, [(-0.025, 0), (0.025, 0), (0.021, 0.008), (-0.021, 0.008)], 0, 1.0, mat="stainless", skip_side=(0, 1, 2, 3))
    for k in range(5): F.bolt((-0.44 + k * 0.22, 0, 0.008), Z, r=0.0045, h=0.0012, hexa=False)

    F.obj("escape_route", "escape_sign", [("escape_route/sign", None)], mount="wall", origin="wall plane, bottom centre of the box; chevrons point to +X",
          light_at=[0, FY - 0.03, 0.15], light_dir=[0, -1, 0], suggested=dict(kelvin=None, rgb=[0.10, 1.0, 0.40], power=0.3, lumens=200, spot_deg=140, range_m=4, shape="panel 0.5 x 0.21"),
          cable_ends=[dict(at=[-0.15, 0, 0.37], dir=[0, 1, 0], note="cable turns into the wall above the box")])
    F.obj("escape_route", "escape_strip", [("escape_route/strip", None)], mount="deck", origin="bottom centre, long side X",
          light_at=[0, 0, 0.02], light_dir=[0, 0, 1], suggested=dict(kelvin=None, rgb=[0.50, 1.0, 0.40], power=0.02, lumens=5, spot_deg=None, range_m=0.5, note="afterglow: emission only, no light source needed"),
          cable_ends=[])
