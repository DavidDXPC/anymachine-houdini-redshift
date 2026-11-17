# _eq.py: shared helpers for the equipment family (cover pieces: xmas_tree, chem_skid, bottle_rack, air_receiver, hpu,
# cable_reel, tugger_winch, pipe_bolster, ibc_stack, heat_exchanger, control_station, waste_skip).
# Sits on the pipework family's helpers (../pipework/_pw.py, only imported) and through them on the rig 1 kit
# (dugout_blender/props_hand/_common/hs.py).  Adds: opaque mesh panels (one quad in the game mesh, the mesh baked),
# stencil digits (bake only), grime runs, a dirtier paint default ("used and somewhat dirty but maintained"),
# and tail(): pw.tail plus size / origin / footprint / cover figures in stats.json.
import bpy, sys, os, json, math, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipework"))
import _pw as pw
from _pw import V, T, at, frame
from mathutils import Matrix

A = pw.A
TX1 = os.path.join(pw.ROOT, "dugout_blender", "props_hand", "_tex", "out")
tx1 = lambda n: os.path.join(TX1, n)
RZ = lambda a: Matrix.Rotation(math.radians(a), 4, "Z")
RX = lambda a: Matrix.Rotation(math.radians(a), 4, "X")
RY = lambda a: Matrix.Rotation(math.radians(a), 4, "Y")

new = pw.new


def quad(b, name, O, ex, ey, w, h, mat, detail=False, lift=0.0):
    """One rectangle: corner O, edges ex*w and ey*h, facing ex x ey."""
    n = V(ex).normalized().cross(V(ey).normalized())
    with at(b, frame(V(O) + n * lift, n, ex)):
        return b.box(name, (0, 0, -0.01), (w, h, 0), mat=mat, skip="-x,+x,-y,+y,-z", detail=detail)


def mesh_panel(b, O, ex, ey, w, h, backs=(), mesh="galv_t", void="void", lw=0.09, sw=0.045, bw=0.008, lo=True, lift=0.0):
    """An opaque expanded-mesh panel.  Game mesh: one quad (material 'void', dark).  Bake source: diamond mesh strands
    3 mm proud, and 'backs' [(u0, u1, v0, v1, material)]: flat patches 1 mm proud that stand for what is seen through
    the mesh (cylinders, a drum).  Players cannot see through it: it is cover."""
    n = V(ex).normalized().cross(V(ey).normalized())
    if lo: quad(b, "mesh_panel", O, ex, ey, w, h, void, lift=lift)
    with at(b, frame(V(O) + n * lift, n, ex)):
        for u0, u1, v0, v1, m in backs:
            b.box("d_back", (u0, v0, 0.0002), (u1, v1, 0.001), mat=m, skip="-z", detail=True)
        k = sw / lw
        for s in (-1, 1):
            c = -k * w if s > 0 else 0.0
            c = math.floor(c / sw) * sw + (sw / 2 if s > 0 else 0)
            while c < h + k * w + sw:
                # line v = c + s*k*u for u in [0, w], clipped to v in [0, h]
                u0, u1 = 0.0, w
                if s > 0:
                    u0 = max(u0, (0 - c) / k); u1 = min(u1, (h - c) / k)
                else:
                    u0 = max(u0, (c - h) / k); u1 = min(u1, c / k)
                if u1 - u0 > 0.02:
                    p0 = (u0, c + s * k * u0, 0); L = (u1 - u0) * math.hypot(1, k)
                    with at(b, T(V(p0)) @ Matrix.Rotation(math.atan2(s * k, 1), 4, "Z")):
                        b.box("d_strand", (0, -bw / 2, 0.0005), (L, bw / 2, 0.0035), mat=mesh, skip="-z,-x,+x", detail=True)
                c += sw


def grid_panel(b, O, ex, ey, w, h, pitch=0.05, bw=0.008, mesh="galv_t", void="void", lo=True, backs=(), lift=0.0):
    """As mesh_panel, with a square welded-wire grid."""
    n = V(ex).normalized().cross(V(ey).normalized())
    if lo: quad(b, "grid_panel", O, ex, ey, w, h, void, lift=lift)
    with at(b, frame(V(O) + n * lift, n, ex)):
        for u0, u1, v0, v1, m in backs:
            b.box("d_back", (u0, v0, 0.0002), (u1, v1, 0.001), mat=m, skip="-z", detail=True)
        nu = max(1, round(w / pitch)); nv = max(1, round(h / pitch))
        for i in range(1, nu):
            u = w * i / nu; b.box("d_wire", (u - bw / 2, 0, 0.0005), (u + bw / 2, h, 0.0035), mat=mesh, skip="-z,-y,+y", detail=True)
        for j in range(1, nv):
            v = h * j / nv; b.box("d_wire", (0, v - bw / 2, 0.0005), (w, v + bw / 2, 0.0035), mat=mesh, skip="-z,-x,+x", detail=True)


