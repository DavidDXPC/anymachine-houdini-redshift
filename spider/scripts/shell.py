"""Generated spider GLB -> normalised body SHELL (legs stripped) + measurements of the generated pose.

blender -b --factory-startup --python shell.py -- --glb gen/meshy/model.glb --gen meshy --out gen/shell_meshy.blend \
    [--body-len 0.40] [--png gen/shell_meshy.png]

Steps
1. Orient: forward = -Y, Z up, ground (lowest foot) at z = 0.
2. Top-down occupancy grid of face centroids (area weighted); a morphological OPENING with a disc larger than a leg
   is wide but smaller than the body removes the legs and keeps the body blob. Largest component = body footprint.
3. Keep faces whose centroid lies in the (slightly eroded) footprint and above the belly cut -> shell.
4. Measure the generated pose: feet (ground-contact clusters), knee heights per leg cluster, body height and outline.
5. Scale uniformly so the shell is --body-len long (Y). Everything measured is reported in the scaled frame.
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]


def opt(k, d=None, cast=str):
    return cast(argv[argv.index(k) + 1]) if k in argv else d


GLB, GEN, OUT = opt("--glb"), opt("--gen"), os.path.abspath(opt("--out"))
BODY_LEN = opt("--body-len", 0.40, float)
PNG = opt("--png")
MIRROR = opt("--mirror")  # left | right | None

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(GLB))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if GEN.startswith("tripo"):
    for o in bpy.context.scene.objects:
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
for o in meshes:
    mw = o.matrix_world.copy()
    o.parent = None
    o.data.transform(mw)
    o.matrix_world = Matrix.Identity(4)
for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
    bpy.data.objects.remove(o)
vl = bpy.context.view_layer
for o in meshes:
    o.select_set(True)
vl.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
gen = vl.objects.active
gen.name = "shell"
me = gen.data
# head direction differs per generator (checked on the inspect renders): make forward = -Y
rot = {"meshy": 0, "tripo": 90}.get(GEN.split("-")[0], 0)  # checked on a tilted top view (a straight-down camera has no defined "up")
me.transform(Matrix.Rotation(math.radians(rot), 4, "Z"))

V = np.array([v.co[:] for v in me.vertices])
lo, hi = V.min(0), V.max(0)
me.transform(Matrix.Translation(Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))))
V = np.array([v.co[:] for v in me.vertices])
span = V.max(0) - V.min(0)

# ---------------------------------------------------------------- top-down occupancy -> body footprint
me.calc_loop_triangles()
P = np.array([p.center[:] for p in me.polygons])
A = np.array([p.area for p in me.polygons])
cell = span[:2].max() / 200.0
gx = ((P[:, 0] - V[:, 0].min()) / cell).astype(int)
gy = ((P[:, 1] - V[:, 1].min()) / cell).astype(int)
W, H = gx.max() + 1, gy.max() + 1
occ = np.zeros((W, H), bool)
occ[gx, gy] = True


def disc(r):
    k = int(math.ceil(r))
    return [(i, j) for i in range(-k, k + 1) for j in range(-k, k + 1) if i * i + j * j <= r * r]


def shift_and(m, offs, fn):
    out = np.ones_like(m) if fn == "and" else np.zeros_like(m)
    for i, j in offs:
        s = np.zeros_like(m)
        xs0, xs1 = max(0, i), W + min(0, i)
        ys0, ys1 = max(0, j), H + min(0, j)
        s[xs0:xs1, ys0:ys1] = m[xs0 - i:xs1 - i, ys0 - j:ys1 - j]
        out = (out & s) if fn == "and" else (out | s)
    return out


# fill pin-holes first (closing), then open with a disc wider than a leg
occ = shift_and(shift_and(occ, disc(2), "or"), disc(2), "and")
# body width is ~20% of the span in both generations, legs ~4%: radius 6% of span strips legs, keeps the body
R = 0.055 * span[:2].max() / cell
body = shift_and(shift_and(occ, disc(R), "and"), disc(R), "or")
# largest connected component
lab = np.zeros_like(body, int)
best, bestn, n = 0, 0, 0
for i in range(W):
    for j in range(H):
        if body[i, j] and not lab[i, j]:
            n += 1
            st, cnt = [(i, j)], 0
            lab[i, j] = n
            while st:
                a, b = st.pop()
                cnt += 1
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < W and 0 <= y < H and body[x, y] and not lab[x, y]:
                        lab[x, y] = n
                        st.append((x, y))
            if cnt > bestn:
                best, bestn = n, cnt
body = lab == best
# erode 1.5 cells so hip actuator stubs at the rim are dropped
body_in = shift_and(body, disc(1.5), "and")
keep_fp = body_in[gx, gy]
NZ = np.array([p.normal.z for p in me.polygons])
# TOP SKIN only (experiment-1 rule: keep the generator's surface where it is good, rebuild the rest). The side walls are
# fused with hip actuators and leg roots, so keep up-facing faces in the upper part of the footprint; a clean chassis is
# lofted underneath in build.py.
zin = P[keep_fp, 2]
z_lo_fp, z_hi_fp = np.percentile(zin, 3), zin.max()
zcut = z_lo_fp + 0.45 * (z_hi_fp - z_lo_fp)
cand = keep_fp & (P[:, 2] > zcut)
# generator winding is not consistent (Meshy), so "up-facing" = visible from the upper hemisphere: ray-cast from 5
# directions (straight down + 4 at 40 deg) towards each candidate centroid; keep it if the first hit is that face
from mathutils.bvhtree import BVHTree
bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
dirs = [Vector((0, 0, -1))] + [Vector((math.cos(a) * 0.64, math.sin(a) * 0.64, -0.77)) for a in (0, 1.57, 3.14, 4.71)]
keep = np.zeros(len(P), bool)
for i in np.nonzero(cand)[0]:
    c = Vector(P[i])
    for d in dirs:
        o = c - d * 0.5 * span.max()
        loc, nrm, idx, dist = bvh.ray_cast(o, d)
        if idx is not None and (idx == i or (loc - c).length < 0.002 * span.max()):
            keep[i] = True
            break
# also report (for the footprint, not just skin) the scale reference
Vfp = P[keep_fp]

# ---------------------------------------------------------------- measure the generated pose (before deleting legs)
legs = ~body[gx, gy]
feet_v = V[V[:, 2] < 0.03 * span[2]]
# cluster foot vertices in xy (greedy, radius 4% of span)
feet = []
for p in feet_v:
    for f in feet:
        if np.hypot(*(p[:2] - f["c"])) < 0.04 * span[:2].max():
            f["pts"].append(p)
            f["c"] = np.mean(f["pts"], 0)[:2]
            break
    else:
        feet.append({"c": p[:2].copy(), "pts": [p]})
feet = [f for f in feet if len(f["pts"]) > 10]
fpl, fph = Vfp.min(0), Vfp.max(0)
s = BODY_LEN / (fph[1] - fpl[1])
cx, cy = (fpl[0] + fph[0]) / 2, (fpl[1] + fph[1]) / 2
# leg clusters: faces outside the footprint, assigned to the nearest foot by azimuth -> knee (highest point) + hip radius
legmeas = []
LP = P[legs]
az = np.arctan2(LP[:, 1] - cy, LP[:, 0] - cx)
for f in feet:
    fa = math.atan2(f["c"][1] - cy, f["c"][0] - cx)
    d = np.abs((az - fa + np.pi) % (2 * np.pi) - np.pi)
    m = d < 0.35
    if m.sum() < 50:
        continue
    q = LP[m]
    r = np.hypot(q[:, 0] - cx, q[:, 1] - cy)
    k = q[:, 2].argmax()
    legmeas.append({"foot_az_deg": round(math.degrees(fa), 1), "foot_r_m": round(float(np.hypot(*(f["c"] - [cx, cy])) * s), 4),
                    "knee_r_m": round(float(r[k] * s), 4), "knee_z_m": round(float(q[k, 2] * s), 4),
                    "hip_r_m": round(float(np.percentile(r, 1) * s), 4)})

bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[f for f, k in zip(bm.faces, keep) if not k], context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
# drop small floating islands (< 0.4% of the skin's area). Generators split vertices at UV seams, so islands are
# judged by union-find over QUANTISED vertex positions (the skin itself stays unwelded to keep its UVs).
eps = 1e-4 * span.max()
parent = {}


def find(k):
    while parent.setdefault(k, k) != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k


bm.faces.ensure_lookup_table()
fkeys = []
for f in bm.faces:
    ks = [tuple(int(round(c / eps)) for c in v.co) for v in f.verts]
    r0 = find(ks[0])
    for k in ks[1:]:
        r = find(k)
        if r != r0:
            parent[r] = r0
    fkeys.append(ks[0])
area = {}
for f, k in zip(bm.faces, fkeys):
    r = find(k)
    area[r] = area.get(r, 0) + f.calc_area()
tot = sum(area.values())
drop = [f for f, k in zip(bm.faces, fkeys) if area[find(k)] < 0.004 * tot]
bmesh.ops.delete(bm, geom=drop, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
if MIRROR:
    # robot bodies are bilaterally symmetric; the generator's halves are not (one side is ragged where legs fused).
    # keep the better half and mirror it across x = cx (UVs are kept, so the copy reuses the same texture region)
    keep_neg = MIRROR == "left"
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.calc_center_median().x > cx) == keep_neg], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    res = bmesh.ops.duplicate(bm, geom=list(bm.faces))
    nv = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    nf = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
    for v in nv:
        v.co.x = 2 * cx - v.co.x
    bmesh.ops.reverse_faces(bm, faces=nf)
bm.to_mesh(me)
bm.free()

me.transform(Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(Vector((-cx, -cy, 0))))
# trim hip-actuator stubs and the ragged tail: per 1 cm station the CARAPACE half-width is taken from verts within 2 cm
# of the station's top only (stubs sit low); faces outside it (+3 mm) or behind --clip-rear are dropped.
CLIP_REAR = opt("--clip-rear", 1.0, float)
UPPER = opt("--upper", 0.035, float)
Vs = np.array([v.co[:] for v in me.vertices])
st_y = np.arange(-BODY_LEN / 2, BODY_LEN / 2 + 1e-9, 0.01)
hw_up = []
for y in st_y:
    m = np.abs(Vs[:, 1] - y) < 0.006
    if m.sum() < 8:
        hw_up.append(0.0)
        continue
    q = Vs[m]
    up = q[q[:, 2] > q[:, 2].max() - UPPER]
    hw_up.append(float(np.percentile(np.abs(up[:, 0]), 98)))
hw_up = np.array(hw_up)
hw_s = np.array([np.median(hw_up[max(0, i - 2):i + 3]) for i in range(len(hw_up))])
bm = bmesh.new()
bm.from_mesh(me)
cut = []
for f in bm.faces:
    c = f.calc_center_median()
    i = int(np.clip(round((c.y + BODY_LEN / 2) / 0.01), 0, len(st_y) - 1))
    if abs(c.x) > hw_s[i] + 0.003 or c.y > CLIP_REAR:
        cut.append(f)
bmesh.ops.delete(bm, geom=cut, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(me)
bm.free()
Vs = np.array([v.co[:] for v in me.vertices])
blo, bhi = Vs.min(0), Vs.max(0)

# body half-width profile along Y (2 cm bins), measured at the shell's widest band
# skin [y, half_width, rim_z (median z of the outermost skin verts), top_z]; footprint [y, half_width, low_z] of the whole
# body blob (legs removed), used to loft the chassis. 1 cm stations.
Q = (Vfp - [cx, cy, 0]) * s
prof, fprof = [], []
for y in np.arange(-BODY_LEN / 2, BODY_LEN / 2 + 1e-9, 0.01):
    m = np.abs(Vs[:, 1] - y) < 0.006
    if m.sum() > 12:
        ax = np.abs(Vs[m, 0])
        hw = float(np.percentile(ax, 99))
        rim = Vs[m][ax > 0.9 * hw]
        prof.append([round(float(y), 3), round(hw, 4), round(float(np.median(rim[:, 2])), 4), round(float(Vs[m, 2].max()), 4)])
    mq = np.abs(Q[:, 1] - y) < 0.006
    if mq.sum() > 5:
        fprof.append([round(float(y), 3), round(float(np.percentile(np.abs(Q[mq, 0]), 99)), 4),
                      round(float(np.percentile(Q[mq, 2], 3)), 4)])
feet_m = sorted([[round(float((f["c"][0] - cx) * s), 4), round(float((f["c"][1] - cy) * s), 4)] for f in feet],
                key=lambda p: (p[0] > 0, p[1]))
rep = {"gen": GEN, "scale": s, "gen_span_m": [round(float(x * s), 4) for x in span],
       "shell_dims_m": [round(float(x), 4) for x in bhi - blo], "shell_z": [round(float(blo[2]), 4), round(float(bhi[2]), 4)],
       "shell_faces": len(me.polygons), "feet_found": len(feet_m), "feet_xy_m": feet_m,
       "foot_radius_from_center_m": [round(math.hypot(*f), 4) for f in feet_m], "half_width_profile": prof, "footprint_profile": fprof, "legs_generated": legmeas,
       "opening_radius_m": round(float(R * cell * s), 4)}
gen["anymachine_shell"] = json.dumps(rep)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump(rep, open(OUT.replace(".blend", ".json"), "w"), indent=1)
print("SHELL", json.dumps({k: v for k, v in rep.items() if k not in ("half_width_profile", "footprint_profile")}), flush=True)

if PNG:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 900, 600
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.energy = 3
    sun.rotation_euler = (0.6, 0.2, 0.5)
    for name, d in {"persp": (-0.7, -1, 0.6), "under": (0.5, -0.6, -0.5), "top": (0, -0.001, 1)}.items():
        d = Vector(d).normalized()
        c = Vector((0, 0, (blo[2] + bhi[2]) / 2))
        cam.location = c + d * 1.0
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 50
        sc.render.filepath = PNG.replace(".png", f"_{name}.png")
        bpy.ops.render.render(write_still=True)
