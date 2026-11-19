import math
from .. import lighting as lkit
from ..lighting import T, R, V, X, Y, Z, Matrix

PH = 0.25; LZ = 0.082          # pole top, lens seat above the head's foot
WY, WZ = -0.13, 0.13           # head axis and seat on the wall bracket

def define(F):
    b = F.part("beacon/head", 0.1)
    b.lathe("body", [(0.045, 0), (0.066, 0.02), (0.066, 0.066), (0.076, 0.066), (0.076, LZ), (0.052, LZ)], n=8, mat="grey")
    for k in range(4):
        a = math.radians(k * 90 + 22.5); c, s = math.cos(a), math.sin(a)
        F.tube("guard", [(c * 0.066, s * 0.066, LZ), (c * 0.066, s * 0.066, LZ + 0.09), (0, 0, LZ + 0.128)], 0.0038, n=3, mat="stainless", bend=0.04, seg=1)
    b.torus("hoop", (0, 0, LZ + 0.075), 0.066, 0.0036, n=8, m=3, mat="stainless")
    F.gland((0, 0.061, 0.043), Y, r=0.013, L=0.03)
    for k in range(4):
        a = math.radians(k * 90 + 22.5); c, s = math.cos(a), math.sin(a)
        b.cyl("d_lug", (c * 0.07, s * 0.07, 0.064), (c * 0.07, s * 0.07, LZ + 0.006), 0.009, n=8, mat="grey", detail=True)
        F.bolt((c * 0.07, s * 0.07, LZ + 0.006), Z, r=0.005, h=0.004)
    b.cyl("d_boss", (0, 0, LZ + 0.118), (0, 0, LZ + 0.134), 0.01, n=8, mat="stainless", detail=True)
    F.plate((0, -0.061, 0.043), (0, -1, 0), Z, w=0.046, h=0.027, mats=("grey",), img="decal_plate_c.png")

    b = F.part("beacon/lens", 0.07)
    b.lathe("lens", [(0.05, 0), (0.05, 0.07), (0.036, 0.098), (0, 0.108)], n=8, mat="lit_beacon")
    F.facet_ribs((0, 0, 0), (0.05, 0.004), (0.05, 0.068), per=3, rr=0.003, mat="lit_beacon")
    b.torus("d_band", (0, 0, 0.072), 0.05, 0.003, n=8, m=4, mat="lit_beacon", detail=True)

    b = F.part("beacon/pole", 0.12)
    b.box("base", (-0.07, -0.07, 0), (0.07, 0.07, 0.01), mat="galv", skip="-z")
    b.cyl("pole", (0, 0, 0.01), (0, 0, PH), 0.03, n=8, mat="pole", caps=(False, False))
    F.tube("cable", [(0, 0.089, PH + 0.043), (0, 0.118, PH + 0.043), (0, 0.118, 0)], 0.0065, n=4, mat="black", bend=0.03, seg=2)
    for sx in (-1, 1):
        for sy in (-1, 1): F.bolt((sx * 0.052, sy * 0.052, 0.01), Z, r=0.007, h=0.006, mat="galv")
    b.cyl("d_weld", (0, 0, 0.01), (0, 0, 0.016), 0.035, n=12, mat="galv", detail=True)

    b = F.part("beacon/wall_bracket", 0.1)
    b.box("wallplate", (-0.06, -0.01, 0), (0.06, 0, 0.16), mat="galv", skip="+y")
    b.box("shelf", (-0.05, WY - 0.055, WZ - 0.01), (0.05, -0.01, WZ), mat="galv", skip="+y")
    b.prism("gusset", (0, 0, 0), Y, Z, [(-0.01, 0.015), (-0.01, WZ - 0.01), (WY - 0.03, WZ - 0.01)], -0.004, 0.004, mat="galv", skip_side=(0, 1))
    b.cyl("tail", (0, WY + 0.089, WZ + 0.043), (0, 0, WZ + 0.043), 0.0065, n=4, mat="black", caps=(False, False))
    for sx in (-1, 1):
        for z in (0.025, 0.145): F.bolt((sx * 0.042, -0.01, z), (0, -1, 0), r=0.007, mat="galv")

    sug = dict(kelvin=None, rgb=[1.0, 0.46, 0.02], power=1.2, lumens=900, spot_deg=50, range_m=14, note="rotating: sweep a 50 degree spot round Z at 2 turns a second, plus a weak all-round glow; red variant rgb [1.0, 0.05, 0.02]")
    F.obj("beacon", "beacon_pole", [("beacon/pole", None), ("beacon/head", T((0, 0, PH)))], mount="deck", origin="bottom centre of the base plate",
          lens_at=[0, 0, round(PH + LZ, 4)], light_at=[0, 0, round(PH + LZ + 0.045, 4)], light_dir=None, suggested=sug, lit_object="beacon_lens",
          cable_ends=[dict(at=[0, 0.118, 0], dir=[0, 0, -1])])
    F.obj("beacon", "beacon_wall", [("beacon/wall_bracket", None), ("beacon/head", T((0, WY, WZ)))], mount="wall", origin="wall plane, bottom centre of the wall plate",
          lens_at=[0, WY, round(WZ + LZ, 4)], light_at=[0, WY, round(WZ + LZ + 0.045, 4)], light_dir=None, suggested=sug, lit_object="beacon_lens",
          cable_ends=[dict(at=[0, 0, round(WZ + 0.043, 4)], dir=[0, 1, 0], note="cable goes straight into the wall")])
    F.obj("beacon", "beacon_lens", [("beacon/lens", None)], mount="on beacon_pole / beacon_wall at lens_at", origin="bottom centre of the dome",
          light_at=[0, 0, 0.045], light_dir=None, suggested=sug, cable_ends=[])