SEG = dict(a=(0, 2, 1, 0), b=(1, 1, 0, 1), c=(1, 0, 0, 1), d=(0, 0, 1, 0), e=(0, 0, 0, 1), f=(0, 1, 0, 1), g=(0, 1, 1, 0))
DIG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g",
       "A": "abcefg", "C": "adef", "E": "adefg", "F": "aefg", "H": "bcefg", "L": "def", "P": "abefg", "U": "bcdef", " ": ""}


def stencil(b, text, O, ex, ey, h, mat="paintw", gap=0.3):
    """Stencil-cut figures (seven strokes with bridges, like a cut stencil), bake only, 1 mm of paint on the surface.
    O: lower-left of the text on the surface, ex along the text, ey up.  Returns the width."""
    n = V(ex).normalized().cross(V(ey).normalized()); cw = h * 0.5; t = h * 0.15; step = cw * (1 + gap); br = t * 0.35
    with at(b, frame(O, n, ex)):
        for i, ch in enumerate(text):
            x0 = i * step
            for s in DIG.get(ch, ""):
                cx, cy, dx, dy = SEG[s]; hh = (h - t) / 2
                if dx:   # horizontal stroke at height cy*hh
                    y = cy * hh; b.box("d_sten", (x0 + br + t * 0.5, y, 0.0002), (x0 + cw - br - t * 0.5, y + t, 0.001), mat=mat, skip="-z", detail=True)
                else:    # vertical stroke on column cx, half cy
                    x = x0 + cx * (cw - t); y = cy * hh; b.box("d_sten", (x, y + br + t * 0.5, 0.0002), (x + t, y + hh + t * 0.5 - br, 0.001), mat=mat, skip="-z", detail=True)
    return len(text) * step - cw * gap


def run(b, top, n, w, h, mats, i=2, strength=0.45):
    """A grime run hanging down from the point 'top' on an upright face with normal n."""
    c = V(top) - V((0, 0, h / 2))
    b.decal(tx1("sn_%02d.png" % i), c, n, (0, 0, 1), w, h, kind="stain", mats=tuple(mats), depth=0.25, strength=strength)


def puddle(b, c, w, mats, i=5, strength=0.5):
    """A stain on a level face (oil under a pump, a ring under a drum)."""
    b.decal(tx1("sn_%02d.png" % i), c, (0, 0, 1), (0, 1, 0), w, w, kind="stain", mats=tuple(mats), depth=0.06, strength=strength)


