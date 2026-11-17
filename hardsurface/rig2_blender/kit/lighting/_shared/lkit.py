# lkit.py: the lighting family's builder, on top of the rig 1 kit (hs.py, only imported).
#
# The whole family shares ONE texture set (lighting/lighting_color|normal|orm.png).  Fixtures are instanced hundreds of
# times and are made of repeated pieces (a flood head is used on its own, on a pole, twice on a crossarm, on a rail
# clamp), so the bake is done on unique PARTS laid out in a row, and the OBJECTS are assembled after the bake from
# transformed copies of those parts: every copy of a part shares its UVs.
#   F.part("flood/head", half)      start a part (modelled round its own origin; 'half' = its half extent along X)
#   F.xf(M)                         local transform for the next primitives (tilts), F.xf() resets
#   F.obj("flood", "flood_pole", [("flood/pole_1m", M), ...], mount=..., light_at=..., ...)
# Lit faces use a wear material "lit_<key>"; after the bake they move to their own emissive material (LIT below).
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
FAM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(FAM, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "dugout_blender", "props_hand", "_common"))
import hs
V = Vector
A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
T2 = os.path.join(ROOT, "rig2_blender", "kit", "_tex", "out"); tx = lambda n: os.path.join(T2, n)
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
IDS = ["wellglass", "tube_light", "flood", "obstruction_light", "helideck_lights", "escape_route", "beacon", "work_light"]
T = Matrix.Translation
def R(deg, axis): return Matrix.Rotation(math.radians(deg), 4, axis)
def arg(flag, default): return type(default)(A[A.index(flag) + 1]) if flag in A else default

# lit materials: wear key -> final material name, emission colour (linear RGB), strength, look when off (tint, rough)
LIT = {
    "wellglass":        dict(mat="wellglass__lit",              rgb=(1.0, 0.74, 0.46), strength=6.0,  off=(0.40, 0.44, 0.41), rough=0.22),
    "tube_light":       dict(mat="tube_light__lit",             rgb=(0.80, 0.90, 1.0), strength=5.0,  off=(0.80, 0.82, 0.80), rough=0.25),
    "flood":            dict(mat="flood__lit",                  rgb=(1.0, 0.52, 0.14), strength=12.0, off=(0.55, 0.56, 0.54), rough=0.15),
    "obstruction":      dict(mat="obstruction_light__lit",      rgb=(1.0, 0.03, 0.015), strength=8.0, off=(0.20, 0.012, 0.010), rough=0.2),
    "heli_green":       dict(mat="helideck_lights__lit",        rgb=(0.04, 1.0, 0.32), strength=6.0,  off=(0.03, 0.30, 0.13), rough=0.2),
    "heli_yellow":      dict(mat="helideck_lights__lit_yellow", rgb=(1.0, 0.78, 0.04), strength=8.0,  off=(0.80, 0.60, 0.05), rough=0.25, tex=True),
    "heli_flood":       dict(mat="helideck_lights__lit_flood",  rgb=(1.0, 0.93, 0.80), strength=8.0,  off=(0.62, 0.63, 0.60), rough=0.2),
    "escape_sign":      dict(mat="escape_route__lit",           rgb=(0.10, 1.0, 0.40), strength=4.0,  off=(0.03, 0.45, 0.20), rough=0.3, tex=True),
    "escape_strip":     dict(mat="escape_route__lit_strip",     rgb=(0.50, 1.0, 0.40), strength=1.2,  off=(0.66, 0.72, 0.40), rough=0.45),
    "beacon":           dict(mat="beacon__lit",                 rgb=(1.0, 0.46, 0.02), strength=8.0,  off=(0.60, 0.24, 0.02), rough=0.2),
    "work":             dict(mat="work_light__lit",             rgb=(1.0, 0.90, 0.74), strength=12.0, off=(0.60, 0.61, 0.58), rough=0.15),
    "work_hand":        dict(mat="work_light__lit_hand",        rgb=(1.0, 0.82, 0.58), strength=5.0,  off=(0.42, 0.45, 0.42), rough=0.22),
}
# flat colours for the --nobake geometry preview
FLAT = dict(grey=(0.55, 0.57, 0.58), dgrey=(0.13, 0.14, 0.15), galv=(0.5, 0.52, 0.53), brass=(0.6, 0.42, 0.15), black=(0.02, 0.02, 0.02),
            yellow=(0.7, 0.5, 0.05), stainless=(0.65, 0.66, 0.66), white=(0.85, 0.85, 0.82), refl=(0.8, 0.8, 0.8), dark=(0.03, 0.03, 0.03),
            plate=(0.6, 0.6, 0.58), red=(0.5, 0.05, 0.04), green=(0.03, 0.3, 0.14), pole=(0.5, 0.52, 0.53), led=(0.85, 0.7, 0.2), orange=(0.8, 0.3, 0.05))


