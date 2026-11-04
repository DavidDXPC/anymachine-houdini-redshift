"""AnyMachine spider: bake procedural motions into linear FK actions on the rig (bpy side of spider_lib).

Every key is a plain FK channel (root/body loc+rot, coxa Z, femur X, tibia X) plus the IK foot-target bone locations, so
glTF consumers need no drivers or solvers. Also embedded in the .blend as a text block: change the rig's custom props
(step_length, step_height, body_height, speed, duty) and run `spider_rebake.py` to regenerate the walk.
"""
import bpy, math
import spider_lib as SL


def _set_pose(arm, P, L, st, sol):
    pbs = arm.pose.bones
    pbs["root"].location = st["root"]
    pbs["body"].location = st["body_loc"]
    pbs["body"].rotation_euler = st["body_rot"]
    for leg in SL.LEGS:
        q = sol[leg]["q"]
        pbs[f"coxa_{leg}"].rotation_euler = (0, 0, q[0])
        pbs[f"femur_{leg}"].rotation_euler = (q[1], 0, 0)
        pbs[f"tibia_{leg}"].rotation_euler = (q[2], 0, 0)
        F, R = st["feet"][leg], L[leg]["foot_rest"]
        # ik bones: parent = root, rest axes = world axes, so local location = world offset from rest - root motion
        pbs[f"ik_{leg}"].location = (F[0] - R[0] - st["root"][0], F[1] - R[1] - st["root"][1], F[2] - R[2] - st["root"][2])


def _key(arm, f):
    pbs = arm.pose.bones
    pbs["root"].keyframe_insert("location", frame=f, group="root")
    pbs["body"].keyframe_insert("location", frame=f, group="body")
    pbs["body"].keyframe_insert("rotation_euler", frame=f, group="body")
    for leg in SL.LEGS:
        pbs[f"coxa_{leg}"].keyframe_insert("rotation_euler", index=2, frame=f, group=leg)
        pbs[f"femur_{leg}"].keyframe_insert("rotation_euler", index=0, frame=f, group=leg)
        pbs[f"tibia_{leg}"].keyframe_insert("rotation_euler", index=0, frame=f, group=leg)
        pbs[f"ik_{leg}"].keyframe_insert("location", frame=f, group=leg)


def states(P, L, motion, n_cycles=1):
    """[(frame, state, solution)] for walk | walk_demo | idle | crouch."""
    fps = P["fps"]
    out = []
    if motion in ("walk", "walk_demo"):
        nf = SL.frames_per_cycle(P) * (n_cycles if motion == "walk_demo" else 1)
        for i in range(nf + 1):
            st = SL.walk_state(P, L, i / fps)
            out.append((1 + i, st))
    elif motion == "idle":
        nf = int(round(3.0 * fps))
        for i in range(nf + 1):
            out.append((1 + i, SL.idle_state(P, L, i / fps)))
    elif motion == "crouch":
        for i in range(fps + 1):            # 1 s, linear: seek t = crouch amount
            out.append((1 + i, SL.crouch_state(P, L, i / fps)))
    return [(f, st, SL.solve_state(P, L, st)) for f, st in out]


def bake(arm, P, L, name, motion, n_cycles=1, nla=True):
    old = bpy.data.actions.get(name)
    if old:
        if arm.animation_data:
            for t in list(arm.animation_data.nla_tracks):
                if t.name == name:
                    arm.animation_data.nla_tracks.remove(t)
        bpy.data.actions.remove(old)
    prefs = bpy.context.preferences.edit
    prev = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = "LINEAR"
    arm.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    seq = states(P, L, motion, n_cycles)
    for f, st, sol in seq:
        _set_pose(arm, P, L, st, sol)
        _key(arm, f)
    prefs.keyframe_new_interpolation_type = prev
    act.frame_range = (seq[0][0], seq[-1][0])
    act["anymachine_motion"] = motion
    if nla:
        trk = arm.animation_data.nla_tracks.new()
        trk.name = name
        trk.strips.new(name, int(seq[0][0]), act)
        trk.mute = True
    arm.animation_data.action = None
    return act, seq


def rest_pose(arm):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