# extra colours on top of pw.presets(): name -> (preset it is made from, changes)
EXTRA = {
    "void": ("dark", {}),
    "paintw": ("pipe", dict(edge=0.0, bias=-0.25, rust=0.05, dirt=0.3)),      # white paint on a surface (stencils, baked patches): no edge chipping
    "blue": ("blue", dict(tint=pw.tn(46, 72, 112))),      # the sheets' navy machinery blue, greyer than the pipe blue
    "maroon": ("red", dict(tint=pw.tn(112, 34, 44))),
    "cylgrey": ("grey", dict(tint=pw.tn(120, 124, 126))),
    "stainless": ("steel", dict(metal=0.85, rough=0.38, rust=0.12, value=1.05, edge=0.1, tile=0.8)),
    "alu": ("steel", dict(metal=0.75, rough=0.45, rust=0.08, value=1.1, edge=0.08, tile=1.0)),
    "rope": ("steel", dict(metal=0.6, rough=0.6, rust=0.35, value=0.55, dirt=0.7)),
    "rubber": ("black", dict(rough=0.75)),
    "plastic": ("pipe", dict(tint=(1.0, 1.0, 0.98), value=1.0, sat=0.15, rust=0.0, edge=0.0, rough=0.5, dirt=0.35)),
    "liquid": ("pipe", dict(tint=(0.62, 0.66, 0.72), value=0.9, sat=0.2, rust=0.0, edge=0.0, rough=0.5, dirt=0.3)),
    "tarp": ("green", dict(tint=pw.tn(58, 104, 74), edge=0.05, rust=0.0, rough=0.7, dirt=0.6, dent=2.2)),
    "brass": ("steel", dict(tint=(1.0, 0.78, 0.4), metal=0.8, rough=0.4, rust=0.1)),
    "wood": ("pipe", dict(tint=(0.55, 0.42, 0.28), value=0.75, sat=0.8, rust=0.0, edge=0.1, rough=0.85, dirt=0.6)),
    "pipesteel": ("black", dict(tint=pw.tn(52, 46, 42), rust=0.55, rough=0.7, edge=0.3, dirt=0.5, metal=0.2)),
    "capblue": ("cblue", dict(rough=0.6)), "capred": ("cred", dict(rough=0.6)), "capgreen": ("green", dict(edge=0.1, rust=0.0, rough=0.6)),
    "lampg": ("green", dict(tint=pw.tn(40, 150, 70), edge=0.0, rust=0.0, rough=0.25)),
    "lampy": ("yellow", dict(edge=0.0, rust=0.0, rough=0.25)),
    "lampr": ("cred", dict(tint=pw.tn(190, 36, 30), edge=0.0, rust=0.0, rough=0.25)),
}
CLEAN = {"paintw", "dark", "glass", "black", "void", "rubber", "plastic", "liquid", "tarp", "lampg", "lampy", "lampr", "wood"}


def dirty(b, over=None):
    """The family's paint: every preset a little dirtier and rustier at the joints than the kit default, plus EXTRA."""
    P = pw.presets(); out = {}; over = over or {}
    for name in b.matdb:
        base = name[:-2] if name.endswith("_t") else name
        e = EXTRA.get(base); thin = name.endswith("_t"); own = over.get(name); o = own or over.get(base) or {}
        if isinstance(o, tuple): bb, ch = o
        elif e: bb = e[0]; ch = dict(e[1]); ch.update(o)
        else: bb, ch = base, o
        ch = dict(ch)
        if thin and not own:      # a change given for the base colour: keep the thin-part softening of its edge wear
            if "edge" in ch: ch["edge"] *= 0.55
            if "bias" in ch: ch["bias"] -= 0.03
        if bb not in P: raise KeyError(f"material {name}: no preset {bb}")
        kw = P[bb][1]; d = {}
        if base not in CLEAN and bb not in ("dark",):
            d = dict(dirt=min(1.0, kw.get("dirt", 0.5) * 1.35 + 0.05), rust=min(1.0, kw.get("rust", 0.5) * 1.3 + 0.03), low=max(kw.get("low", 0.5), 0.45))
            if bb not in ("steel", "galv", "grate", "deck"):      # painted: a little more chipping than the kit default
                e0, b0 = kw.get("edge", 0.45), kw.get("bias", 0.0)
                if thin: e0, b0 = e0 * 0.55, b0 - 0.03
                d.update(edge=e0 * 1.2, bias=b0 + 0.02)
        d.update(ch); out[name] = (bb, d)
    return out


def cover(o, hx, hy, H, zmax=1.0, res=0.02):
    """Fraction of the box's side elevation (up to zmax or H) that the model blocks, seen along Y and along X."""
    me = o.data; me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices]); tri = np.array([t.vertices[:] for t in me.loop_triangles]); out = {}
    for name, a, half in (("along_y", 0, hx), ("along_x", 1, hy)):
        W = int(round(2 * half / res)); Hh = int(round(min(H, zmax) / res)); g = np.zeros((Hh, W), bool)
        for p in co[tri][:, :, [a, 2]]:
            mn = p.min(0); mx = p.max(0)
            i0 = max(0, int((mn[0] + half) / res)); i1 = min(W - 1, int((mx[0] + half) / res)); j0 = max(0, int(mn[1] / res)); j1 = min(Hh - 1, int(mx[1] / res))
            if i1 < i0 or j1 < j0: continue
            d = (p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1]) - (p[2, 0] - p[0, 0]) * (p[1, 1] - p[0, 1])
            if abs(d) < 1e-12: continue
            X, Y = np.meshgrid((np.arange(i0, i1 + 1) + 0.5) * res - half, (np.arange(j0, j1 + 1) + 0.5) * res)
            u = ((X - p[0, 0]) * (p[2, 1] - p[0, 1]) - (p[2, 0] - p[0, 0]) * (Y - p[0, 1])) / d
            v = ((p[1, 0] - p[0, 0]) * (Y - p[0, 1]) - (X - p[0, 0]) * (p[1, 1] - p[0, 1])) / d
            g[j0:j1 + 1, i0:i1 + 1] |= (u >= -0.02) & (v >= -0.02) & (u + v <= 1.02)
        out[name] = round(float(g.mean()), 3)
    return out