class Fam:
    def __init__(s, name="lighting"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        s.b = hs.Build(name); s.parts = {}; s.x = 0.0; s.objects = {}; s.base = Matrix.Identity(4)

    # ---------------------------------------------------------------- parts and objects
    def part(s, name, half):
        s.x += half + 0.3
        s.b.tag = len(s.parts) + 1; s.base = T((s.x, 0, 0)); s.b.xf = s.base.copy()
        s.parts[name] = dict(tag=s.b.tag, base=s.base.copy()); s.x += half + 0.3
        return s.b

    def xf(s, M=None):
        s.b.xf = (s.base @ M) if M is not None else s.base.copy()

    def obj(s, fid, name, inst, **meta):
        s.objects[name] = dict(id=fid, inst=[(p, (m if m is not None else Matrix.Identity(4))) for p, m in inst], meta=meta)

    def decal(s, img, c, n, up, w, h=None, kind="label", mats=("grey",), depth=0.012, strength=1.0):
        M = s.b.xf; rot = M.to_3x3()
        s.b.decal(os.path.join(FAM, "_shared", img), M @ V(c), rot @ V(n), rot @ V(up), w, h, kind=kind, mats=mats, depth=depth, strength=strength)

    # ---------------------------------------------------------------- geometry helpers
    def tube(s, name, pts, r, n=5, mat="galv", bend=0.0, seg=2, caps=(False, False), detail=False, phase=0.5):
        """A round bar or pipe along a polyline, corners rounded to radius 'bend' with 'seg' steps (from cabinets/kit.py)."""
        b = s.b; P = [V(p) for p in pts]; path = [P[0]]
        for i in range(1, len(P) - 1):
            a, c, d = P[i - 1], P[i], P[i + 1]
            u = (a - c).normalized(); w = (d - c).normalized(); ang = u.angle(w)
            if bend <= 0 or ang > math.pi - 1e-3:
                path.append(c); continue
            t = min(bend / math.tan(ang / 2), (a - c).length * (0.49 if i > 1 else 0.98), (d - c).length * (0.49 if i < len(P) - 2 else 0.98))
            rr = t * math.tan(ang / 2); ctr = c + (u + w).normalized() * (rr / math.sin(ang / 2))
            v0 = c + u * t - ctr; v1 = c + w * t - ctr; sweep = v0.angle(v1); axis = v0.cross(v1).normalized()
            for k in range(seg + 1): path.append(ctr + Matrix.Rotation(sweep * k / seg, 3, axis) @ v0)
        path.append(P[-1])
        tans = [(path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized() for i in range(len(path))]
        t0 = tans[0]; ex = t0.cross(V(Z)).normalized() if abs(t0.z) < 0.9 else V(X)
        bm = bmesh.new(); rings = []
        for i, (p, t) in enumerate(zip(path, tans)):
            if i > 0: ex = (tans[i - 1].rotation_difference(t) @ ex).normalized()
            ey = t.cross(ex)
            rings.append([bm.verts.new(p + (ex * math.cos(2 * math.pi * (k + phase) / n) + ey * math.sin(2 * math.pi * (k + phase) / n)) * r) for k in range(n)])
        for a, c in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n; bm.faces.new((a[i], a[j], c[j], c[i]))
        if caps[0]: bm.faces.new(list(reversed(rings[0])))
        if caps[1]: bm.faces.new(rings[-1])
        hs._quad_caps(bm)
        return b._obj(bm, name, mat, detail)

    def gland(s, p, n, r=0.013, L=0.03, cable=0.0, cr=None, mat="brass"):
        """Cable gland: hex body on a face at p, pointing along n; 'cable' = length of cable stub leaving it."""
        b = s.b; p, n = V(p), V(n).normalized()
        b.cyl("gland", p, p + n * L, r, n=6, mat=mat, caps=(False, True), r1=r * 0.7)
        b.cyl("d_glandnut", p - n * 0.001, p + n * L * 0.45, r * 1.12, n=6, mat=mat, caps=(False, True), detail=True)
        if cable > 0: b.cyl("cable", p + n * L, p + n * (L + cable), cr or r * 0.5, n=5, mat="black", caps=(False, True))

    def bolt(s, p, n, r=0.006, h=0.004, mat="stainless", hexa=True):
        s.b.bolt(p, n, r=r, h=h, mat=mat, hexa=hexa)

    def facet_ribs(s, at, lo, hi, n=8, per=3, rr=0.003, mat="grey", phase=0.5):
        """Bake-only ribs lying exactly on the facets of an n-sided lathe surface, between profile points lo and hi (r, z)."""
        at = V(at)
        for i in range(n):
            a0, a1 = 2 * math.pi * (i + phase) / n, 2 * math.pi * (i + 1 + phase) / n
            for j in range(per):
                f = (j + 0.5) / per; c = math.cos(a0) * (1 - f) + math.cos(a1) * f; sn = math.sin(a0) * (1 - f) + math.sin(a1) * f
                s.b.cyl("d_rib", at + V((c * lo[0], sn * lo[0], lo[1])), at + V((c * hi[0], sn * hi[0], hi[1])), rr, n=5, mat=mat, detail=True, caps=(False, False))

    def saddle(s, p, along, n, r=0.012, mat="galv"):
        """Bake-only conduit saddle clip at p on a surface with normal n, conduit running 'along'."""
        b = s.b; p, a, n = V(p), V(along).normalized(), V(n).normalized(); side = a.cross(n)
        b.cyl("d_saddle", p - a * 0.008 + n * r, p + a * 0.008 + n * r, r + 0.003, n=10, mat=mat, detail=True)
        for sg in (-1, 1): b.bolt(p + side * sg * (r + 0.012), n, r=0.005, h=0.003, mat=mat)


    def plate(s, c, n, up, w=0.05, h=0.03, mats=("grey",), img="decal_plate_a.png"):
        """Maker's plate: a bake-only thin plate with the plate decal on it, two rivets."""
        b = s.b; c, n, up = V(c), V(n).normalized(), V(up).normalized(); r = up.cross(n)
        s.decal(img, c + n * 0.001, n, up, w, h, kind="label", mats=mats, depth=0.01)
        M = b.xf
        for sg in (-1, 1): b.rivet(c + r * sg * (w / 2 - 0.004) + n * 0.0002, n, r=0.0022, mat="stainless")


# -------------------------------------------------------------------- finish
def wear_all(b):
    P, R_, G, O = tx("paint_offwhite.png"), tx("rust_steel.png"), tx("steel_galv.png"), tx("paint_ochre.png")
    def paint(name, tint, **k):
        d = dict(tile=0.5, edge=0.45, bias=-0.06, rust=0.2, dirt=0.3, top=0.08, low=0, chip_dark=0.25, chip_metal=0.4, chip_rough=0.6, tint=tint, bump=0.35, dent=0.2)
        d.update(k); b.wear(name, P, R_ if d.pop("rusty", False) else G, **d)
    paint("grey", (0.22, 0.25, 0.28))
    paint("dgrey", (0.07, 0.076, 0.086), dirt=0.25, rough=0.5)
    paint("white", (0.92, 0.92, 0.88), edge=0, bias=-0.3, rust=0, dirt=0.1, rough=0.35, top=0)
    paint("red", (0.55, 0.05, 0.04), rough=0.4)
    paint("green", (0.03, 0.34, 0.15), edge=0.1, bias=-0.2, rust=0.05, dirt=0.15, rough=0.35, top=0)
    paint("orange", (0.85, 0.30, 0.04), rough=0.45)
    b.wear("yellow", O, R_, tile=0.6, edge=0.4, bias=-0.06, rust=0.14, dirt=0.3, top=0.1, low=0, chip_metal=0.25, bump=0.35, dent=0.2)
    b.wear("galv", G, R_, tile=0.4, metal=0.85, rough=0.45, edge=0.3, bias=-0.12, rust=0.4, dirt=0.3, chip_metal=0.1, value=0.9, low=0, top=0.05, bump=0.3, dent=0.2)
    b.wear("pole", G, R_, tile=0.6, metal=0.85, rough=0.48, edge=0.2, bias=-0.1, rust=0.45, dirt=0.4, chip_metal=0.1, value=0.85, low=0, top=0, bump=0.3, dent=0.2)
    b.wear("stainless", P, R_, tile=0.5, tint=(0.62, 0.63, 0.64), metal=0.92, rough=0.32, edge=0.1, bias=-0.3, rust=0.1, dirt=0.2, low=0, top=0, bump=0.12, dent=0.0)
    b.wear("refl", G, R_, tile=0.3, metal=1.0, rough=0.16, edge=0, bias=-0.5, rust=0, dirt=0.12, value=1.45, sat=0.3, low=0, top=0, bump=0.1, dent=0.1)
    b.wear("brass", G, R_, tile=0.3, metal=0.9, rough=0.36, edge=0.1, bias=-0.3, rust=0.1, dirt=0.3, tint=(1.0, 0.70, 0.30), value=1.05, low=0, top=0, bump=0.2, dent=0.1)
    b.wear("plate", G, R_, tile=0.3, metal=0.8, rough=0.35, edge=0, bias=-0.5, rust=0.05, dirt=0.15, value=1.2, sat=0.4, low=0, top=0, bump=0.1, dent=0.0)
    b.wear("black", P, R_, tile=0.5, tint=(0.028, 0.028, 0.03), edge=0.15, bias=-0.2, rust=0.0, dirt=0.3, rough=0.62, top=0, low=0, bump=0.2, dent=0.1)
    b.wear("steel", G, R_, tile=0.4, metal=0.85, rough=0.45, edge=0.3, bias=-0.12, rust=0.4, dirt=0.3, chip_metal=0.1, value=0.9, low=0, top=0.05)
    b.wear("dark", R_, R_, tile=0.9, value=0.2, sat=0.3, edge=0.1, rust=0.3, dirt=1.0, rough=0.85, low=0)
    b.wear("led", P, R_, tile=0.5, tint=(0.95, 0.74, 0.16), edge=0, bias=-0.5, rust=0, dirt=0.05, rough=0.4, top=0, low=0, bump=0.1, dent=0)
    for k, d in LIT.items():
        b.wear("lit_" + k, P, R_, tile=0.4, tint=d["off"], edge=0, bias=-0.5, rust=0, dirt=0.14, rough=d["rough"], top=0, low=0, bump=0.08, dent=0.0)


def _flat(name, rgb, emit=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = (*rgb, 1); bs.inputs["Roughness"].default_value = 0.5
    if emit: bs.inputs["Emission Color"].default_value = (*emit, 1); bs.inputs["Emission Strength"].default_value = strength
    return m


def run(defs, only=None):
    """defs: the define(F) functions of the fixtures to build.  Full family when only is None (bakes unless --nobake);
    a single id is always a geometry check (no bake): it prints triangle counts and sizes and writes nothing."""
    F = Fam()
    for d in defs: d(F)
    b = F.b
    b.finish()
    lo = b.lo_obj; me = lo.data; pre = len(b.name) + 1
    wname = [me.materials[p.material_index].name[pre:] for p in me.polygons]
    tags = np.array([d.value for d in me.attributes["item"].data])
    me.calc_loop_triangles(); ttag = np.array([tags[t.polygon_index] for t in me.loop_triangles])
    ptris = {n: int((ttag == p["tag"]).sum()) for n, p in F.parts.items()}
    known = set(FLAT) | {"steel"} | {"lit_" + k for k in LIT}
    bad = {m.name[pre:] for m in b.hi_obj.data.materials} - known
    if bad: raise SystemExit(f"materials without a wear set: {bad}")
    ngon = sum(1 for p in me.polygons if len(p.vertices) > 4)
    st = b.stats(); st["part_tris"] = ptris
    bake = only is None and "--nobake" not in A
    if bake or "--uv" in A:
        st.update(b.unwrap(margin=0.003, uv_scale={"pole": 0.45, "dark": 0.4, "black": 0.5, "yellow": 0.65}))
    if bake:
        wear_all(b)
        size = arg("--size", 2048)
        b.bake(FAM, size=size, samples=arg("--spp", 24)); st["texture"] = size
        base = lo.data.materials[0]; mats = {None: base}; col = [n for n in base.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.name.endswith("_color")][0]
        for k, d in LIT.items():
            if ("lit_" + k) not in wname: continue
            m = base.copy(); m.name = d["mat"]; nt = m.node_tree; bs = nt.nodes["Principled BSDF"]
            if d.get("tex"):       # the sign face glows with its own picture
                ct = [n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image and n.image.name.endswith("_color")][0]
                nt.links.new(ct.outputs[0], bs.inputs["Emission Color"])
            else: bs.inputs["Emission Color"].default_value = (*d["rgb"], 1)
            bs.inputs["Emission Strength"].default_value = d["strength"]; mats[k] = m
    else:
        me.materials.clear(); mats = {}
        for w in sorted(set(wname)):
            if w.startswith("lit_"): d = LIT[w[4:]]; mats[w[4:]] = _flat(d["mat"], d["off"], d["rgb"], d["strength"])
            else: mats["_" + w] = _flat("flat_" + w, FLAT.get(w, (0.5, 0.5, 0.5)))
    order = list(mats);
    if not bake: lo.data.materials.clear()
    else:
        while len(lo.data.materials) > 1: lo.data.materials.pop()
    for k in order[1:] if bake else order: lo.data.materials.append(mats[k])
    for p, w in zip(me.polygons, wname):
        if bake: p.material_index = order.index(w[4:]) if w.startswith("lit_") else 0
        else: p.material_index = order.index(w[4:] if w.startswith("lit_") else "_" + w)
    # ---- parts -> objects
    pmesh = {}
    for n, p in F.parts.items():
        m = lo.data.copy(); bm = bmesh.new(); bm.from_mesh(m); lay = bm.faces.layers.int["item"]
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] != p["tag"]], context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(m); bm.free(); m.transform(p["base"].inverted()); pmesh[n] = m
    sc = bpy.context.scene; made = {}
    for name, o in F.objects.items():
        obs = []
        for pn, M in o["inst"]:
            m = pmesh[pn].copy(); m.transform(M); ob = bpy.data.objects.new(name, m); sc.collection.objects.link(ob); obs.append(ob)
        bpy.ops.object.select_all(action="DESELECT")
        for ob in obs: ob.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1: bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active; ob.name = ob.data.name = name
        bpy.ops.object.material_slot_remove_unused()
        made[name] = ob
    bpy.data.objects.remove(lo); bpy.data.objects.remove(b.hi_obj)
    for e in [o for o in bpy.data.objects if o.type == "EMPTY"]: bpy.data.objects.remove(e)
    for m in pmesh.values(): bpy.data.meshes.remove(m)
    try: bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)     # wear shaders, tiles, decals
    except Exception as e: print("purge:", e)
    # ---- stats, export, per id
    fam_items = {}
    for fid in IDS:
        names = [n for n, o in F.objects.items() if o["id"] == fid]
        if not names: continue
        items = {}; lay = {}; x = 0.0
        for n in names:
            ob = made[n]; m = ob.data; m.calc_loop_triangles(); co = np.array([v.co[:] for v in m.vertices]); mn, mx = co.min(0), co.max(0)
            meta = dict(F.objects[n]["meta"]); lits = [s.material.name for s in ob.material_slots if s.material and "__lit" in s.material.name]
            mount = meta.get("mount", ""); plane = {"wall": abs(mx[1]), "deck": abs(mn[2]), "ceiling": abs(mx[2])}.get(mount.split(" ")[0])
            it = dict(tris=len(m.loop_triangles), min=[round(float(v), 4) for v in mn], max=[round(float(v), 4) for v in mx],
                      size=[round(float(v), 4) for v in (mx - mn)], parts=[p for p, _ in F.objects[n]["inst"]],
                      lit_material=(lits[0] if len(lits) == 1 else lits or None))
            if plane is not None: it["bbox_err_mm"] = round(float(plane) * 1000, 2)     # distance of the mounting face from the origin plane
            it.update(meta); items[n] = it
            x += (mx[0] - mn[0]) / 2 + 0.12 if lay else 0; lay[n] = [round(float(x - (mx[0] + mn[0]) / 2), 4), 0, 0]; x += (mx[0] - mn[0]) / 2 + 0.12
        d = os.path.join(FAM, fid); os.makedirs(d, exist_ok=True)
        s2 = dict(tris=sum(i["tris"] for i in items.values()), ngons=ngon, texture=st.get("texture"), baked=bake,
                  atlas="../lighting_color.png, ../lighting_normal.png, ../lighting_orm.png (shared by the family)",
                  bbox_err_mm=max([i.get("bbox_err_mm", 0) for i in items.values()]), items=items, layout=lay,
                  unique_tris=sum(ptris[p] for p in {p for i in items.values() for p in i["parts"]}))
        fam_items[fid] = s2
        if only is not None: continue          # a single id is a geometry check: print, write nothing
        json.dump(s2, open(os.path.join(d, "stats.json"), "w"), indent=1)
        bpy.ops.object.select_all(action="DESELECT")
        for n in names: made[n].select_set(True)
        bpy.context.view_layer.objects.active = made[names[0]]
        if "--noglb" not in A: bpy.ops.export_scene.gltf(filepath=os.path.join(d, fid + ".glb"), export_format="GLB", use_selection=True, export_tangents=True, export_apply=True, export_yup=True)
        if bake:
            for ob in made.values():
                if ob.name not in names: sc.collection.objects.unlink(ob)
            for n in names: made[n].location = lay[n]
            _rel(d); bpy.ops.wm.save_as_mainfile(filepath=os.path.join(d, fid + ".blend"), copy=True, relative_remap=False); _rel(None)
            for n in names: made[n].location = (0, 0, 0)
            for ob in made.values():
                if ob.name not in names: sc.collection.objects.link(ob)
    st["fixtures"] = {k: dict(tris=v["tris"], objects={n: i["tris"] for n, i in v["items"].items()}) for k, v in fam_items.items()}
    print("STATS", json.dumps(st["fixtures"]), "ngons", ngon, "lo tris", st["tris"], "hi", st["hi_tris"], "uv_fill", st.get("uv_fill"))
    for k, v in fam_items.items():
        for n, i in v["items"].items(): print(f"  {n:22s} {i['tris']:5d} tris  size {i['size']}  mount {i.get('mount')}  err {i.get('bbox_err_mm')}")
    if only is None:
        json.dump(st, open(os.path.join(FAM, "stats.json"), "w"), indent=1)
        if bake:
            x = 0.0
            for n, ob in made.items():
                co = np.array([v.co[:] for v in ob.data.vertices]); w = co[:, 0].max() - co[:, 0].min()
                ob.location = (x + w / 2 - (co[:, 0].max() + co[:, 0].min()) / 2, 0, 0); x += w + 0.25
            _rel(FAM); bpy.ops.wm.save_as_mainfile(filepath=os.path.join(FAM, "lighting.blend"), relative_remap=False)
    return st


def _rel(d):
    for im in bpy.data.images:
        p = getattr(im, "filepath_raw", "")
        if p and im.name.startswith("lighting_"):
            q = os.path.join(FAM, im.name + ".png"); im.filepath = bpy.path.relpath(q, start=d) if d else q


def load_defs(ids=None):
    import importlib.util
    out = []
    for fid in (ids or IDS):
        sp = importlib.util.spec_from_file_location("lighting_" + fid, os.path.join(FAM, fid, "build.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        out.append(m.define)
    return out
