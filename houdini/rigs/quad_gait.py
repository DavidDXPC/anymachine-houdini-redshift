"""Analytic IK and rolling-contact clips, adapted from AnyMachine's quadruped gait."""
import math
import numpy as np

from .geometry import rx as Rx, ry as Ry

LEGS = ("FL","FR","HL","HR")
DIAG = {"FL":0.0, "HR":0.0, "FR":0.5, "HL":0.5}


def Vector(value):
    return np.array(value,dtype=float)


def rotation_vector(m):
    # Logarithm of the small proper rotation between adjacent sampled poses.
    v = np.array([m[2,1]-m[1,2], m[0,2]-m[2,0], m[1,0]-m[0,1]]) / 2
    s = np.linalg.norm(v)
    if s < 1e-12:
        return v
    return v * (math.atan2(s,(np.trace(m)-1)/2) / s)


class Leg:
    def __init__(self, name, spec, geo):
        self.name, self.s = name, spec["s"]
        self.P = Vector(spec["haa_pivot"])  # HAA pivot (rest, world)
        self.H = Vector(spec["hfe"])  # HFE axis point in the leg plane
        self.t0 = Vector((0, geo["t0"][0], geo["t0"][1]))  # rest thigh vector (y, z)
        self.s0 = Vector((0, geo["s0"][0], geo["s0"][1]))  # rest shin vector
        self.L1, self.L2 = np.linalg.norm(self.t0), np.linalg.norm(self.s0)
        self.psi0 = math.atan2(self.s0[2], self.s0[1]) - math.atan2(self.t0[2], self.t0[1])
        self.d = self.s * (self.H[0] - self.P[0])  # lateral offset of the leg plane from the HAA pivot (>0)
        self.lim = geo["limits_rad"]

    def haa_R(self, a):
        # right: about -Y by a; left: about +Y by a  (positive = outward)
        return Ry(-a) if self.s > 0 else Ry(a)

    def fk_local(self, a, f1, f2):
        """Body-frame (rest coords) knee, foot centre and foot rotation."""
        K = self.H + Rx(f1) @ self.t0
        F = K + Rx(f1 + f2) @ self.s0
        R = self.haa_R(a)
        return self.P + R @ (K - self.P), self.P + R @ (F - self.P), R @ Rx(f1 + f2)

    def ik_local(self, p):
        """Body-frame target foot centre -> (a, f1, f2), unclamped, plus a reach flag."""
        u = self.s * (p[0] - self.P[0])
        v = p[1] - self.P[1]
        w = p[2] - self.P[2]
        r2 = u * u + w * w
        wp = -math.sqrt(max(r2 - self.d ** 2, 1e-9))
        a = math.atan2(w, u) - math.atan2(wp, self.d)
        q2 = v * v + wp * wp
        c = (q2 - self.L1 ** 2 - self.L2 ** 2) / (2 * self.L1 * self.L2)
        ok = -1 <= c <= 1
        psi = math.copysign(math.acos(max(-1, min(1, c))), self.psi0)
        f2 = psi - self.psi0
        ang_q = math.atan2(wp, v)
        ang_t = ang_q - math.atan2(self.L2 * math.sin(psi), self.L1 + self.L2 * math.cos(psi))
        f1 = ang_t - math.atan2(self.t0[2], self.t0[1])
        f1 = (f1 + math.pi) % (2 * math.pi) - math.pi
        return (a, f1, f2), ok


