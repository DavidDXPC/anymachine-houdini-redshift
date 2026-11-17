# tube_light: sealed 1.3 m twin-tube fitting.  Lit material: tube_light__lit (the diffuser; tubes are baked into it).
#   tube_light_ceiling  origin on the ceiling plane, centre; tubes along X, diffuser down; two hangers, cable loops
#                       from each end gland up to the ceiling.  1.51 x 0.15 x 0.17
#   tube_light_pole     on a rail post: origin on TOP of a handrail top rail (rail along X, its axis at z = -0.028);
#                       post 1.05 m, arm to +Y (the deck side of circulation/handrail), fitting under a spreader bar.
#                       The cable runs inside the post and leaves the clamp on the -Y side.
#   tube_light_broken   the ceiling fitting with its +X hanger let go: body hangs 12 degrees, cable pulled taut.
#   blender -b --factory-startup -t 4 --python build.py        (geometry check only; the bake is ../build.py)
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "_shared"))
import lkit
from lkit import T, R, V, X, Y, Z
GAP = 0.07                     # ceiling to body top
BODY = T((0, 0, -GAP))
PIV = V((-0.4, 0, -GAP)); DROP = T(PIV) @ R(12, "Y") @ T(-PIV) @ BODY


def define(F):
    b = F.part("tube_light/body", 0.68)             # body top at z = 0, tubes along X, diffuser down
    b.box("tray", (-0.6, -0.07, -0.06), (0.6, 0.07, 0), mat="grey", skip="-z,-x,+x")
    b.strip("lens", (-0.6, 0, 0), (1.2, 0, 0), Y, (0, 0, -1), [(-0.064, 0.06), (-0.046, 0.092), (0.046, 0.092), (0.064, 0.06)], mat="lit_tube_light")
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 0.6, sx * 0.65))
        b.box("endcap", (x0, -0.075, -0.1), (x1, 0.075, 0.004), mat="grey")
        F.gland((sx * 0.65, 0, -0.045), (sx, 0, 0), r=0.014, L=0.03)
        for sy in (-1, 1):
            for z in (-0.085, -0.012): F.bolt((sx * 0.65, sy * 0.058, z), (sx, 0, 0), r=0.006)
    for k in range(5):
        x = -0.48 + k * 0.24
        for sy in (-1, 1):              # stainless toggle clips over the tray / diffuser joint
            b.box("d_clip", (x - 0.012, min(sy * 0.0695, sy * 0.0745), -0.066), (x + 0.012, max(sy * 0.0695, sy * 0.0745), -0.034), mat="stainless", detail=True)
            b.cyl("d_clip_pin", (x - 0.014, sy * 0.074, -0.04), (x + 0.014, sy * 0.074, -0.04), 0.003, n=6, mat="stainless", detail=True)
    b.box("d_rim", (-0.6, -0.0715, -0.064), (0.6, 0.0715, -0.056), mat="grey", detail=True)
    F.decal("decal_tubes.png", (0, 0, -0.092), (0, 0, -1), Y, 1.2, 0.128, kind="label", mats=("lit_tube_light",), depth=0.045)
    F.plate((0.25, -0.07, -0.028), (0, -1, 0), Z, w=0.06, h=0.034, mats=("grey",), img="decal_plate_a.png")

    b = F.part("tube_light/hanger", 0.06)           # origin on the ceiling plane above the body centre line
    b.box("foot", (-0.03, -0.035, -0.006), (0.03, 0.035, 0), mat="galv", skip="+z")
    b.box("flat", (-0.02, -0.003, -GAP), (0.02, 0.003, -0.006), mat="galv", skip="+z,-z")
    b.box("strap", (-0.02, -0.074, -GAP - 0.005), (0.02, 0.074, -GAP + 0.001), mat="galv")
    for sy in (-1, 1):
        F.bolt((0, sy * 0.022, -0.006), (0, 0, -1), r=0.006, mat="galv"); F.bolt((0, sy * 0.05, -GAP - 0.005), (0, 0, -1), r=0.005, mat="galv")

    b = F.part("tube_light/cable", 0.1)             # from the +X end gland up to the ceiling; modelled at x - 0.7
    F.tube("cable", [(-0.02, 0, -GAP - 0.045), (0.05, 0, -GAP - 0.045), (0.05, 0, 0)], 0.0065, n=4, mat="black", bend=0.04, seg=2)
    b.cyl("d_grommet", (0.05, 0, -0.008), (0.05, 0, 0.0), 0.012, n=8, mat="black", detail=True)

    b = F.part("tube_light/post", 0.5)              # rail post: origin on top of the top rail (rail along X)
    b.box("clamp", (-0.045, -0.04, -0.066), (0.045, 0.04, 0.012), mat="galv", skip="-z")
    F.tube("post", [(0, 0, 0.012), (0, 0, 1.05), (0, 0.24, 1.05)], 0.021, n=6, mat="pole", bend=0.09, seg=3, caps=(False, True))
    b.box("spreader", (-0.45, 0.18, 0.989), (0.45, 0.22, 1.029), mat="galv")
    F.gland((0, -0.04, -0.03), (0, -1, 0), r=0.012, L=0.022)
    F.tube("tail", [(0, -0.062, -0.03), (0, -0.075, -0.03), (0, -0.075, -0.12), (0, -0.0375, -0.12)], 0.006, n=4, mat="black", bend=0.012, seg=1)
    for sx in (-1, 1):
        for sy in (-1, 1): F.bolt((sx * 0.03, sy * 0.027, 0.012), Z, r=0.007, mat="galv")
    b.cyl("d_collar", (0, 0, 0.011), (0, 0, 0.03), 0.027, n=10, mat="galv", detail=True)

    b = F.part("tube_light/cable_loose", 0.1)       # the broken fitting's cable: gland of the dropped end to the ceiling
    g = (T((-0.75, 0, 0)) @ DROP) @ V((0.68, 0, -0.045)); u = (DROP.to_3x3() @ V((1, 0, 0)))
    F.tube("cable", [g - u * 0.02, g + u * 0.05, (g.x + 0.02, 0, -0.12), (0.0, 0, -0.035), (0, 0, 0)], 0.0065, n=4, mat="black", bend=0.02, seg=1)

    hang = [("tube_light/hanger", T((-0.4, 0, 0))), ("tube_light/hanger", T((0.4, 0, 0)))]
    cab = [("tube_light/cable", T((0.7, 0, 0))), ("tube_light/cable", R(180, "Z") @ T((0.7, 0, 0)))]
    sug = dict(kelvin=5000, rgb=[0.80, 0.90, 1.0], power=1.6, lumens=3200, spot_deg=150, range_m=9, shape="line 1.2 m along X")
    F.obj("tube_light", "tube_light_ceiling", [("tube_light/body", BODY)] + hang + cab, mount="ceiling", origin="ceiling plane, centre",
          light_at=[0, 0, round(-GAP - 0.1, 4)], light_dir=[0, 0, -1], suggested=sug,
          cable_ends=[dict(at=[0.75, 0, 0], dir=[0, 0, 1]), dict(at=[-0.75, 0, 0], dir=[0, 0, 1])])
    PB = T((0, 0.2, 0.989))
    F.obj("tube_light", "tube_light_pole", [("tube_light/post", None), ("tube_light/body", PB @ BODY), ("tube_light/hanger", PB @ T((-0.3, 0, 0))),
                                           ("tube_light/hanger", PB @ T((0.3, 0, 0))), ("tube_light/cable", PB @ T((0.7, 0, 0)))],
          mount="rail", origin="top of the handrail top rail, over a post; rail along X, fitting on the +Y (deck) side",
          light_at=[0, 0.2, round(0.989 - GAP - 0.1, 4)], light_dir=[0, 0, -1], suggested=sug,
          cable_ends=[dict(at=[0, -0.0375, -0.12], dir=[0, 1, 0], note="tail from the clamp ends on the handrail post")])
    F.obj("tube_light", "tube_light_broken", [("tube_light/body", DROP)] + hang + [("tube_light/cable_loose", T((0.75, 0, 0)))], mount="ceiling",
          origin="ceiling plane, centre (as tube_light_ceiling)",
          light_at=[0.05, 0, round(-GAP - 0.2, 4)], light_dir=[0.2079, 0, -0.9781], suggested=dict(sug, power=0.8, note="one tube out: flicker it"),
          cable_ends=[dict(at=[0.75, 0, 0], dir=[0, 0, 1])])


if __name__ == "__main__": lkit.run([define], only=["tube_light"])
