# ls.py: helpers for the lifesaving family, on top of the landmarks helpers (lm.py) and the rig 1 kit (hs.py), both
# imported and not edited.  Oriented boxes, lettering as bake-only geometry, and a tail that can move the whole build
# by a matrix before it is finished (the boat is modelled in boat coordinates and delivered in the station frame).
import bpy, bmesh, sys, os, json, math, subprocess
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "landmarks", "_shared"))
import lm
from lm import hs, V, Z, A, sect, rect, tube
import station as st


def F(o, ex, ey):
    """Frame matrix: origin o, local x and y (made orthonormal), z = x cross y."""
    ex = V(ex).normalized(); ey = V(ey); ey = (ey - ex * ey.dot(ex)).normalized(); ez = ex.cross(ey)
    m = Matrix.Identity(4)
    for i, c in enumerate((ex, ey, ez)):
        for k in range(3): m[k][i] = c[k]
    for k in range(3): m[k][3] = V(o)[k]
    return m


def obox(b, name, M, mn, mx, mat="paint", bev=0.0, skip="", detail=False, bev_axes=None):
    """hs box in the local frame M."""
    return b.box(name, mn, mx, mat=mat, bev=bev, skip=skip, detail=detail, xf=M, bev_axes=bev_axes)


def text(b, s, o, ex, ey, height, mat="stencil", lift=0.0012, spacing=1.05):
    """Lettering as flat bake-only geometry lying in the plane (o, ex, ey), centred on o, cap height `height`."""
    cu = bpy.data.curves.new("t", "FONT"); cu.body = s; cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.size = height / 0.69
    cu.space_character = spacing; cu.offset = height * 0.035
    ob = bpy.data.objects.new("t", cu); bpy.context.scene.collection.objects.link(ob); bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bm = bmesh.new(); bm.from_mesh(me); M = F(o, ex, ey) @ Matrix.Translation((0, 0, lift))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu); bpy.data.meshes.remove(me)
    return b._obj(bm, "d_text", mat, True)


def polytube(b, name, pts, r, n=6, mat="paint", caps=(True, True)):
    """One tube through a polyline with mitred joints (no overlapping ends)."""
    pts = [V(p) for p in pts]; bm = bmesh.new(); rings = []
    t0 = (pts[1] - pts[0]).normalized(); e1 = t0.orthogonal().normalized()
    if abs(t0.z) < 0.9: e1 = t0.cross(Z).normalized()
    for i, p in enumerate(pts):
        tin = (p - pts[i - 1]).normalized() if i > 0 else (pts[1] - p).normalized()
        tout = (pts[i + 1] - p).normalized() if i < len(pts) - 1 else tin
        if i > 0:                       # carry the section along without twisting
            q = pts[i - 1] - pts[i - 2] if i > 1 else tin
            e1 = (e1 - tin * e1.dot(tin)).normalized()
        tb = (tin + tout).normalized(); e2 = tin.cross(e1).normalized(); ring = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n; off = (e1 * math.cos(a) + e2 * math.sin(a)) * r
            d = tb.dot(tin); off = off - tin * (off.dot(tb) / d) if abs(d) > 1e-4 else off      # project onto the mitre plane
            ring.append(bm.verts.new(p + off))
        rings.append(ring)
    for a_, c_ in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n; bm.faces.new((a_[k], a_[j], c_[j], c_[k]))
    if caps[0]: bm.faces.new(list(reversed(rings[0])))
    if caps[1]: bm.faces.new(rings[-1])
    hs._quad_caps(bm)
    return b._obj(bm, name, mat)


def tail(parts, here, name, mn, mx, views, M=None, extras=(), size=2048, margin=0.002, place=None, note=None, sharp=65, weld=0.0002):
    """lm.tail_multi, with the whole build moved by M first.  parts = [(build, wear function, uv_scale)]."""
    hs._normals.__defaults__ = (sharp,)
    stt = dict(sets={})
    for b, wear, uvs in parts:
        if M is not None:
            for o in b.lo + b.hi: o.data.transform(M)
            for d in b.decals: d["e"].matrix_world = M @ d["e"].matrix_basis      # matrix_world is stale until the depsgraph runs
        if "--parts" in A:       # the pieces as they were modelled, in build order, for the making-of film (film/film.py)
            for i, o in enumerate(b.lo): o["part"] = i
            for o in b.hi: bpy.data.objects.remove(o)
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(here, name + "_parts.blend")); print("PARTS", len(b.lo)); sys.exit(0)
        b.finish(weld=weld); s_ = b.stats(); s_.update(b.unwrap(margin=margin, uv_scale=uvs)); stt["sets"][b.name] = s_
    ex = [e.obj() for e in extras]
    stt["tris_baked"] = sum(s_["tris"] for s_ in stt["sets"].values()); stt["tris_tiles"] = sum(lm.tris(o) for o in ex); stt["tris"] = stt["tris_baked"] + stt["tris_tiles"]
    stt["min"] = [min(s_["min"][i] for s_ in stt["sets"].values()) for i in range(3)]; stt["max"] = [max(s_["max"][i] for s_ in stt["sets"].values()) for i in range(3)]
    if mn is not None: stt["bbox_err_mm"] = round(max(max(abs(stt["min"][i] - mn[i]), abs(stt["max"][i] - mx[i])) for i in range(3)) * 1000, 2)
    if place: stt["place"] = place
    if note: stt["note"] = note
    if os.environ.get("LS_MAXDEC"):
        for b, wear, uvs in parts: del b.decals[int(os.environ["LS_MAXDEC"]):]
    for b, wear, uvs in parts: wear(b)
    if "--nobake" not in A:
        size = int(A[A.index("--size") + 1]) if "--size" in A else size
        for b, wear, uvs in parts: b.bake(here, size=size, samples=int(A[A.index("--spp") + 1]) if "--spp" in A else 24)
        stt["texture"] = size; stt["texture_sets"] = len(parts)
    print("STATS", json.dumps(stt))
    json.dump(stt, open(os.path.join(here, "stats.json"), "w"), indent=1)
    if "--nobake" in A:      # preview: the .blend only (the glTF exporter stalls on the unbaked decal stack)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(here, name + ".blend"))
    else: lm.export(here, name, [b.lo_obj for b, w_, u_ in parts] + ex)
    if "--noreview" not in A:
        subprocess.run([bpy.app.binary_path, "-b", "--factory-startup", "-t", "4", "--python", os.path.join(lm.HERE, "review.py"),
                        "--", here, name, views], stdout=subprocess.DEVNULL)
    return stt