class Body:
    def __init__(self, head):
        self.head = Vector(head)

    def matrix(self, root, loc, pitch, roll):
        """4x4 world matrix taking rest-world coords of body-attached points to posed world."""
        rotation = Ry(roll) @ Rx(pitch)
        m = np.eye(4)
        m[:3,:3] = rotation
        m[:3,3] = Vector(root) + self.head + Vector(loc) - rotation @ self.head
        return m


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Gaits:
    def __init__(self, spec):
        self.spec = spec
        geo = spec["geometry"]
        self.legs = {n: Leg(n, spec["legs"][n], geo) for n in LEGS}
        self.body = Body(spec["body_head"])
        self.r = geo["foot_r"]
        self.z_hip0 = spec["body_head"][2]

    # neutral foot centre (rest-world xy) under each hip
    def neutral(self, n, dy=0.0):
        L = self.legs[n]
        return Vector((L.H[0], L.H[1] + dy, self.r))

    def solve(self, frames):
        """frames: list of dict(root, loc, pitch, roll, feet{n: world foot centre}) -> per-frame joint angles.
        Contact feet roll without slipping: the foot centre is shifted by r * (foot rotation increment), iterated."""
        out = []
        for fr in frames:
            M = self.body.matrix(fr["root"], fr["loc"], fr["pitch"], fr["roll"])
            Mi = np.linalg.inv(M)
            ang, Rw, reach = {}, {}, True
            for n, L in self.legs.items():
                p = Mi[:3,:3] @ fr["feet"][n] + Mi[:3,3]
                q, ok = L.ik_local(p)
                reach &= ok
                ang[n] = q
                Rw[n] = M[:3,:3] @ L.fk_local(*q)[2]
            out.append({"ang": ang, "Rw": Rw, "M": M, "reach": reach})
        return out

    # ------------------------------------------------------------------ gaits
    def trot(self, p, cycles=1, root_motion=False, fps=30):
        """Trot. p: step_length (world stride per cycle, m), step_height, body_height (hip height), speed (m/s),
        duty (stance fraction), pitch_deg, roll_deg, bob (m). Period T = step_length / speed."""
        T = p["step_length"] / p["speed"]
        nf = round(T * fps)
        T = nf / fps  # snap to whole frames so the loop closes exactly
        v = p["step_length"] / T
        duty = p["duty"]
        stroke = v * duty * T
        frames, contact = [], []
        N = nf * cycles
        # foot plans: stance foot world y fixed at root_y(t_td) + y_n - stroke/2
        for i in range(N + 1):
            t = i / fps
            ph = (t / T) % 1.0
            ry = -v * t
            fr = {"root": (0, ry if root_motion else 0, 0),
                  "loc": (0, 0, p["body_height"] - self.z_hip0 - p["bob"] * 0.5 * (1 - math.cos(4 * math.pi * ph))),
                  "pitch": math.radians(p["pitch_deg"]) * math.sin(4 * math.pi * ph),
                  "roll": math.radians(p["roll_deg"]) * math.sin(2 * math.pi * ph), "feet": {}}
            ct = {}
            for n in LEGS:
                lp = (ph - DIAG[n]) % 1.0
                k = math.floor(t / T - DIAG[n])
                t_td = (k + DIAG[n]) * T  # touch-down time of the current cycle for this leg
                nb = self.neutral(n)
                y_td = -v * t_td + nb[1] - stroke / 2
                if lp < duty:
                    pos = Vector((nb[0], y_td, self.r))
                    ct[n] = True
                else:
                    sw = (lp - duty) / (1 - duty)
                    y_lo = y_td  # lift-off point (stance drift added later)
                    y_next = -v * (t_td + T) + nb[1] - stroke / 2
                    c = sw - math.sin(2 * math.pi * sw) / (2 * math.pi)
                    pos = Vector((nb[0], y_lo + (y_next - y_lo) * c, self.r + p["step_height"] * 0.5 * (1 - math.cos(2 * math.pi * sw))))
                    ct[n] = False
                if not root_motion:
                    pos[1] -= ry
                fr["feet"][n] = pos
            frames.append(fr)
            contact.append(ct)
        return frames, contact, nf

    def idle(self, p, fps=30, seconds=4.0):
        nf = round(seconds * fps)
        frames, contact = [], []
        for i in range(nf + 1):
            x = 2 * math.pi * i / nf
            frames.append({"root": (0, 0, 0),
                           "loc": (0.014 * math.sin(x), 0.006 * math.sin(2 * x), p["body_height"] - self.z_hip0 - 0.004 * (1 - math.cos(2 * x)) * 0.5),
                           "pitch": math.radians(0.8) * math.sin(2 * x + 0.6), "roll": math.radians(1.6) * math.sin(x),
                           "feet": {n: self.neutral(n) for n in LEGS}})
            contact.append({n: True for n in LEGS})
        return frames, contact, nf

    def sit_pose(self, p):
        return {"loc": (0, p.get("sit_dy", 0.03), p.get("sit_z", 0.25) - self.z_hip0), "pitch": math.radians(p.get("sit_pitch_deg", -22.0)), "roll": 0.0}

    def sit(self, p, fps=30, seconds=1.6, reverse=False):
        nf = round(seconds * fps)
        sp = self.sit_pose(p)
        st = {"loc": (0, 0, p["body_height"] - self.z_hip0), "pitch": 0.0, "roll": 0.0}
        frames, contact = [], []
        for i in range(nf + 1):
            k = smooth(i / nf)
            if reverse:
                k = 1 - k
            lerp = lambda a, b: a + (b - a) * k
            frames.append({"root": (0, 0, 0), "loc": tuple(lerp(a, b) for a, b in zip(st["loc"], sp["loc"])),
                           "pitch": lerp(st["pitch"], sp["pitch"]), "roll": 0.0,
                           "feet": {n: self.neutral(n, p.get("sit_hind_foot_dy", -0.02) * k if n[0] == "H" else 0.0) for n in LEGS}})
            contact.append({n: True for n in LEGS})
        # hind feet slide forward slightly as the robot sits: mark the move as a (tiny) re-placement, not contact,
        # only if it is non-zero; keep contact so rolling compensation still applies.
        return frames, contact, nf


