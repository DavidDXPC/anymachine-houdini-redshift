"""Re-import the exported GLB and re-measure it independently of the .blend: actions, extras, foot targets, foot slip.

blender -b --factory-startup --python verify_glb.py -- out/spider.glb out/verify_glb.json
Feet are tracked as the centroid of each tibia mesh's foot-ball vertices (not bone tails: the importer re-orients bones).
"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spider_lib as SL

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
P = json.loads(arm["anymachine_params"])
hwj = json.loads(arm["anymachine_chassis_hw"])
spec = json.loads(arm["anymachine"])
L = SL.layout(P, lambda y: float(np.interp(y, hwj["y"], hwj["hw"])))
res = {"objects": len(bpy.data.objects), "meshes": sorted(o.name for o in bpy.data.objects if o.type == "MESH"),
       "bones": len(arm.data.bones), "actions": {a.name: list(a.frame_range) for a in bpy.data.actions},
       "extras_keys": sorted(arm.keys()), "spec_chains": len(spec["chains"])}

# foot-ball vertex sets in the rest pose (imported scene starts at rest)
arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
balls = {}
for leg in SL.LEGS:
    ob = bpy.data.objects[f"tibia_{leg}"]
    F = Vector(L[leg]["foot_rest"])
    idx = [v.index for v in ob.data.vertices if abs(((ob.matrix_world @ v.co) - F).length - P["foot_r"]) < 1e-4]  # on the ball surface
    balls[leg] = (ob, idx)
res["foot_ball_verts"] = {k: len(v[1]) for k, v in balls.items()}


def feet():
    out = {}
    for leg, (ob, idx) in balls.items():
        M = ob.matrix_world
        out[leg] = sum((M @ ob.data.vertices[i].co for i in idx), Vector()) / len(idx)
    return out


rest_err = max((feet()[leg] - Vector(L[leg]["foot_rest"])).length for leg in SL.LEGS)
res["rest_foot_err_mm"] = round(rest_err * 1000, 4)


def act_named(n):
    return next(a for a in bpy.data.actions if a.name == n or a.name.startswith(n + "_") or a.name.startswith(n))


for name, sub in (("walk", 0.5), ("idle", 1.0), ("crouch", 1.0)):
    a = act_named(name)
    arm.animation_data.action = a
    if a.slots:
        arm.animation_data.action_slot = a.slots[0]
    f0, f1 = a.frame_range
    hist = {leg: [] for leg in SL.LEGS}
    err = 0.0
    f = f0
    while f <= f1 + 1e-9:
        sc.frame_set(int(f), subframe=f - int(f))
        bpy.context.view_layer.update()
        t = (f - f0) / P["fps"]
        st = SL.walk_state(P, L, t) if name == "walk" else (SL.idle_state(P, L, t) if name == "idle" else SL.crouch_state(P, L, t))
        ft = feet()
        for leg in SL.LEGS:
            err = max(err, (ft[leg] - Vector(st["feet"][leg])).length)
            hist[leg].append((st["stance"][leg], ft[leg].copy()))
        f += sub
    slip = 0.0
    for leg, h in hist.items():
        r0 = None
        for s, p in h:
            if s:
                r0 = p if r0 is None else r0
                slip = max(slip, (p - r0).length)
            else:
                r0 = None
    res[name] = {"frames": [f0, f1], "sample_step": sub, "max_foot_target_err_mm": round(err * 1000, 3),
                 "max_foot_slip_mm": round(slip * 1000, 3)}
json.dump(res, open(OUT, "w"), indent=1)
print("VERIFY", json.dumps(res), flush=True)
