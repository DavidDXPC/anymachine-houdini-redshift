"""Verify the quadruped rig: joint sweeps, random poses, every baked action.

blender -b --factory-startup --python check.py -- --blend out/quadruped.blend --out out/check.json [--random 300]

Per evaluated pose (Blender's own depsgraph, constraints included):
  overlaps   BVH triangle intersections between rigid groups (body, and per leg: haa, thigh, shin)
  clearance  min vertex->surface distance between groups; reported for all pairs and for non-adjacent pairs
             (adjacent = body|haa, haa|thigh, thigh|shin of one leg: their coaxial running gaps are fixed by design)
  limits     evaluated joint angle within its limit; commanded past a limit -> clamped to it
  tracking   evaluated joint angle vs the keyed value; evaluated foot centre vs the gait planner's target
  ground     lowest non-foot point; foot penetration
  slip       during stance (foot centre within --contact-tol, default 0.05 mm, of rolling height): horizontal motion of the material point in
             contact, frame to frame, summed per stance (true slip); plus the contact point's rolling travel
"""
import bpy, sys, os, json, math, random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gait

argv = sys.argv[sys.argv.index("--") + 1:]
opt = lambda k, d=None, c=str: c(argv[argv.index(k) + 1]) if k in argv else d
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(opt("--blend")))
OUT = os.path.abspath(opt("--out"))
NRAND = opt("--random", 300, int)
CONTACT_TOL = opt("--contact-tol", 0.00005, float)  # foot centre within this of rolling height = stance
sc = bpy.context.scene
arm = bpy.data.objects["quadruped_rig"]
spec = json.loads(arm["anymachine"])
lim = spec["geometry"]["limits_rad"]
r_foot = spec["geometry"]["foot_r"]
ad = arm.animation_data
for t in ad.nla_tracks:
    t.mute = True
groups = {}
for o in bpy.data.objects:
    if o.type == "MESH" and "group" in o.keys():
        groups.setdefault(o["group"], []).append(o)
GN = sorted(groups)
ADJ = {frozenset(("body", f"{n}_haa")) for n in gait.LEGS} | {frozenset((f"{n}_haa", f"{n}_thigh")) for n in gait.LEGS} | \
      {frozenset((f"{n}_thigh", f"{n}_shin")) for n in gait.LEGS}
foot_rest = {n: Vector(spec["legs"][n]["foot"]) for n in gait.LEGS}
dg = lambda: bpy.context.evaluated_depsgraph_get()


def group_geo(name):
    verts, polys = [], []
    for o in groups[name]:
        oe = o.evaluated_get(dg())
        m = oe.to_mesh()
        mw = oe.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in m.vertices]
        m.calc_loop_triangles()
        polys += [tuple(off + i for i in t.vertices) for t in m.loop_triangles]
        oe.to_mesh_clear()
    return verts, polys


def snapshot(which=None):
    which = which or GN
    geo = {g: group_geo(g) for g in which}
    return geo, {g: BVHTree.FromPolygons(*geo[g]) for g in which}


def collide(geo, bvh, pairs, clearance=False, stride=3):
    over, clr = {}, {}
    for a, b in pairs:
        h = bvh[a].overlap(bvh[b])
        if h:
            over[f"{a}|{b}"] = len(h)
        if clearance:
            va = geo[a][0] if len(geo[a][0]) < len(geo[b][0]) else geo[b][0]
            tb = bvh[b] if va is geo[a][0] else bvh[a]
            d = min((tb.find_nearest(p)[3] for p in va[::stride]), default=9)
            clr[f"{a}|{b}"] = d
    return over, clr


ALLPAIRS = [(a, b) for i, a in enumerate(GN) for b in GN[i + 1:]]


def leg_pairs(n):
    mine = [g for g in GN if g.startswith(n + "_")]
    return [(a, b) for a in mine for b in GN if b not in mine] + [(a, b) for i, a in enumerate(mine) for b in mine[i + 1:]]


def local_angle(pbn):
    pb = arm.pose.bones[pbn]
    par = pb.parent
    rest_rel = par.bone.matrix_local.inverted() @ pb.bone.matrix_local
    L = (par.matrix @ rest_rel).inverted() @ pb.matrix
    if pbn.endswith("_haa"):
        return math.atan2(L[0][2], L[0][0])
    return math.atan2(L[2][1], L[1][1])


def set_pose(angles=None, body=None):
    ad.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
    if body:
        arm.pose.bones["body"].location = body[0]
        arm.pose.bones["body"].rotation_euler = body[1]
    for k, a in (angles or {}).items():
        pb = arm.pose.bones[k]
        pb.rotation_euler = (0, a, 0) if k.endswith("_haa") else (a, 0, 0)
    vl = bpy.context.view_layer
    arm.update_tag()
    sc.frame_set(1)
    vl.update()


res = {"groups": GN}
D = math.degrees