METALS = {"stainless", "alu", "steel", "galv", "rope", "brass", "grate"}
#          dark runs, blotchy grime, chips on flats, light scuffs, fading
WEATHER = dict(paint=dict(streak=0.75, grime=0.6, chips=0.4, scuff=0.35, fade=0.3),
               metal=dict(streak=0.65, grime=0.55, chips=0.0, scuff=0.25, fade=0.0),
               clean=dict(streak=0.3, grime=0.3, chips=0.0, scuff=0.2, fade=0.0))


def weather(b, ov, grunge=None):
    """A second layer over the kit's wear shader, on the bake source only: what the sheets and the map have on every
    flat face and the kit's shader leaves clean.  Dark runs down upright faces, blotchy grime, small chips to primer
    and rust away from the edges, light scuffs, uneven fading.  grunge: {material: {streak, grime, chips, scuff,
    fade}} changes the amounts for one material (0 switches a layer off)."""
    grunge = grunge or {}
    for name, d in b.sock.items():
        base = name[:-2] if name.endswith("_t") else name; bb = ov[name][0]
        if base in ("dark", "void", "glass") or bb == "dark": continue
        kind = "metal" if (base in METALS or bb in ("steel", "galv", "grate")) else "clean" if base in CLEAN else "paint"
        a = dict(WEATHER[kind]); a.update(grunge.get(base, {})); a.update(grunge.get(name, {}))
        g = d["g"]; e_col = d["color"].node; col0 = e_col.inputs[0].links[0].from_socket; users = [(l.to_node, l.to_socket) for l in col0.links]
        P = g.new("ShaderNodeTexCoord").outputs["Object"]; geo = g.new("ShaderNodeNewGeometry")
        ns = g.new("ShaderNodeSeparateXYZ"); g.link(geo.outputs["True Normal"], ns.inputs[0])
        upright = g.math("SUBTRACT", 1.0, g.math("ABSOLUTE", ns.outputs["Z"]))
        col = col0
        def stretched(scale, detail=4, rough=0.6):
            mp = g.new("ShaderNodeMapping"); g.link(P, mp.inputs[0]); mp.inputs["Scale"].default_value = scale
            return g.noise(mp.outputs[0], 1.0, detail, rough)
        if a["fade"] > 0:
            f = g.maprange(g.noise(P, 0.9, 3, 0.5), 0.4, 0.8, 0, 0.6 * a["fade"])
            col = g.mix(f, col, g.mix(0.45, col, (0.62, 0.61, 0.58, 1)))
        if a["grime"] > 0:
            m = g.maprange(g.noise(P, 2.6, 7, 0.68), 0.47, 0.72, 0, 0.9 * a["grime"])
            col = g.mix(m, col, g.mix(1.0, col, (0.38, 0.33, 0.29, 1), "MULTIPLY"))
        if a["streak"] > 0:
            wide = g.maprange(stretched((7.0, 7.0, 0.35)), 0.45, 0.65, 0, 1); fine = g.maprange(stretched((34.0, 34.0, 0.9), 5), 0.52, 0.74, 0, 1)
            m = g.math("MULTIPLY", g.math("MULTIPLY", g.math("MAXIMUM", g.math("MULTIPLY", wide, 0.7), g.math("MULTIPLY", wide, fine)), upright), 1.0 * a["streak"])
            col = g.mix(m, col, g.mix(1.0, col, (0.3, 0.25, 0.21, 1), "MULTIPLY"))
        if a["scuff"] > 0:
            m = g.math("MULTIPLY", g.maprange(stretched((1.6, 1.6, 55.0), 3), 0.66, 0.8, 0, 1), g.maprange(g.noise(P, 1.3, 2, 0.5), 0.45, 0.6, 0, 0.6 * a["scuff"]))
            col = g.mix(m, col, g.mix(0.5, col, (0.7, 0.69, 0.66, 1)))
        if a["chips"] > 0:
            where = g.maprange(g.noise(P, 1.9, 3, 0.55), 0.42, 0.55, 0, 1, smooth=True)
            n = g.noise(P, 28, 6, 0.7)
            chip = g.math("MULTIPLY", g.maprange(n, 0.64 - 0.04 * a["chips"], 0.655 - 0.04 * a["chips"], 0, 1), where)
            halo = g.math("MULTIPLY", g.maprange(n, 0.58 - 0.04 * a["chips"], 0.655 - 0.04 * a["chips"], 0, 0.5), where)
            rustc = g.img(pw.kt("rust_steel.png"), g.mapping(P, 1 / 0.7, (0.3, 0.6, 0.1)), "BOX").outputs["Color"]
            bare = g.mix(g.maprange(g.noise(P, 9, 4, 0.6), 0.3, 0.55, 0, 1), rustc, (0.21, 0.2, 0.195, 1))
            col = g.mix(halo, col, g.mix(1.0, col, (0.78, 0.6, 0.47, 1), "MULTIPLY"))
            col = g.mix(chip, col, bare)
        for node, sock in users:
            for l in list(sock.links): g.nt.links.remove(l)
            g.link(col, sock)


