# survival_craft: totally enclosed motor-propelled survival craft (the platform's lifeboat), hand-modelled from
# sheets/survival_craft_turn.png, _close1.png, _close2.png.  Replaces the boat half of the generated `lifeboat` prop.
# Built in boat coordinates (x forward, y to port, z up from the keel), delivered in the station frame (see
# _shared/station.py): place it with the old lifeboat's transform, together with lifeboat_davit.
# One 2048 texture set.  Separate real parts: moulded hull and canopy, rubber rubbing strake, boarding hatches with
# hinges and dogs, portlights in gaskets, conning position, on-load release hooks in their boxes, deluge pipe, grab
# rails, becketed grab line, propeller in its nozzle, rudder.  Tape, lettering, screws and seals are bake-only.
#   blender -b --factory-startup -t 4 --python build.py [-- --nobake] [--size 2048] [--spp 24] [--noreview]
import bpy, bmesh, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "_shared"))
import station as st
import ls
from ls import lm, hs, V, Z, F, obox, tube, polytube
b = lm.start("survival_craft")
X, Y = V((1, 0, 0)), V((0, 1, 0))


def SF(x, j, t, sg):
    """Frame matrix on the hull surface: local x = up cross n (so lettering reads from outside), y = up, z = outward."""
    p, n, fwd, up = st.frame(x, j, t, sg); return F(p, up.cross(n), up), p, n, up


def loft(name, rings, mat, closed=False, cap0=False, cap1=False, flip=False):
    bm = bmesh.new(); R = [[bm.verts.new(p) for p in r] for r in rings]; n = len(rings[0])
    for a, c in zip(R, R[1:]):
        for k in range(n if closed else n - 1):
            j = (k + 1) % n; f = (a[k], c[k], c[j], a[j]); bm.faces.new(tuple(reversed(f)) if flip else f)
    if cap0: bm.faces.new(R[0] if not flip else list(reversed(R[0])))
    if cap1: bm.faces.new(list(reversed(R[-1])) if not flip else R[-1])
    hs._quad_caps(bm)
    return b._obj(bm, name, mat)