# ---------------------------------------------------------------- 1. single-joint sweeps (+-6 deg past each limit)
sweeps = {}
STEP = math.radians(2)
for n in gait.LEGS:
    for j in ("haa", "hfe", "kfe"):
        lo, hi = lim[j]
        a = lo - math.radians(6)
        rows = []
        pairs = leg_pairs(n)
        while a <= hi + math.radians(6) + 1e-9:
            set_pose({f"{n}_{j}": a})
            geo, bvh = snapshot()
            over, clr = collide(geo, bvh, pairs, clearance=True, stride=4)
            ev = local_angle(f"{n}_{j}")
            want = max(lo, min(hi, a))
            na = {k: v for k, v in clr.items() if frozenset(k.split("|")) not in ADJ}
            rows.append({"cmd": round(D(a), 1), "eval": round(D(ev), 3), "clamp_err": round(D(abs(ev - want)), 4),
                         "overlaps": over, "min_clear_mm": round(1000 * min(clr.values()), 2),
                         "min_clear_nonadj_mm": round(1000 * min(na.values()), 2) if na else None})
            a += STEP
        sweeps[f"{n}_{j}"] = {"limits_deg": [round(D(lo), 2), round(D(hi), 2)], "steps": len(rows),
                              "overlap_steps": [r["cmd"] for r in rows if r["overlaps"]],
                              "overlap_pairs": sorted({k for r in rows for k in r["overlaps"]}),
                              "max_clamp_err_deg": max(r["clamp_err"] for r in rows),
                              "min_clear_mm": min(r["min_clear_mm"] for r in rows),
                              "min_clear_nonadj_mm": min(r["min_clear_nonadj_mm"] for r in rows if r["min_clear_nonadj_mm"] is not None),
                              "rows": rows}
        print("SWEEP", n, j, {k: v for k, v in sweeps[f'{n}_{j}'].items() if k != "rows"}, flush=True)
res["sweeps"] = sweeps

# ---------------------------------------------------------------- 2. random poses inside the limits (all joints at once)
random.seed(7)
bad, pairs_hit = 0, {}
for i in range(NRAND):
    ang = {f"{n}_{j}": random.uniform(*lim[j]) for n in gait.LEGS for j in ("haa", "hfe", "kfe")}
    set_pose(ang)
    geo, bvh = snapshot()
    over, _ = collide(geo, bvh, ALLPAIRS)
    if over:
        bad += 1
        for k in over:
            kk = "|".join(sorted(x.split("_", 1)[1] if "_" in x else x for x in k.split("|")))
            pairs_hit[kk] = pairs_hit.get(kk, 0) + 1
res["random_poses"] = {"n": NRAND, "with_overlap": bad, "pair_types": pairs_hit}
print("RANDOM", res["random_poses"], flush=True)

# ---------------------------------------------------------------- 3. actions
p = dict(gait.DEFAULTS)
for k in p:
    if k in arm.keys():
        p[k] = arm[k]