def tail(b, here, hx, hy, H, size=2048, over=None, views=None, uv_scale=None, front=None, notes=None, close=None, grunge=None):
    """Finish, stats, unwrap, paint, weather, bake (--size / --spp, --nobake), export, review (unless --noreview).
    The model must fill (-hx, -hy, 0) .. (hx, hy, H): origin at the centre of the footprint on the floor.
    close: dict(sheet="<id>_close1", shots=[dict(eye=, at=, lens=)] * 6) renders review_close.jpg beside that sheet.
    (pw.tail's steps, written out here so the weather layer can go between the paint and the bake.)"""
    lo, hi = b.finish(weld=0.0002)
    st = b.stats((-hx, -hy, 0), (hx, hy, H))
    us = {"dark": 0.3, "void": 0.6}; us.update(uv_scale or {})
    st.update(b.unwrap(margin=0.004, uv_scale=us))
    ov = dirty(b, over); pal = pw.paints(b, ov)
    baked = "--nobake" not in A
    if baked:
        weather(b, ov, grunge)
        sz = int(pw.arg("--size", size)); b.bake(here, size=sz, samples=int(pw.arg("--spp", 24))); st["texture"] = sz
    else: st["texture"] = 0
    st["texture_target"] = size
    st["size"] = [round(st["max"][i] - st["min"][i], 4) for i in range(3)]
    st["box"] = [2 * hx, 2 * hy, H]
    st["origin"] = "centre of the footprint, on the floor (z = 0); long side along X; front faces -Y"
    st["footprint"] = dict(min=st["min"][:2], max=st["max"][:2])
    st["cover_below_1m"] = cover(lo, hx, hy, H)
    if front: st["faces"] = front
    if notes: st["notes"] = notes
    json.dump(st, open(os.path.join(here, "stats.json"), "w"), indent=1)
    bpy.ops.object.select_all(action="DESELECT"); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    bpy.ops.export_scene.gltf(filepath=os.path.join(here, b.name + ".glb"), export_format="GLB", use_selection=True, export_tangents=True, export_apply=True, export_yup=True)
    for im in bpy.data.images:
        if im.filepath_raw and os.path.exists(bpy.path.abspath(im.filepath_raw)):
            try: im.filepath = bpy.path.relpath(im.filepath_raw, start=here)
            except Exception: pass
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(here, b.name + ".blend"))
    cfg = dict(id=b.name, baked=baked, palette=pal, tintable=[])
    if views: cfg["views"] = views
    if close: cfg["close"] = close
    json.dump(cfg, open(os.path.join(here, "_review.json"), "w"), indent=1)
    if "--noreview" not in A:
        subprocess.run([bpy.app.binary_path, "-b", "--factory-startup", "-t", "4", "--python", os.path.join(pw.HERE, "_review.py"), "--", here], stdout=subprocess.DEVNULL)
    print("EQ", b.name, "tris", st["tris"], "bbox_err_mm", st["bbox_err_mm"], "cover", st["cover_below_1m"], "uv_fill", st["uv_fill"], flush=True)
    return st