def trot_with_drift(g, p, cycles, root_motion, fps=30):
    """Trot with rolling contact: stance drift carried into the following swing so lift-off is continuous."""
    frames, contact, nf = g.trot(p, cycles + 2, root_motion, fps)  # 1 cycle of warm-up each side
    base = [{n: fr["feet"][n].copy() for n in LEGS} for fr in frames]
    sol = g.solve(frames)
    for _ in range(3):
        drift = {n: Vector((0, 0, 0)) for n in LEGS}
        last = {n: Vector((0, 0, 0)) for n in LEGS}
        offs = [{} for _ in frames]
        for i in range(len(frames)):
            for n in LEGS:
                if contact[i][n]:
                    if i > 0 and contact[i - 1][n]:
                        dR = sol[i]["Rw"][n] @ sol[i - 1]["Rw"][n].T
                        w = rotation_vector(dR)

                        drift[n] = drift[n] + Vector((g.r * w[1], -g.r * w[0], 0))
                    else:
                        drift[n] = Vector((0, 0, 0))
                    last[n] = drift[n].copy()
                    offs[i][n] = drift[n].copy()
                else:
                    offs[i][n] = None
        # swing: fade the last stance drift to zero over the swing
        for n in LEGS:
            i = 0
            while i < len(frames):
                if not contact[i][n]:
                    j = i
                    while j < len(frames) and not contact[j][n]:
                        j += 1
                    d0 = offs[i - 1][n] if i > 0 and offs[i - 1][n] is not None else Vector((0, 0, 0))
                    for k in range(i, j):
                        sw = (k - i + 1) / (j - i + 1)
                        c = sw - math.sin(2 * math.pi * sw) / (2 * math.pi)
                        offs[k][n] = d0 * (1 - c)
                    i = j
                else:
                    i += 1
        for i, fr in enumerate(frames):
            for n in LEGS:
                fr["feet"][n] = base[i][n] + offs[i][n]
        sol = g.solve(frames)
    # drop the warm-up cycle at the start and the spare at the end
    a, b = nf, nf * (cycles + 1) + 1
    frames, contact, sol = frames[a:b], contact[a:b], sol[a:b]
    if root_motion:
        y0 = frames[0]["root"][1]
        for fr in frames:
            fr["root"] = (0, fr["root"][1] - y0, 0)
            for n in LEGS:
                fr["feet"][n][1] -= y0
        sol = g.solve(frames)
    return frames, contact, sol, nf


def planted_with_rolling(g, frames, contact):
    """All-feet-planted actions (idle/sit/stand): rolling-contact drift accumulates over the whole action."""
    base = [{n: fr["feet"][n].copy() for n in LEGS} for fr in frames]
    sol = g.solve(frames)
    for _ in range(3):
        drift = {n: Vector((0, 0, 0)) for n in LEGS}
        for i, fr in enumerate(frames):
            for n in LEGS:
                if i > 0:
                    dR = sol[i]["Rw"][n] @ sol[i - 1]["Rw"][n].T
                    w = rotation_vector(dR)

                    drift[n] = drift[n] + Vector((g.r * w[1], -g.r * w[0], 0))
                fr["feet"][n] = base[i][n] + drift[n]
        sol = g.solve(frames)
    return sol


DEFAULTS = {"step_length": 0.24, "step_height": 0.07, "body_height": 0.32, "speed": 0.40, "duty": 0.55,
            "pitch_deg": 1.2, "roll_deg": 1.5, "bob": 0.006, "fps": 30, "forward_cycles": 4,
            "sit_z": 0.235, "sit_pitch_deg": -25.0, "sit_dy": 0.04, "sit_hind_foot_dy": 0.0}


def build_all(spec, p):
    """-> {action_name: (frames, contact, sol)}"""
    g = Gaits(spec)
    fps = p["fps"]
    acts = {}
    fr, ct, sol, nf = trot_with_drift(g, p, 1, False, fps)
    acts["trot"] = (fr, ct, sol)
    fr, ct, sol, nf = trot_with_drift(g, p, p["forward_cycles"], True, fps)
    acts["trot_forward"] = (fr, ct, sol)
    fr, ct, nf = g.idle(p, fps)
    acts["idle"] = (fr, ct, planted_with_rolling(g, fr, ct))
    fr, ct, nf = g.sit(p, fps)
    acts["sit"] = (fr, ct, planted_with_rolling(g, fr, ct))
    # stand-up = sit played backwards: rolling contact is reversible, so it stays slip-free and starts exactly
    # where sit ends (re-solving the reverse path would accumulate a different rolling drift)
    acts["stand"] = tuple(list(reversed(x)) for x in acts["sit"])
    return g, acts
