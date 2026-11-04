"""Re-import an exported bag GLB and confirm: nodes, skins, morph targets, animations; each <ctl>_param action poses
the rig differently at t=0 and t=1 and matches the baked .blend pose at t=0.5 (vertex error).
blender -b --python verify_glb.py -- <glb> <baked.blend> <out.json>"""
import bpy, sys, os, json
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, BAKED, OUT = [os.path.abspath(a) for a in argv[:3]]


def snap(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in sorted(objs, key=lambda o: o.name):
        oe = o.evaluated_get(dg)
        m = oe.to_mesh()
        pts += [oe.matrix_world @ v.co for v in m.vertices]
        oe.to_mesh_clear()
    return pts


def pose_all(act_name, frame):
    for o in bpy.data.objects:
        for idb in (o, getattr(o.data, "shape_keys", None) if o.type == "MESH" else None):
            if idb is None or not idb.animation_data:
                continue
            ad = idb.animation_data
            for t in ad.nla_tracks:
                t.mute = True
            hit = [a for a in bpy.data.actions if a.name.split(".")[0] == act_name or a.name.startswith(act_name + "_")]
            ad.action = None
    sc = bpy.context.scene
    for o in bpy.data.objects:
        for idb in (o, getattr(o.data, "shape_keys", None) if o.type == "MESH" else None):
            if idb is None or not idb.animation_data:
                continue
            for t in idb.animation_data.nla_tracks:
                t.mute = t.name != act_name
    sc.frame_set(frame)
    bpy.context.view_layer.update()


# reference poses from the baked .blend
bpy.ops.wm.open_mainfile(filepath=BAKED)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
ctls = [c["param"] for c in json.loads(arm["anymachine"])["controls"]]
ref = {}
meshes = lambda: [o for o in bpy.data.objects if o.type == "MESH"]
for c in ctls:
    for f in (1, 13, 25):
        pose_all(f"{c}_param", f)
        ref[(c, f)] = snap(meshes())
pose_all("demo", 60)
ref[("demo", 60)] = snap(meshes())

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
res = {"glb": GLB, "size_kb": os.path.getsize(GLB) // 1024,
       "objects": sorted((o.name, o.type) for o in bpy.data.objects),
       "actions": sorted(a.name for a in bpy.data.actions),
       "morph_targets": {o.name: [k.name for k in o.data.shape_keys.key_blocks] for o in meshes() if o.data.shape_keys}}
garm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
res["extras_keys"] = list(garm.keys())
res["tracks"] = {}
for o in bpy.data.objects:
    for idb in (o, getattr(o.data, "shape_keys", None) if o.type == "MESH" else None):
        if idb is not None and idb.animation_data:
            res["tracks"][idb.name] = [t.name for t in idb.animation_data.nla_tracks]
# the importer puts each glTF animation on an NLA track named after it
err = {}
for (c, f), R in ref.items():
    name = f"{c}_param" if c != "demo" else "demo"
    pose_all(name, f)
    G = snap(meshes())
    from mathutils.kdtree import KDTree
    kd = KDTree(len(R))
    for i, r in enumerate(R):
        kd.insert(r, i)
    kd.balance()
    e = sorted(kd.find(g)[2] for g in G)
    err[f"{name}@{f}"] = {"median_mm": round(e[len(e) // 2] * 1000, 3), "p99_mm": round(e[int(len(e) * 0.99)] * 1000, 3), "max_mm": round(e[-1] * 1000, 3)}
res["pose_match"] = err
moves = {}
for c in ctls:
    pose_all(f"{c}_param", 1)
    A = snap(meshes())
    pose_all(f"{c}_param", 25)
    B = snap(meshes())
    moves[c] = round(max((a - b).length for a, b in zip(A, B)) * 1000, 1)
res["param_action_max_motion_mm"] = moves
json.dump(res, open(OUT, "w"), indent=1)
print("VERIFIED", json.dumps({k: v for k, v in res.items() if k != "objects"})[:3000], flush=True)