_, plan = gait.build_all(spec, p)
acts = {}
for name in ("trot", "trot_forward", "idle", "sit", "stand"):
    act = bpy.data.actions[name]
    nf = int(act.frame_range[1])
    frames, contact, sol = plan[name]
    rows = []
    feet_hist = []
    for f in range(1, nf + 1):
        ad.action = act
        if getattr(ad, "action_slot", None) is None and len(getattr(act, "slots", [])):
            ad.action_slot = act.slots[0]
        sc.frame_set(f)
        bpy.context.view_layer.update()
        geo, bvh = snapshot()
        over, clr = collide(geo, bvh, ALLPAIRS, clearance=True, stride=5)
        na = {k: v for k, v in clr.items() if frozenset(k.split("|")) not in ADJ}
        ev = {f"{n}_{j}": local_angle(f"{n}_{j}") for n in gait.LEGS for j in ("haa", "hfe", "kfe")}
        keyed = sol[f - 1]["ang"]
        trk = max(abs(ev[f"{n}_{j}"] - keyed[n][i]) for n in gait.LEGS for i, j in enumerate(("haa", "hfe", "kfe")))
        lim_ok = all(lim[k.split("_")[1]][0] - 1e-5 <= v <= lim[k.split("_")[1]][1] + 1e-5 for k, v in ev.items())
        fm = {n: bpy.data.objects[f"{n}_foot"].matrix_world.copy() for n in gait.LEGS}
        fc = {n: fm[n] @ foot_rest[n] for n in gait.LEGS}
        if name == "trot":  # in-place clip: compare against the planner in the body-relative frame
            ft_err = max((fc[n] - frames[f - 1]["feet"][n]).length for n in gait.LEGS)
        else:
            ft_err = max((fc[n] - (frames[f - 1]["feet"][n] + Vector(arm.location))).length for n in gait.LEGS)
        nonfoot_min = min(v.z for g in GN for v in geo[g][0] if not g.endswith("_shin")) if True else 0
        shin_min = min(v.z for n in gait.LEGS for o in groups[f"{n}_shin"] if not o.name.endswith("_foot")
                       for v in [o.matrix_world @ vv.co for vv in list(o.data.vertices)[::7]])
        foot_min = min(fc[n].z - r_foot for n in gait.LEGS)
        feet_hist.append((fm, fc))
        rows.append({"f": f, "overlaps": over, "min_clear_mm": round(1000 * min(clr.values()), 2),
                     "min_clear_nonadj_mm": round(1000 * min(na.values()), 2), "track_err_deg": round(D(trk), 5),
                     "limits_ok": lim_ok, "foot_target_err_mm": round(1000 * ft_err, 3),
                     "lowest_nonfoot_mm": round(1000 * min(nonfoot_min, shin_min), 1), "foot_penetration_mm": round(-1000 * min(0, foot_min), 3)})
    # slip (world-moving clips only; the in-place trot is a treadmill by construction)
    slip = None
    if name != "trot":
        per_stance, per_frame_max, roll_travel = {n: [] for n in gait.LEGS}, 0.0, {n: [] for n in gait.LEGS}
        for n in gait.LEGS:
            acc, rt, run = 0.0, 0.0, 0
            for i in range(len(feet_hist) - 1):
                (m0, c0), (m1, c1) = feet_hist[i], feet_hist[i + 1]
                st0 = c0[n].z < r_foot + CONTACT_TOL
                st1 = c1[n].z < r_foot + CONTACT_TOL
                if st0 and st1:
                    pc = c0[n] - Vector((0, 0, r_foot))
                    q = m0[n].inverted() @ pc
                    d = (m1[n] @ q) - pc
                    s_ = math.hypot(d.x, d.y)
                    acc += s_
                    per_frame_max = max(per_frame_max, s_)
                    rt += math.hypot(c1[n].x - c0[n].x, c1[n].y - c0[n].y)
                    run += 1
                elif run:
                    per_stance[n].append(acc)
                    roll_travel[n].append(rt)
                    acc, rt, run = 0.0, 0.0, 0
            if run:
                per_stance[n].append(acc)
                roll_travel[n].append(rt)
        allst = [x for v in per_stance.values() for x in v]
        slip = {"stances": len(allst), "max_slip_per_stance_mm": round(1000 * max(allst), 3) if allst else None,
                "mean_slip_per_stance_mm": round(1000 * sum(allst) / len(allst), 3) if allst else None,
                "max_slip_per_frame_mm": round(1000 * per_frame_max, 3),
                "rolling_travel_per_stance_mm": round(1000 * max(x for v in roll_travel.values() for x in v), 2) if allst else None}
    acts[name] = {"frames": nf, "frames_with_overlap": sum(1 for r in rows if r["overlaps"]),
                  "overlap_pairs": sorted({k for r in rows for k in r["overlaps"]}),
                  "min_clear_mm": min(r["min_clear_mm"] for r in rows), "min_clear_nonadj_mm": min(r["min_clear_nonadj_mm"] for r in rows),
                  "max_track_err_deg": max(r["track_err_deg"] for r in rows), "limits_ok": all(r["limits_ok"] for r in rows),
                  "max_foot_target_err_mm": max(r["foot_target_err_mm"] for r in rows),
                  "lowest_nonfoot_mm": min(r["lowest_nonfoot_mm"] for r in rows),
                  "max_foot_penetration_mm": max(r["foot_penetration_mm"] for r in rows), "slip": slip, "rows": rows}
    print("ACTION", name, {k: v for k, v in acts[name].items() if k != "rows"}, flush=True)
res["actions"] = acts

# joint usage per action (deg) vs limits
use = {}
for name, (frames, contact, sol) in plan.items():
    use[name] = {j: [round(D(min(s_["ang"][n][i] for s_ in sol for n in gait.LEGS)), 1),
                     round(D(max(s_["ang"][n][i] for s_ in sol for n in gait.LEGS)), 1)] for i, j in enumerate(("haa", "hfe", "kfe"))}
res["joint_usage_deg"] = use

S = res["summary"] = {
    "sweep_overlap_joints": {k: v["overlap_steps"] for k, v in sweeps.items() if v["overlap_steps"]},
    "sweep_max_clamp_err_deg": max(v["max_clamp_err_deg"] for v in sweeps.values()),
    "sweep_min_clear_nonadj_mm": min(v["min_clear_nonadj_mm"] for v in sweeps.values()),
    "random_poses_with_overlap": f"{bad}/{NRAND}",
    "actions": {k: {kk: vv for kk, vv in v.items() if kk not in ("rows", "overlap_pairs")} for k, v in acts.items()},
}
json.dump(res, open(OUT, "w"), indent=1)
print("CHECK", json.dumps(S), flush=True)
