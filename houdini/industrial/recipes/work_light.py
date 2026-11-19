import math
from .. import lighting as lkit
from ..lighting import T, R, V, X, Y, Z, Matrix

HUB, LOW, TOP = 0.80, 0.36, 1.50         # leg hub, brace hub, crossbar underside
HX = 0.19                                # head centres on the crossbar

def r4(values):
    return [round(x,4) for x in values]


def define(F):
    b = F.part("work_light/mast", 0.34)
    b.cyl("mast_lo", (0, 0, 0.2), (0, 0, 1.05), 0.02, n=6, mat="yellow", caps=(True, False))
    b.cyl("mast_hi", (0, 0, 1.05), (0, 0, TOP), 0.015, n=6, mat="yellow", caps=(False, False))
    b.cyl("collar", (0, 0, 1.03), (0, 0, 1.07), 0.027, n=6, mat="black")
    b.cyl("hub", (0, 0, HUB - 0.03), (0, 0, HUB + 0.03), 0.032, n=6, mat="galv")
    b.cyl("hub_lo", (0, 0, LOW - 0.02), (0, 0, LOW + 0.02), 0.03, n=6, mat="galv")
    b.box("crossbar", (-0.32, -0.02, TOP), (0.32, 0.02, TOP + 0.04), mat="yellow")
    b.cyl("d_knob", (0.026, 0, 1.05), (0.05, 0, 1.05), 0.011, n=8, mat="black", detail=True)
    for sx in (-1, 1): F.bolt((sx * 0.012, -0.02, TOP + 0.02), (0, -1, 0), r=0.006, mat="galv")

    b = F.part("work_light/leg", 0.32)              # one leg in the X-Z plane, towards +X
    p0, p1 = V((0.03, 0, HUB)), V((0.55, 0, 0.03)); d = (p1 - p0).normalized()
    b.cyl("leg", p0, p1, 0.014, n=4, mat="yellow", caps=(False, False))
    b.cyl("foot", p1 - d * 0.03, p1 + d * 0.016, 0.02, n=4, mat="black")
    b.cyl("brace", (0.028, 0, LOW), p0 + d * 0.50, 0.008, n=3, mat="yellow", caps=(False, False))
    F.bolt(p0 + d * 0.50 + V((0, -0.014, 0)), (0, -1, 0), r=0.006, mat="galv")

    b = F.part("work_light/head", 0.13)             # small flood head with wire guard; origin on the crossbar top
    b.cyl("stem", (0, 0, 0), (0, 0, 0.03), 0.012, n=6, mat="galv", caps=(False, False))
    b.box("body", (-0.1, -0.03, 0.03), (0.1, 0.04, 0.2), mat="dgrey", skip="-y")
    q = [(-0.1, -0.085), (0.1, -0.085), (0.1, 0.085), (-0.1, 0.085)]; qi = [(-0.08, -0.065), (0.08, -0.065), (0.08, 0.065), (-0.08, 0.065)]
    b.ring_plate("bezel", (0, -0.045, 0.115), X, Z, q, qi, -0.015, 0, mat="dgrey", back=False)
    b.strip("lens", (-0.08, -0.033, 0.05), (0.16, 0, 0), Z, (0, -1, 0), [(0, 0), (0.13, 0)], mat="lit_work")
    for k in range(5):
        x = -0.072 + k * 0.036
        b.box("fin", (x - 0.004, 0.04, 0.04), (x + 0.004, 0.062, 0.19), mat="dgrey", skip="-y")
    for z in (0.08, 0.15):
        F.tube("guard_h", [(-0.092, -0.045, z), (-0.092, -0.08, z), (0.092, -0.08, z), (0.092, -0.045, z)], 0.0035, n=3, mat="galv", bend=0.015, seg=1)
    for x in (-0.04, 0.04): b.cyl("guard_v", (x, -0.077, 0.045), (x, -0.077, 0.185), 0.0035, n=3, mat="galv", caps=(True, True))
    F.decal("decal_flood.png", (0, -0.033, 0.115), (0, -1, 0), Z, 0.16, 0.13, kind="label", mats=("lit_work",), depth=0.008)
    for sx in (-1, 1):
        for sz in (-1, 1): F.bolt((sx * 0.09, -0.045, 0.115 + sz * 0.075), (0, -1, 0), r=0.005)
        b.cyl("d_knob", (sx * 0.099, 0, 0.115), (sx * 0.112, 0, 0.115), 0.014, n=8, mat="black", detail=True)

    b = F.part("work_light/cable_box", 0.95)        # cable from the crossbar down the mast, over the deck to the plug box
    F.tube("cable", [(0, 0.028, TOP), (0, 0.028, 0.22), (0.12, 0.12, 0.017), (0.5, 0.33, 0.017), (0.74, 0.2, 0.017), (0.79, 0.2, 0.04)],
           0.008, n=4, mat="black", bend=0.09, seg=1)
    b.box("plugbox", (0.79, 0.14, 0), (0.93, 0.26, 0.08), mat="yellow", skip="-z")
    b.box("d_lid", (0.80, 0.15, 0.079), (0.92, 0.25, 0.084), mat="yellow", detail=True)
    b.cyl("d_gland", (0.776, 0.2, 0.04), (0.791, 0.2, 0.04), 0.014, n=6, mat="brass", detail=True)
    for sx in (0.812, 0.908):
        for sy in (0.162, 0.238): F.bolt((sx, sy, 0.084), Z, r=0.005, h=0.003)
    for z in (0.5, 0.95, 1.35): b.cyl("d_tie", (0, 0.0, z - 0.006), (0, 0.0, z + 0.006), 0.0375, n=10, mat="black", detail=True)

    b = F.part("work_light/handlamp", 0.16)         # wall hook, lamp, coil, socket box; z = 0 at the bottom
    LY = -0.075; HK = 0.47
    b.box("hookplate", (-0.025, -0.006, HK - 0.04), (0.025, 0, HK + 0.04), mat="galv", skip="+y")
    F.tube("hook", [(0, -0.006, HK), (0, -0.092, HK), (0, -0.092, HK + 0.03)], 0.005, n=3, mat="galv", bend=0.015, seg=1, caps=(False, True))
    b.lathe("cap", [(0.042, 0.395), (0.04, 0.425), (0.012, 0.458)], n=8, mat="grey", at=(0, LY, 0), cap_top=True)
    b.lathe("glass", [(0.02, 0.265), (0.033, 0.285), (0.033, 0.395)], n=8, mat="lit_work_hand", at=(0, LY, 0))
    for k in range(4):
        a = math.radians(k * 90 + 22.5); c, s = math.cos(a), math.sin(a)
        F.tube("cage", [(c * 0.04, LY + s * 0.04, 0.395), (c * 0.04, LY + s * 0.04, 0.292), (c * 0.024, LY + s * 0.024, 0.262)], 0.0028, n=3, mat="galv", bend=0.02, seg=1)
    b.torus("hoop", (0, LY, 0.34), 0.04, 0.0028, n=8, m=3, mat="galv")
    b.cyl("collar", (0, LY, 0.245), (0, LY, 0.265), 0.027, n=8, mat="grey", caps=(True, True))
    b.cyl("handle", (0, LY, 0.13), (0, LY, 0.245), 0.017, n=6, mat="black", caps=(True, False))
    F.tube("lead", [(0, LY, 0.13), (0, LY, 0.085), (0.09, -0.025, 0.085), (0.09, -0.025, 0.33)], 0.006, n=3, mat="black", bend=0.03, seg=1)
    F.xf(T((0, -0.025, 0.33)) @ R(90, "X") @ Matrix.Diagonal((1, 1.55, 1, 1)))     # an oval hank of cable on the hook
    b.torus("coil", (0, 0, 0), 0.09, 0.013, n=10, m=4, mat="black", squash=1.3)
    for k, (dr, dz) in enumerate(((0.009, 0.009), (-0.009, 0.009), (0.009, -0.009), (-0.009, -0.009), (0, 0.016))):
        b.torus("d_turn", (0, 0, dz), 0.09 + dr, 0.0062, n=20, m=6, mat="black", detail=True)
    F.xf()
    b.box("socket", (-0.125, -0.05, 0), (-0.055, 0, 0.07), mat="grey", skip="+y")
    b.cyl("drop", (-0.09, -0.025, 0.33), (-0.09, -0.025, 0.07), 0.006, n=3, mat="black", caps=(False, False))
    b.cyl("d_plug", (-0.09, -0.025, 0.069), (-0.09, -0.025, 0.1), 0.016, n=8, mat="black", detail=True)
    b.cyl("d_ring", (0, LY, 0.455), (0, LY, 0.475), 0.008, n=8, mat="galv", detail=True)
    F.facet_ribs((0, LY, 0), (0.033, 0.288), (0.033, 0.392), per=2, rr=0.0024, mat="lit_work_hand")
    for z in (HK - 0.028, HK + 0.028): F.bolt((0, -0.006, z), (0, -1, 0), r=0.006, mat="galv")
    for sx in (-0.115, -0.065):
        for z in (0.012, 0.058): F.bolt((sx, -0.05, z), (0, -1, 0), r=0.004)

    legs = [("work_light/leg", R(90 + 120 * k, "Z")) for k in range(3)]
    hm = [T((sx * HX, 0, TOP + 0.04)) @ R(sx * -8, "Z") @ R(8, "X") @ Matrix.Scale(1.35, 4) for sx in (-1, 1)]    # the baked head is 0.2 m wide
    lp, ld = V((0, -0.05, 0.115)), V((0, -1, 0))
    F.obj("work_light", "work_tripod", [("work_light/mast", None), ("work_light/cable_box", None)] + legs + [("work_light/head", m) for m in hm],
          mount="deck", origin="on the deck under the mast; heads throw to -Y",
          light_at=r4(((hm[0] @ lp) + (hm[1] @ lp)) / 2), light_dir=r4(R(8, "X").to_3x3() @ ld),
          lights=[dict(at=r4(m @ lp), dir=r4((m.to_3x3() @ ld).normalized())) for m in hm],
          suggested=dict(kelvin=3200, rgb=[1.0, 0.90, 0.74], power=4.0, lumens=9000, spot_deg=120, range_m=14, note="both heads together; halve it per head"),
          cable_ends=[dict(at=[0.86, 0.2, 0], dir=[0, 0, -1], note="the plug box on the deck is the end")])
    F.obj("work_light", "work_handlamp", [("work_light/handlamp", None)], mount="wall", origin="wall plane, bottom centre (0.47 below the hook)",
          light_at=[0, LY, 0.34], light_dir=None, suggested=dict(kelvin=2700, rgb=[1.0, 0.82, 0.58], power=0.6, lumens=450, spot_deg=None, range_m=5),
          cable_ends=[dict(at=[-0.09, 0, 0.035], dir=[0, 1, 0], note="plugged into the socket box on the wall")])
