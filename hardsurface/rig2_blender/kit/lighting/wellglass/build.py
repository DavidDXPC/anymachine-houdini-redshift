# wellglass: caged bulkhead "well glass" lamp.  Wall piece: back on the wall plane (y = 0), stands out to -Y,
# origin bottom centre of the back (the lowest point is the lower conduit elbow).  0.18 x 0.18 x 0.30 m.
# Conduit leaves the back box top and bottom and elbows into the wall.  Lit material: wellglass__lit (the glass).
#   blender -b --factory-startup -t 4 --python build.py        (geometry check only; the bake is ../build.py)
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "_shared"))
import lkit
from lkit import T, R, V, X, Y, Z
AY = -0.100; GR, CR = 0.054, 0.062; ZO = 0.1505      # lamp axis off the wall, glass and cage radius, origin shift


def define(F):
    b = F.part("wellglass/main", 0.11)
    b.box("backbox", (-0.09, -0.04, -0.09), (0.09, 0, 0.09), mat="grey", skip="+y")
    b.box("neck", (-0.045, AY + 0.06, 0.0), (0.045, -0.04, 0.086), mat="grey", skip="+y,-y")
    b.lathe("body", [(0.076, 0.012), (0.076, 0.058), (0.05, 0.084), (0, 0.09)], n=8, mat="grey", at=(0, AY, 0))
    b.lathe("flange", [(GR + 0.004, -0.004), (0.084, -0.004), (0.084, 0.012), (0.076, 0.012)], n=8, mat="grey", at=(0, AY, 0))
    b.lathe("glass", [(0, -0.128), (0.032, -0.12), (0.05, -0.096), (GR, -0.004)], n=8, mat="lit_wellglass", at=(0, AY, 0))
    for k in range(4):
        a = math.radians(k * 90 + 22.5); c, s = math.cos(a), math.sin(a)
        F.tube("cage_v", [(c * CR, AY + s * CR, -0.004), (c * CR, AY + s * CR, -0.098), (c * 0.006, AY + s * 0.006, -0.139)], 0.0032, n=3, mat="galv", bend=0.03, seg=1)
    for z in (-0.04, -0.088): b.torus("cage_h", (0, AY, z), CR, 0.003, n=8, m=3, mat="galv")
    for sz in (-1, 1):                 # conduit entry top and bottom: gland, conduit, elbow into the wall
        F.gland((0, -0.02, sz * 0.09), (0, 0, sz), r=0.014, L=0.025)
        F.tube("conduit", [(0, -0.02, sz * 0.113), (0, -0.02, sz * 0.14), (0, 0, sz * 0.14)], 0.0105, n=4, mat="galv", bend=0.011, seg=1)
    # bake only
    for sx in (-1, 1):
        for sz in (-1, 1): F.bolt((sx * 0.074, -0.04, sz * 0.074), (0, -1, 0), r=0.007)
    for k in range(4):
        a = math.radians(k * 90 + 45); c, s = math.cos(a), math.sin(a)
        b.cyl("d_lug", (c * 0.079, AY + s * 0.079, -0.006), (c * 0.079, AY + s * 0.079, 0.016), 0.011, n=8, mat="grey", detail=True)
        F.bolt((c * 0.079, AY + s * 0.079, 0.016), Z, r=0.006); F.bolt((c * 0.079, AY + s * 0.079, -0.006), (0, 0, -1), r=0.006)
    F.facet_ribs((0, AY, 0), (0.05, -0.094), (GR, -0.008), per=4, rr=0.0026, mat="lit_wellglass")     # prismatic ribs on the glass
    b.torus("d_ring", (0, AY, -0.139), 0.009, 0.0035, n=8, m=4, mat="galv", detail=True)
    F.plate((0, AY - 0.0702, 0.036), (0, -1, 0), Z, w=0.046, h=0.027, mats=("grey",), img="decal_plate_a.png")
    F.obj("wellglass", "wellglass", [("wellglass/main", T((0, 0, ZO)))], mount="wall", origin="wall plane, bottom centre",
          light_at=[0, AY, round(ZO - 0.06, 4)], light_dir=None,
          suggested=dict(kelvin=2700, rgb=[1.0, 0.74, 0.46], power=1.0, lumens=800, spot_deg=None, range_m=7),
          cable_ends=[dict(at=[0, 0, round(ZO + 0.14, 4)], dir=[0, 1, 0], note="conduit elbows into the wall above"),
                      dict(at=[0, 0, round(ZO - 0.14, 4)], dir=[0, 1, 0], note="and below")])


if __name__ == "__main__": lkit.run([define], only=["wellglass"])
