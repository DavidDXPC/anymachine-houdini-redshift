"""Shoulder straps with a strap_length control (shared by the daypack and roll-top; the rucksack has its own copy).
Padded strap (fixed length) from a top anchor, adjuster, webbing to a bottom anchor (stretches), free tail (jiggle)."""
import math
from mathutils import Vector, Matrix
from softlib import *
from rig_parts import *

X = Vector((1, 0, 0))


class ShoulderStraps:
    def __init__(self, top, bottom, lp=0.46, npad=9, web=(0.06, 0.20), web_tot=0.32, s_def=0.4, bulge=(0.9, 1.0),
                 lift=(0.05, 0.15)):
        """top/bottom: callables sx -> Vector anchor (sx = +1 for .L (+X), -1 for .R)."""
        self.top, self.bottom, self.LP, self.N = top, bottom, lp, npad
        self.web, self.WT, self.S_DEF, self.bulge, self.lift = web, web_tot, s_def, bulge, lift
        self.rest = {}

    def path(self, sx, s):
        A, C = self.top(sx), self.bottom(sx)
        Lw = lerp(self.web[0], self.web[1], s)

        def curve(beta):
            c1 = A + Vector((sx * 0.01, beta * self.bulge[0], self.lift[0]))
            c2 = C + Vector((sx * 0.01, beta * self.bulge[1], self.lift[1]))
            return [A * (1 - t) ** 3 + c1 * 3 * t * (1 - t) ** 2 + c2 * 3 * t * t * (1 - t) + C * t ** 3
                    for t in (i / 160 for i in range(161))]

        L = lambda pts: sum((b - a).length for a, b in zip(pts, pts[1:]))
        lo, hi = 0.0, 0.8
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if L(curve(mid)) < self.LP + Lw else (lo, mid)
        return curve((lo + hi) / 2), Lw

    @staticmethod
    def split(pts, at):
        acc = 0.0
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            seg = (b - a).length
            if acc + seg >= at:
                q = a.lerp(b, (at - acc) / seg)
                return pts[:i + 1] + [q], [q] + pts[i + 1:]
            acc += seg
        return pts, [pts[-1]]

    @staticmethod
    def ups(pts):
        out = []
        for i in range(len(pts)):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            out.append(t.cross(X).normalized())
        if out[0].y < 0:
            out = [-u for u in out]
        for i in range(1, len(out)):
            if out[i].dot(out[i - 1]) < 0:
                out[i] = -out[i]
        return out

    def padpts(self, sx, s):
        pts, Lw = self.path(sx, s)
        pad, web = self.split(pts, self.LP)
        pp = resample(pad, self.LP / self.N)[:self.N + 1]
        pp[-1] = pad[-1]
        return pp, web[-1], Lw

    def add_bones(self, B, parent="root"):
        for side, sx in (("L", 1), ("R", -1)):
            pp, wend, Lw = self.padpts(sx, self.S_DEF)
            u = self.ups(pp)
            names = B.chain(f"sh.{side}_", pp, parent=parent, ups=u)
            B.add(f"web.{side}", pp[-1], wend, names[-1], up=u[-1])
            tl = self.WT - Lw
            tail = [pp[-1] + Vector((0, 0.012, 0)) + DOWN * (tl * i / 3) for i in range(4)]
            tn = B.chain(f"tail.{side}_", tail, parent=names[-1], up=Vector((0, 1, 0)))
            self.rest[side] = dict(pad=pp, ups=u, names=names, web=wend, tail=tail, tnames=tn, Lw=Lw)

    def build_meshes(self, arm, pad_m, web_m, plast):
        parts = []
        for side in ("L", "R"):
            r = self.rest[side]
            dense = resample(r["pad"], 0.01)
            wid = [lerp(0.6, 1.0, smoothstep(0.0, 0.12, i / len(dense))) for i in range(len(dense))]
            s_ob, _ = strap_object(f"strap.{side}", dense, self.ups(dense), 0.062, 0.015, pad_m, seg=3, widths=wid)
            skin(s_ob, arm, chain_weights([v.co for v in s_ob.data.vertices], r["pad"], r["names"], falloff=0.45))
            wpts = [r["pad"][-1].lerp(r["web"], t / 6) for t in range(7)]
            w_ob, _ = strap_object(f"webbing.{side}", wpts, [r["ups"][-1]] * 7, 0.025, 0.003, web_m)
            skin(w_ob, arm, {f"web.{side}": [1.0] * len(w_ob.data.vertices)})
            tpts = resample(r["tail"], 0.01)
            t_ob, _ = strap_object(f"tail.{side}", tpts, [Vector((0, 1, 0))] * len(tpts), 0.025, 0.003, web_m)
            skin(t_ob, arm, chain_weights([v.co for v in t_ob.data.vertices], r["tail"], r["tnames"], falloff=0.4))
            d = (r["pad"][-1] - r["pad"][-2]).normalized()
            lk = ladder_lock(f"adjuster.{side}", r["pad"][-1] - d * 0.012, d, r["ups"][-1], material=plast)
            rigid_to_bone(lk, arm, r["names"][-1])
            parts += [s_ob, w_ob, t_ob, lk]
        return parts

    def bones(self):
        return [n for s in ("L", "R") for n in self.rest[s]["names"] + [f"web.{s}", self.rest[s]["tnames"][0]]]

    def pose(self, arm, s):
        out = {}
        for side, sx in (("L", 1), ("R", -1)):
            r = self.rest[side]
            pp, wend, Lw = self.padpts(sx, s)
            o, armm = chain_locals(arm, r["names"], pp, ups=self.ups(pp))
            out.update(o)
            o, _ = chain_locals(arm, [f"web.{side}"], [pp[-1], wend], parent_pose=armm[r["names"][-1]], stretch=True)
            out.update(o)
            k = (self.WT - Lw) / (self.WT - r["Lw"])
            tn = r["tnames"]
            b0 = arm.data.bones[tn[0]]
            M = aim_matrix(b0.matrix_local, pp[-1] + Vector((0, 0.012, 0)), DOWN, k)
            Pm = armm[r["names"][-1]]
            out[tn[0]] = (Pm @ (b0.parent.matrix_local.inverted() @ b0.matrix_local)).inverted() @ M
        return out
