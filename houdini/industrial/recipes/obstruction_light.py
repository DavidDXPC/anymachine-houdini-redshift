import math
from .. import lighting as lkit
from ..lighting import T, R, V, X, Y, Z, Matrix


def define(F):
    b = F.part("obstruction_light/main", 0.12)
    b.box("plate", (-0.075, -0.075, 0), (0.075, 0.075, 0.012), mat="grey", skip="-z")
    b.lathe("body", [(0.06, 0.012), (0.06, 0.074), (0.07, 0.074), (0.07, 0.09), (0.05, 0.09)], n=8, mat="grey")
    b.lathe("dome", [(0.05, 0.09), (0.05, 0.15), (0.037, 0.18), (0, 0.192)], n=8, mat="lit_obstruction")
    for k in range(2):
        d = V((1, 0, 0)) if k == 0 else V((0, 1, 0)); r = 0.063
        F.tube("guard", [-d * r + V((0, 0, 0.09)), -d * r + V((0, 0, 0.206)), d * r + V((0, 0, 0.206)), d * r + V((0, 0, 0.09))], 0.004, n=3, mat="stainless", bend=0.05, seg=2)
    F.gland((0.0554, 0, 0.045), X, r=0.014, L=0.03)
    F.tube("cable", [(0.083, 0, 0.045), (0.11, 0, 0.045), (0.11, 0, 0)], 0.0065, n=4, mat="black", bend=0.022, seg=1)
    # bake only
    for sx in (-1, 1):
        for sy in (-1, 1): F.bolt((sx * 0.06, sy * 0.06, 0.012), Z, r=0.008, h=0.007)
    for k in range(4):
        a = math.radians(k * 90); c, s = math.cos(a), math.sin(a)
        b.cyl("d_lug", (c * 0.063, s * 0.063, 0.072), (c * 0.063, s * 0.063, 0.096), 0.01, n=8, mat="grey", detail=True)
        F.bolt((c * 0.063, s * 0.063, 0.096), Z, r=0.0055, h=0.004)
    for k in range(8): b.torus("d_fresnel", (0, 0, 0.097 + k * 0.0075), 0.05, 0.003, n=8, m=4, mat="lit_obstruction", detail=True)
    for z, r in ((0.158, 0.0465), (0.166, 0.043), (0.174, 0.0396)): b.torus("d_fresnel", (0, 0, z), r, 0.003, n=8, m=4, mat="lit_obstruction", detail=True)
    b.cyl("d_boss", (0, 0, 0.2), (0, 0, 0.214), 0.011, n=8, mat="stainless", detail=True)
    F.plate((0, -0.0554, 0.043), (0, -1, 0), Z, w=0.05, h=0.029, mats=("grey",), img="decal_plate_c.png")
    F.obj("obstruction_light", "obstruction_light", [("obstruction_light/main", None)], mount="pole top", origin="bottom centre of the base plate",
          light_at=[0, 0, 0.14], light_dir=None,
          suggested=dict(kelvin=None, rgb=[1.0, 0.03, 0.015], power=0.6, lumens=400, spot_deg=None, range_m=12, note="steady red; seen from far, lights little"),
          cable_ends=[dict(at=[0.11, 0, 0], dir=[0, 0, -1])])
