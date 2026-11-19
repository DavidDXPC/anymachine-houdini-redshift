# station.py: the lifeboat station's shared numbers.  Both builds (survival_craft, lifeboat_davit) are made in the
# STATION frame, which is the frame of the generated `lifeboat` prop they replace, so each is placed with that prop's
# own transform:  origin at the old prop's origin, boat length along Y (bow +Y), the platform deck edge is the plane
# x = EDGE_X with the deck on the -X side, and the top of the main deck is z = DECK_Z.
# The boat is described in BOAT coordinates (x forward, y to port, z up from the keel) and moved by BOAT_M.
import math
from .geometry import Vector, Matrix
V = Vector

EDGE_X, DECK_Z = -2.25, 2.6            # deck edge plane and deck top, station frame (old prop: bbox x +-2.02, z 0..6.207)
WALL_X = -4.25                         # face of the cellar wall under the gallery (map x = 2.0), where the knee braces land
BX, KZ = 0.55, 1.3                     # boat centre line and keel height, station frame
BOAT_M = Matrix.Translation((BX, 0, KZ)) @ Matrix.Rotation(math.radians(90), 4, "Z")     # boat -> station: (x, y) -> (-y, x)

# ------------------------------------------------------------------ hull sections
XS, XB, HB = -3.5, 3.75, 1.28          # transom, bow tip, half beam at the sheer
MID0, MID1 = -2.0, 1.4                 # parallel middle body
STN = [XS, -3.3, -3.1, -2.9, -2.6, -2.3, MID0, -1.0, 0.0, 0.7, MID1, 1.65, 1.9, 2.15, 2.4, 2.65, 2.9, 3.1, 3.3, 3.45, 3.57, 3.66, 3.72, XB]
NP = 13                                # points in a half section, keel centre to top centre


def sm(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def fb(x):                             # plan half breadth factor
    if x > MID1:
        u = min(1.0, (x - MID1) / (XB - MID1)); return max(0.0, 1 - u ** 1.9) ** 0.8
    if x < MID0:
        u = (MID0 - x) / (MID0 - XS); return 1 - 0.2 * u * u
    return 1.0


def zk(x):                             # keel line: rises at the bow (raked stem) and aft over the propeller
    if x > 1.6: return 1.15 * ((x - 1.6) / (XB - 1.6)) ** 2.2
    if x < -2.3: return 0.62 * ((-2.3 - x) / (-2.3 - XS)) ** 1.3
    return 0.0


def zs(x):                             # sheer line (centre of the rubbing strake)
    return 1.28 + 0.14 * max(0.0, (x - MID1) / (XB - MID1)) ** 2


def gc(x):                             # canopy height factor: full over the middle, sloping down to the hook positions
    if x > MID1: return 1 - 0.70 * sm((x - MID1) / 1.7) - 0.12 * sm((x - 3.1) / (XB - 3.1))
    if x < -2.6: return 1 - 0.58 * sm((-2.6 - x) / (-2.6 - XS))
    return 1.0


def sec(x):
    """Half section at x: [(y, z)] from the keel centre up to the top centre."""
    b = HB * fb(x); k = zk(x); s = zs(x); g = gc(x); dep = (s - 0.2 - k) / 1.08
    kw = 0.05 * min(1.0, b / 0.3); c0 = s + 0.16
    P0, C, P1 = (b * 0.86, c0 + 0.82 * g), (b * 0.80, c0 + 1.25 * g), (b * 0.30, c0 + 1.29 * g)     # flat side panel, then a round shoulder
    bez = lambda t: tuple((1 - t) ** 2 * P0[i] + 2 * t * (1 - t) * C[i] + t * t * P1[i] for i in (0, 1))
    return [(0.0, k), (kw, k), (kw * 1.3, k + 0.15 * dep), (b * 0.84, k + (s - 0.2 - k) * 0.42), (b, s - 0.13), (b, s + 0.09),
            (b * 0.975, c0)] + [bez(t) for t in (0.0, 0.3, 0.55, 0.8, 1.0)] + [(0.0, c0 + 1.31 * g)]


def sec_lin(x):
    """The section on the built (faceted) hull: straight between the stations."""
    x = max(STN[0], min(STN[-1], x))
    for a, c in zip(STN, STN[1:]):
        if a <= x <= c:
            t = (x - a) / (c - a); A, C = sec(a), sec(c)
            return [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t) for p, q in zip(A, C)]


def frame(x, j, t, sg):
    """A point on the built hull and its frame: facet j (between section points j and j+1), fraction t up it, side
    sg (+1 port, -1 starboard).  Returns (p, n outward, fwd along the boat, up along the section)."""
    S = sec_lin(x); a = V((x, sg * S[j][0], S[j][1])); c = V((x, sg * S[j + 1][0], S[j + 1][1])); p = a + (c - a) * t
    d = 0.02; x0, x1 = max(STN[0], x - d), min(STN[-1], x + d); S0, S1 = sec_lin(x0), sec_lin(x1)
    q0 = V((x0, sg * (S0[j][0] + (S0[j + 1][0] - S0[j][0]) * t), S0[j][1] + (S0[j + 1][1] - S0[j][1]) * t))
    q1 = V((x1, sg * (S1[j][0] + (S1[j + 1][0] - S1[j][0]) * t), S1[j][1] + (S1[j + 1][1] - S1[j][1]) * t))
    fwd = (q1 - q0).normalized(); up = (c - a).normalized(); n = fwd.cross(up).normalized()
    if n.dot(V((0, p.y, p.z - 1.3))) < 0: n = -n
    up = n.cross(fwd).normalized()
    if up.dot(c - a) < 0: up = -up
    return p, n, fwd, up


def top_z(x):
    return sec_lin(x)[-1][1]


# ------------------------------------------------------------------ lifting hooks (boat coordinates) and what the falls need
HOOK_X = (3.0, -3.0)                   # fore, aft: on the centre line
HOOK_BOX_H, HOOK_PIVOT, HOOK_ARC, HOOK_R = 0.30, 0.09, 0.205, 0.065      # box height, pivot above the box, bowl of the hook above the pivot, bowl radius


def hook_base(i):
    x = HOOK_X[i]; return min(top_z(x - 0.17), top_z(x + 0.17)) - 0.03


def hook_point(i):
    """Where the suspension link bears in the hook (boat coordinates)."""
    x = HOOK_X[i]; return V((x + math.copysign(HOOK_R, x), 0, hook_base(i) + HOOK_BOX_H + HOOK_PIVOT + HOOK_ARC))


def hook_point_station(i):
    return BOAT_M @ hook_point(i)