def frustum(name, c0, a0, b0, c1, a1, b1, mat, top=True):
    """Tapered box from the rectangle (centre c0, half sizes a0 along x, b0 along y) up to (c1, a1, b1).  No bottom."""
    c0, c1 = V(c0), V(c1)
    r0 = [c0 + V((sx * a0, sy * b0, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    r1 = [c1 + V((sx * a1, sy * b1, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm = bmesh.new(); A_ = [bm.verts.new(p) for p in r0]; B_ = [bm.verts.new(p) for p in r1]
    for k in range(4):
        j = (k + 1) % 4; bm.faces.new((A_[k], A_[j], B_[j], B_[k]))
    if top: bm.faces.new(B_)
    b._obj(bm, name, mat)
    return r0, r1


# ---------------------------------------------------------------- hull and canopy: one moulding, lofted through the stations
rings = []
for x in st.STN:
    S = st.sec(x)
    rings.append([V((x, -y, z)) for y, z in S] + [V((x, y, z)) for y, z in reversed(S[1:-1])])      # starboard up, port down
loft("hull", rings, "orange", closed=True, cap0=True)

# ---------------------------------------------------------------- rubbing strake: black rubber D section right round
DP = [(0.0, -0.07), (0.045, -0.062), (0.075, -0.025), (0.075, 0.025), (0.045, 0.062), (0.0, 0.07)]
def plan_n(x):
    if x >= st.XB - 1e-6: return 1.0, 0.0
    d = (st.HB * st.fb(min(st.XB, x + 0.004)) - st.HB * st.fb(max(st.XS, x - 0.004))) / (min(st.XB, x + 0.004) - max(st.XS, x - 0.004))
    L = math.hypot(d, 1.0); return -d / L, 1.0 / L
for sg in (-1, 1):
    rr = []
    for x in st.STN:
        nx, ny = plan_n(x); bb = st.HB * st.fb(x); z = st.zs(x) - 0.02
        rr.append([V((x + nx * o, sg * (bb + ny * o), z + dz)) for o, dz in DP])
    loft("strake", rr, "rubber", cap0=True, flip=(sg > 0))
bt = st.HB * st.fb(st.XS)
lm.sect(b, "strake_stern", (st.XS, -(bt + 0.075), st.zs(st.XS) - 0.02), (st.XS, bt + 0.075, st.zs(st.XS) - 0.02), DP, -X, "rubber", caps=(True, True))
for sg in (-1, 1):                                   # strake end fixings at the quarters, and screws along it (bake)
    for x in [st.XS + 0.06] + [-3.0 + 0.5 * k for k in range(13)]:
        nx, ny = plan_n(x); bb = st.HB * st.fb(x)
        b.rivet(V((x + nx * 0.075, sg * (bb + ny * 0.075), st.zs(x) - 0.02)), V((nx, sg * ny, 0)), r=0.009, mat="stain")


# ---------------------------------------------------------------- hatches, portlights
def hatch(M, w, h, grab=True):
    """Outward-opening hatch on the frame M: moulded coaming, raised lid, seal, two hinges, two lever dogs."""
    a, c = w / 2, h / 2
    obox(b, "hatch_coaming", M, (-a - 0.07, -c - 0.06, -0.012), (a + 0.07, c + 0.06, 0.028), mat="orange", bev=0.014, skip="-z")
    obox(b, "hatch_lid", M, (-a, -c, 0.028), (a, c, 0.054), mat="orange", bev=0.012, skip="-z")
    for (x0, x1, y0, y1) in ((-a - 0.012, a + 0.012, -c - 0.012, -c), (-a - 0.012, a + 0.012, c, c + 0.012), (-a - 0.012, -a, -c, c), (a, a + 0.012, -c, c)):
        obox(b, "d_seal", M, (x0, y0, 0.027), (x1, y1, 0.034), mat="rubber", skip="-z", detail=True)
    for y in (-c * 0.56, c * 0.56):
        obox(b, "hinge_leaf", M, (-a - 0.115, y - 0.05, 0.028), (-a - 0.006, y + 0.05, 0.037), mat="galv", skip="-z")
        obox(b, "hinge_leaf", M, (-a + 0.006, y - 0.05, 0.054), (-a + 0.13, y + 0.05, 0.063), mat="galv", skip="-z")
        b.cyl("hinge_knuckle", M @ V((-a, y - 0.055, 0.058)), M @ V((-a, y + 0.055, 0.058)), 0.015, n=8, mat="galv", caps=(True, True))
        nz = (M.to_3x3() @ Z)
        for dx, z in ((-0.085, 0.037), (-0.04, 0.037), (0.05, 0.063), (0.1, 0.063)):
            for dy in (-0.028, 0.028): b.bolt(M @ V((-a + dx, y + dy, z)), nz, r=0.007, h=0.004, mat="galv")
        yd = y * 0.9
        b.cyl("dog_boss", M @ V((a - 0.1, yd, 0.054)), M @ V((a - 0.1, yd, 0.09)), 0.03, n=10, mat="stain", caps=(False, True), bev=0.006)
        e = V((-0.2, -0.085 if y > 0 else 0.085, 0))
        b.cyl("dog_lever", M @ V((a - 0.1, yd, 0.078)), M @ (V((a - 0.1, yd, 0.078)) + e), 0.011, n=6, mat="stain", caps=(False, False))
        b.cyl("dog_knob", M @ (V((a - 0.1, yd, 0.078)) + e), M @ (V((a - 0.1, yd, 0.078)) + e * 1.14), 0.016, n=6, mat="stain", caps=(True, True))
    if grab:
        gx = a + 0.15
        polytube(b, "hatch_grab", [M @ V(p) for p in ((gx, -0.17, 0.0), (gx, -0.17, 0.065), (gx, 0.17, 0.065), (gx, 0.17, 0.0))], 0.012, n=6, mat="stain", caps=(False, False))
        for y in (-0.17, 0.17): b.cyl("d_foot", M @ V((gx, y, -0.001)), M @ V((gx, y, 0.006)), 0.024, n=10, mat="stain", caps=(False, True), detail=True)


def portlight(M, w, h, name="port"):
    """Fixed light: black rubber gasket ring with clipped corners, pane set back in it, a ring of screws (bake)."""
    a, c, g = w / 2, h / 2, 0.045
    ex, ey = M.to_3x3() @ X, M.to_3x3() @ Y; nz = M.to_3x3() @ Z
    def clip(px, py):
        if abs(abs(px) - (a + g)) < 1e-6 and abs(abs(py) - (c + g)) < 1e-6: return px * (1 - 0.03 / (a + g)), py * (1 - 0.03 / (c + g))
        return px, py
    lm.grid_plate(b, name + "_gasket", M @ V((0, 0, 0.008)), ex, ey, [-a - g, -a, a, a + g], [-c - g, -c, c, c + g], 0.02, holes=[(1, 1)], mat="rubber", warp=clip)
    obox(b, name + "_glass", M, (-a, -c, 0.0), (a, c, 0.005), mat="glass", skip="-z,-x,+x,-y,+y")
    nx_, ny_ = max(2, round(w / 0.11)), max(1, round(h / 0.11))
    pts = [(-a + w * i / nx_, sy * (c + g / 2)) for i in range(nx_ + 1) for sy in (-1, 1)] + [(sx * (a + g / 2), -c + h * (k + 0.5) / ny_) for k in range(ny_) for sx in (-1, 1)]
    for px, py in pts: b.rivet(M @ V((px, py, 0.018)), nz, r=0.0065, mat="stain")


def dplate(M, w, h, mat, t=0.0014, name="d_tape"):
    obox(b, name, M, (-w / 2, -h / 2, 0.0004), (w / 2, h / 2, t), mat=mat, skip="-z", detail=True)


for sg in (-1, 1):
    hatch(SF(0.0, 6, 0.5, sg)[0], 0.9, 0.7)
    portlight(SF(-1.9, 6, 0.6, sg)[0], 0.3, 0.2); portlight(SF(1.68, 6, 0.6, sg)[0], 0.34, 0.2)
    # lettering (bake): identification aft of the hatch, capacity forward of it
    M, p, n, up = SF(-1.14, 6, 0.56, sg); ls.text(b, "LIFEBOAT", p, up.cross(n), up, 0.115)
    M, p, n, up = SF(0.98, 6, 0.66, sg); ls.text(b, "CAPACITY", p, up.cross(n), up, 0.07)
    M, p, n, up = SF(0.98, 6, 0.48, sg); ls.text(b, "26 PERSONS", p, up.cross(n), up, 0.07)
    # retro-reflective tape: bars round the canopy, along the topsides and on the bottom
    for x in (-3.1, -2.45, -1.45, -0.72, 0.72, 1.3, 2.1, 2.75, 3.2): dplate(SF(x, 6, 0.93 if -2.6 < x < 1.5 else 0.6, sg)[0], 0.3, 0.05, "tape")
    for x in (-3.0, -2.2, -1.4, -0.6, 0.2, 1.0, 1.8, 2.5, 3.05): dplate(SF(x, 3, 0.5, sg)[0], 0.3, 0.05, "tape")
    for x in (-1.6, 0.0, 1.5): dplate(SF(x, 2, 0.6, sg)[0], 0.3, 0.05, "tape")
    for x in (-0.9, 0.9): dplate(SF(x, 9, 0.5, sg)[0], 0.3, 0.05, "tape")
    # grab rail along the canopy shoulder
    xs_ = [-1.25, -0.45, 0.35, 1.15, 1.85]; fr = [st.frame(x, 8, 0.5, sg) for x in xs_]
    pts = [fr[0][0] - X * 0.0] + [f[0] + f[1] * 0.075 for f in fr] + [fr[-1][0]]
    pts[0] = fr[0][0] - X * 0.07; pts[-1] = fr[-1][0] + X * 0.07
    polytube(b, "canopy_rail", pts, 0.016, n=8, mat="stain", caps=(False, False))
    for f in fr[1:-1]:
        b.cyl("rail_stanchion", f[0], f[0] + f[1] * 0.075, 0.011, n=6, mat="stain", caps=(False, False))
        b.cyl("d_foot", f[0] - f[1] * 0.001, f[0] + f[1] * 0.006, 0.026, n=10, mat="stain", caps=(False, True), detail=True)
    # becketed grab line: eyes under the strake, rope hanging in loops between them
    xe = [-3.3, -2.7, -2.1, -1.5, -0.9, -0.3, 0.3, 0.9, 1.5, 2.1, 2.6, 3.0, 3.3, 3.52]; rope = []
    ef = [st.frame(x, 3, 0.95, sg) for x in xe]
    for i, (p, n, fwd, up) in enumerate(ef):
        M = F(p, up.cross(n), up)
        obox(b, "becket_eye", M, (-0.022, -0.03, 0.0), (0.022, 0.03, 0.01), mat="galv", skip="-z")
        b.cyl("becket_lug", p + n * 0.01, p + n * 0.045, 0.014, n=6, mat="galv", caps=(False, True))
        b.bolt(M @ V((0, 0.019, 0.01)), n, r=0.006, h=0.004, mat="galv"); b.bolt(M @ V((0, -0.019, 0.01)), n, r=0.006, h=0.004, mat="galv")
        a = p + n * 0.04 - Z * 0.012; rope.append(a)
        if i < len(ef) - 1:
            q = ef[i + 1][0] + ef[i + 1][1] * 0.04 - Z * 0.012; nm = (n + ef[i + 1][1]).normalized()
            for t in (0.2, 0.5, 0.8):
                k = 4 * t * (1 - t); rope.append(a + (q - a) * t - Z * 0.17 * k + nm * 0.035 * k)
    polytube(b, "becket_line", rope, 0.013, n=5, mat="rope", caps=(True, True))

# top hatch forward, on the centre line
hatch(F((0.45, 0, st.top_z(0.45) - 0.022), X, Y), 0.62, 0.56, grab=False)

# ---------------------------------------------------------------- conning position aft: tower, windows, roof hatch, light, rails
TZ0, TZ1 = st.top_z(-1.9) - 0.17, st.top_z(-1.9) + 0.32
r0, r1 = frustum("tower", (-1.93, 0, TZ0), 0.58, 0.56, (-1.97, 0, TZ1), 0.50, 0.455, "orange", top=False)
obox(b, "tower_roof", F((-1.97, 0, TZ1), X, Y), (-0.53, -0.485, 0.0), (0.53, 0.485, 0.036), mat="orange", bev=0.012)
def face(k):                                        # frame on tower side k (0: starboard, 1: front, 2: port, 3: rear)
    j = (k + 1) % 4; c = (r0[k] + r0[j] + r1[k] + r1[j]) / 4; up = ((r1[k] + r1[j]) - (r0[k] + r0[j])).normalized()
    n = (r0[j] - r0[k]).cross(up).normalized(); return c, n, up
for k in range(4):
    c, n, up = face(k); ex = up.cross(n); c = c + up * 0.07
    if k in (0, 2): portlight(F(c, ex, up), 0.56, 0.2, "tower_win")
    else:
        for o in (-0.225, 0.225): portlight(F(c + ex * o, ex, up), 0.3, 0.2, "tower_win")
RT = TZ1 + 0.036
MR = F((-1.9, 0, RT), X, Y)
obox(b, "roof_hatch", MR, (-0.26, -0.25, 0.0), (0.26, 0.25, 0.028), mat="orange", bev=0.01, skip="-z")
for y in (-0.14, 0.14):
    obox(b, "hinge_leaf", MR, (-0.33, y - 0.04, 0.0), (-0.2, y + 0.04, 0.036), mat="galv", skip="-z")
    b.cyl("hinge_knuckle", MR @ V((-0.265, y - 0.045, 0.036)), MR @ V((-0.265, y + 0.045, 0.036)), 0.013, n=8, mat="galv", caps=(True, True))
polytube(b, "roof_hatch_grab", [MR @ V(p) for p in ((0.16, -0.1, 0.028), (0.16, -0.1, 0.075), (0.16, 0.1, 0.075), (0.16, 0.1, 0.028))], 0.01, n=6, mat="stain", caps=(False, False))
for y in (-0.41, 0.41):
    polytube(b, "tower_rail", [(-2.42, y, RT), (-2.36, y, RT + 0.085), (-1.58, y, RT + 0.085), (-1.52, y, RT)], 0.014, n=8, mat="stain", caps=(False, False))
    b.cyl("rail_stanchion", V((-1.97, y, RT)), V((-1.97, y, RT + 0.085)), 0.01, n=6, mat="stain", caps=(False, False))
NL = V((-2.36, 0.0, RT))
lm.spun(b, "nav_mast", NL, Z, [(0.045, 0), (0.045, 0.02), (0.018, 0.035), (0.018, 0.27), (0.045, 0.28), (0.045, 0.305)], n=10, mat="stain")
lm.spun(b, "nav_lens", NL + Z * 0.305, Z, [(0.04, 0), (0.04, 0.075)], n=10, mat="lampw")
lm.spun(b, "nav_cap", NL + Z * 0.38, Z, [(0.046, 0), (0.046, 0.012), (0.0, 0.02)], n=10, mat="stain")

# ---------------------------------------------------------------- deluge (water spray) pipe along the canopy top, port of the hatch
px_ = [-1.34, -0.5, 0.45, 1.4, 1.8, 2.2, 2.55, 2.78]; pf = [st.frame(x, 10, 0.7, 1) for x in px_]
polytube(b, "deluge_pipe", [f[0] + f[1] * 0.06 for f in pf], 0.017, n=6, mat="stain", caps=(True, True))
for i, f in enumerate(pf):
    b.cyl("deluge_stand", f[0], f[0] + f[1] * 0.05, 0.009, n=5, mat="stain", caps=(False, False))
    obox(b, "d_clip", F(f[0] + f[1] * 0.06, f[2], f[1].cross(f[2])), (-0.012, -0.024, -0.022), (0.012, 0.024, 0.022), mat="stain", detail=True)
    if i in (1, 2, 3, 5, 7):
        c = f[0] + f[1] * 0.06 + f[2] * 0.12
        lm.spun(b, "deluge_nozzle", c, f[1], [(0.012, 0.0), (0.012, 0.04), (0.022, 0.05), (0.022, 0.062), (0.0, 0.062)], n=6, mat="stain")


# ---------------------------------------------------------------- on-load release hooks in their boxes, fore and aft
def hook(i):
    x = st.HOOK_X[i]; d = 1 if x > 0 else -1; z0 = st.hook_base(i); zt = z0 + st.HOOK_BOX_H
    frustum("hook_box", (x, 0, z0), 0.17, 0.15, (x, 0, zt), 0.13, 0.115, "galv", top=False)
    MB = F((x, 0, zt), X, Y)
    obox(b, "hook_box_lid", MB, (-0.145, -0.13, 0.0), (0.145, 0.13, 0.014), mat="galv", bev=0.004)
    for sx in (-1, 1):
        for sy in (-1, 1): b.bolt(MB @ V((sx * 0.12, sy * 0.105, 0.014)), Z, r=0.01, h=0.006, mat="galv")
        for k in range(4):                           # box side fixings (bake): a row down each corner flange
            b.bolt(V((x + sx * (0.165 - 0.0 * k), 0.0, z0 + 0.06)) + V((0, (k - 1.5) * 0.07, 0)), V((sx, 0, 0.13)), r=0.009, h=0.005, mat="galv")
    for sy in (-1, 1):
        for k in range(4): b.bolt(V((x + (k - 1.5) * 0.08, sy * 0.146, z0 + 0.06)), V((0, sy, 0.13)), r=0.009, h=0.005, mat="galv")
        lm.grid_plate(b, "hook_cheek", V((x, sy * 0.045, zt + 0.014)), X, Z, [-0.075, -0.03, 0.03, 0.075], [0.0, 0.07, 0.14], 0.016, mat="galv",
                      warp=lambda px, pz: (px * (0.55 if pz > 0.13 else 1.0), pz))
    pv = V((x, 0, zt + st.HOOK_PIVOT))
    b.cyl("hook_pin", pv - Y * 0.07, pv + Y * 0.07, 0.016, n=8, mat="galv", caps=(True, True))
    for sy in (-1, 1): b.cyl("hook_pin_nut", pv + Y * sy * 0.053, pv + Y * sy * 0.068, 0.026, n=6, mat="galv", caps=(True, True))
    R = st.HOOK_R; C = pv + V((d * R, 0, st.HOOK_ARC - R + 0.03))
    pts = [pv + V((0, 0, -0.03)), pv + V((0, 0, 0.05)), V((pv.x, 0, C.z))]
    rad = [(0.04, 0.03), (0.036, 0.03), (0.03, 0.028)]
    for a in (150, 120, 90, 60, 30, 0, -30, -55):
        ar = math.radians(a); pts.append(C + V((-d * R * math.cos(ar), 0, R * math.sin(ar)))); t = (150 - a) / 205
        rad.append((0.03 - 0.018 * t ** 2, 0.028 - 0.014 * t ** 2))
    lm.sweep(b, "hook", pts, rad, Y if d > 0 else -Y, n=8, mat="galv")
    # release cable: from the box side down onto the canopy and aft to a gland
    s_ = -d; g0 = V((x + s_ * 0.16, 0.06, z0 + 0.2)); xg = x + s_ * 0.55
    polytube(b, "release_cable", [g0, g0 + V((s_ * 0.08, 0, 0.0)), V((x + s_ * 0.36, 0.06, st.top_z(x + s_ * 0.36) + 0.05)), V((xg, 0.06, st.top_z(xg) + 0.012))], 0.007, n=5, mat="stain", caps=(False, False))
    b.cyl("cable_gland", V((xg, 0.06, st.top_z(xg) - 0.01)), V((xg, 0.06, st.top_z(xg) + 0.03)), 0.018, n=6, mat="stain", caps=(False, True))
    b.cyl("cable_gland", g0 - X * s_ * 0.03, g0 + X * s_ * 0.012, 0.016, n=6, mat="stain", caps=(False, True))


hook(0); hook(1)

# ---------------------------------------------------------------- stern gear: skeg, shoe, shaft, propeller in its nozzle, rudder, exhaust
b.prism("skeg", (0, 0, 0), X, Z, [(-3.08, 0.0), (-2.5, 0.0), (-2.5, 0.1), (-3.08, 0.44)], -0.035, 0.035, mat="orange", caps=(True, True))
b.box("shoe", (-3.68, -0.03, 0.0), (-3.08, 0.03, 0.05), mat="orange", skip="+x")
PC = V((-3.3, 0, 0.25))
b.cyl("shaft_boss", V((-3.06, 0, 0.25)), V((-3.23, 0, 0.25)), 0.05, n=8, mat="orange", caps=(False, True), r1=0.04)
lm.spun(b, "prop_hub", V((-3.23, 0, 0.25)), -X, [(0.045, 0), (0.05, 0.02), (0.05, 0.11), (0.03, 0.15), (0.0, 0.16)], n=8, mat="bronze")
for k in range(4):
    a = math.radians(45 + 90 * k); rd = V((0, math.cos(a), math.sin(a))); tg = X.cross(rd).normalized(); pt = (tg * math.cos(math.radians(32)) + X * math.sin(math.radians(32))).normalized()
    b.prism("prop_blade", PC + X * 0.01, rd, pt, [(0.035, -0.035), (0.11, -0.085), (0.175, -0.07), (0.2, -0.01), (0.175, 0.055), (0.11, 0.075), (0.035, 0.035)], -0.006, 0.006, mat="bronze", caps=(True, True))
lm.spun(b, "nozzle", V((-3.2, 0, 0.25)), -X, [(0.224, 0), (0.258, 0.03), (0.252, 0.21), (0.226, 0.21), (0.216, 0.1), (0.224, 0)], n=16, mat="galv")
b.box("nozzle_strut", (-3.38, -0.025, 0.49), (-3.24, 0.025, st.zk(-3.38) + 0.04), mat="orange", skip="+z,-z")
b.box("rudder", (-3.72, -0.022, 0.05), (-3.46, 0.022, 0.6), mat="orange", bev=0.01)
b.cyl("rudder_stock", V((-3.5, 0, 0.6)), V((-3.5, 0, 0.66)), 0.026, n=8, mat="stain", caps=(False, False))
b.cyl("rudder_heel", V((-3.5, 0, 0.0)), V((-3.5, 0, 0.05)), 0.03, n=8, mat="stain", caps=(True, False))
EX = V((st.XS, -0.52, 1.02))
b.cyl("exhaust", EX + X * 0.01, EX - X * 0.09, 0.062, n=10, mat="stain", caps=(False, False))
b.cyl("exhaust_in", EX - X * 0.04, EX - X * 0.041, 0.056, n=10, mat="dark", caps=(False, True))
lm.spun(b, "exhaust_flange", EX, -X, [(0.062, 0.0), (0.095, 0.0), (0.095, 0.012), (0.062, 0.012)], n=10, mat="stain")
for y in (-0.45, 0.45): dplate(F((st.XS, y, 1.02 if y > 0 else 0.86), -Y, Z), 0.3, 0.05, "tape")
# bow: painter eye plate and ring on the stem under the strake
BE = V((st.XB, 0, 1.2)); MBW = F(BE, Y, Z)
obox(b, "painter_plate", MBW, (-0.035, -0.06, -0.01), (0.035, 0.06, 0.012), mat="galv", skip="-z")
lm.spun(b, "painter_eye", BE + X * 0.045, Y, None, n=10, mat="galv", torus=(0.036, 0.011))
for dz in (-0.04, 0.04): b.bolt(MBW @ V((0, dz, 0.012)), X, r=0.008, h=0.005, mat="galv")


# ---------------------------------------------------------------- stains (projected in the bake): runs below fittings, grime round hatches
OM = ("orange",)
GR = lambda k: os.path.join(HERE, "..", "_tex", "gr_0%d.png" % k)      # dark grime streaks (see _tex/make_grime.py)
def run(x, j, t, sg, w, h, k, s_=0.75):
    M, p, n, up = SF(x, j, t, sg); b.decal(GR(k % 5), p - up * h * 0.5, n, up, w, h, kind="stain", mats=OM, depth=0.25, strength=s_)
for sg in (-1, 1):
    for i, x in enumerate((-1.9, 1.68)): run(x, 6, 0.46, sg, 0.3, 0.7, i + (sg > 0), 0.4)             # under the portlights
    for i, x in enumerate((-0.47, 0.47)): run(x, 6, 0.1, sg, 0.22, 0.5, i + 2, 0.5)                # hatch lower corners, hinges and dogs
    run(0.0, 6, 0.95, sg, 1.1, 0.25, 3, 0.3)                                                       # along the hatch head
    M_, p_, n_, up_ = SF(0.1, 3, 0.98, sg); b.decal(os.path.join(HERE, "..", "_tex", "gr_row.png"), p_ - up_ * 0.31, n_, up_, 6.6, 0.62, kind="stain", mats=OM, depth=1.0, strength=0.42)    # salt and rust weeping from under the strake (one strip)
    for i, x in enumerate((-2.2, 0.9, 2.4)): run(x, 7, 0.9, sg, 0.3, 1.0, i + 3, 0.32)             # dirt washed down off the canopy top
for i in (0, 1):                                                                                   # round the hook boxes and the top hatch
    b.decal(GR(5), (st.HOOK_X[i], 0, st.hook_base(i) + 0.05), (0, 0, 1), (1, 0, 0), 0.9, 0.9, kind="stain", mats=OM, depth=0.3, strength=0.5)
b.decal(GR(5), (0.45, 0, st.top_z(0.45)), (0, 0, 1), (1, 0, 0), 1.0, 1.0, kind="stain", mats=OM, depth=0.2, strength=0.35)
b.decal(GR(1), (st.XS, -0.52, 0.66), (-1, 0, 0), (0, 0, 1), 0.3, 0.7, kind="stain", mats=OM, depth=0.2, strength=0.8)     # soot and drips under the exhaust
for y, k in ((0.5, 2), (-0.1, 4)): b.decal(GR(k), (st.XS, y, 0.9), (-1, 0, 0), (0, 0, 1), 0.3, 0.6, kind="stain", mats=OM, depth=0.2, strength=0.4)


# ---------------------------------------------------------------- finish: maintained but in service (salt, grime in the seams, scuffed strake)
def wear(b):
    Wt, Rt, Gv = lm.tx("paint_offwhite.png"), lm.tx("rust_steel.png"), lm.tx("steel_galv.png")
    b.wear("orange", Wt, Rt, tile=2.2, edge=0.75, bias=-0.14, rust=0.3, dirt=0.7, tint=(0.92, 0.15, 0.02), value=1.25, rough=0.36, bump=0.1, dent=0.25, top=0.5, low=0.0, sat=0.0)
    b.wear("rubber", Wt, Rt, tile=0.6, edge=0.1, bias=-0.3, rust=0.0, dirt=0.6, tint=(0.03, 0.03, 0.032), rough=0.82, bump=0.9, dent=0.6, top=0.75, low=0.0, sat=0.0)
    b.wear("galv", Gv, Rt, tile=0.8, metal=0.65, rough=0.5, edge=0.5, bias=-0.16, rust=0.32, dirt=0.4, chip_metal=0.1, value=1.05, low=0.0)
    b.wear("stain", Gv, Rt, tile=0.6, metal=1.0, rough=0.26, edge=0.0, bias=-0.4, rust=0.0, dirt=0.3, value=1.25, sat=0.3, bump=0.1, low=0.0, top=0.0)
    b.wear("bronze", Gv, Rt, tile=0.6, metal=1.0, rough=0.34, edge=0.0, bias=-0.4, rust=0.0, dirt=0.45, tint=(1.0, 0.62, 0.26), value=1.1, bump=0.1, low=0.0, top=0.0)
    b.wear("glass", Wt, Rt, tile=2.0, edge=0.0, bias=-0.6, rust=0.0, dirt=0.12, tint=(0.03, 0.04, 0.045), rough=0.08, bump=0.0, top=0.0, low=0.0)
    b.wear("tape", Wt, Rt, tile=0.3, edge=0.0, bias=-0.6, rust=0.0, dirt=0.4, tint=(0.66, 0.68, 0.7), rough=0.36, metal=0.35, bump=0.05, top=0.0, low=0.0, sat=0.0)
    b.wear("rope", Wt, Rt, tile=0.25, edge=0.0, bias=-0.6, rust=0.0, dirt=0.6, tint=(0.74, 0.7, 0.62), rough=0.9, bump=0.8, dent=0.0, top=0.0, low=0.0)
    b.wear("stencil", Wt, Rt, tile=1.0, edge=0.0, bias=-0.6, rust=0.0, dirt=0.05, tint=(0.02, 0.02, 0.02), rough=0.5, bump=0.0, top=0.0, low=0.0)
    b.wear("lampw", Wt, Rt, tile=1.0, edge=0.0, bias=-0.6, rust=0.0, dirt=0.08, tint=(0.95, 0.94, 0.88), rough=0.15, bump=0.0, top=0.0, low=0.0)
    b.wear("dark", Rt, Rt, tile=0.9, value=0.12, edge=0.0, rust=0.0, dirt=0.5, rough=0.8, sat=0.2, low=0.0)


ls.tail([(b, wear, {"dark": 0.5})], HERE, "survival_craft", None, None, "180,0;-90,0;0,0;90,0;-90,90;-145,20", M=st.BOAT_M, sharp=52,
        place=dict(frame="station frame = the frame of the generated lifeboat prop: use that prop's transform unchanged",
                   scene_blender=[dict(loc=[-2.25, -21.0, 2.4], rot_z_deg=180), dict(loc=[-2.25, -33.0, 2.4], rot_z_deg=180)],
                   hook_points_station=[[round(c, 4) for c in st.hook_point_station(i)] for i in (0, 1)]),
        note="one object / one texture set.  Hangs by its two hooks from lifeboat_davit (same transform).")
