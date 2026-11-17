"""Procedural PBR bake shader, decal sheets and final glTF material for the detail_* pipeline.

All object-space maths is in the mesh's local units (cm for the pack's weapons, set CFG['unit']=0.01),
Bevel/AO distances are world metres.
"""
import math
import os

import bpy

# ---------------------------------------------------------------- material classes
# coat: finish colour / roughness / metallic.  worn: what shows where the finish is rubbed through.
CLASS_PARAMS = {
    "steel_park": dict(coat=(0.032, 0.033, 0.036), coat_r=0.58, coat_m=0.3, worn=(0.52, 0.50, 0.47), worn_r=0.32,
                       worn_m=1.0, wear=1.0, grain=0.35, scratch=0.8, dust=0.8, sheen=0.5),
    "steel_blued": dict(coat=(0.040, 0.043, 0.050), coat_r=0.40, coat_m=0.7, worn=(0.50, 0.49, 0.47), worn_r=0.30,
                        worn_m=1.0, wear=0.8, grain=0.15, scratch=0.9, dust=0.6, sheen=0.6),
    "steel_milled": dict(coat=(0.11, 0.11, 0.115), coat_r=0.40, coat_m=1.0, worn=(0.62, 0.61, 0.59), worn_r=0.25,
                         worn_m=1.0, wear=0.7, grain=0.12, scratch=1.0, dust=0.9, sheen=0.4),
    "alu_anod": dict(coat=(0.035, 0.036, 0.040), coat_r=0.48, coat_m=0.45, worn=(0.62, 0.62, 0.63), worn_r=0.35,
                     worn_m=1.0, wear=0.9, grain=0.10, scratch=0.8, dust=0.7, sheen=0.5),
    "chrome": dict(coat=(0.55, 0.55, 0.56), coat_r=0.22, coat_m=1.0, worn=(0.7, 0.7, 0.7), worn_r=0.3,
                   worn_m=1.0, wear=0.3, grain=0.05, scratch=1.0, dust=0.8, sheen=0.3),
    "mag_alu": dict(coat=(0.050, 0.052, 0.055), coat_r=0.50, coat_m=0.4, worn=(0.60, 0.60, 0.61), worn_r=0.34,
                    worn_m=1.0, wear=1.0, grain=0.15, scratch=1.0, dust=0.8, sheen=0.6),
    "steel_nitride": dict(coat=(0.030, 0.031, 0.034), coat_r=0.40, coat_m=0.7, worn=(0.45, 0.45, 0.44), worn_r=0.3,
                          worn_m=1.0, wear=0.7, grain=0.2, scratch=0.8, dust=0.6, sheen=0.7),
    "alu_optic": dict(coat=(0.030, 0.031, 0.034), coat_r=0.50, coat_m=0.35, worn=(0.60, 0.60, 0.61), worn_r=0.36,
                      worn_m=1.0, wear=0.85, grain=0.3, scratch=0.3, dust=0.6, sheen=0.5),
    "polymer": dict(coat=(0.017, 0.017, 0.018), coat_r=0.62, coat_m=0.0, worn=(0.055, 0.055, 0.055), worn_r=0.42,
                    worn_m=0.0, wear=0.55, grain=1.0, scratch=0.5, dust=1.0, sheen=0.8),
    "polymer_mag": dict(coat=(0.030, 0.028, 0.026), coat_r=0.55, coat_m=0.0, worn=(0.085, 0.082, 0.078), worn_r=0.40,
                        worn_m=0.0, wear=0.7, grain=0.7, scratch=0.9, dust=1.0, sheen=0.8),
    "polymer_smoke": dict(coat=(0.030, 0.019, 0.011), coat_r=0.22, coat_m=0.0, worn=(0.12, 0.08, 0.05), worn_r=0.35,
                          worn_m=0.0, wear=0.3, grain=0.05, scratch=1.0, dust=0.6, sheen=0.3),
    "polymer_fde": dict(coat=(0.33, 0.24, 0.14), coat_r=0.6, coat_m=0.0, worn=(0.45, 0.36, 0.25), worn_r=0.45,
                        worn_m=0.0, wear=0.5, grain=1.0, scratch=0.5, dust=1.0, sheen=0.6),
    "indicator": dict(coat=(0.55, 0.12, 0.02), coat_r=0.5, coat_m=0.0, worn=(0.6, 0.3, 0.1), worn_r=0.45,
                      worn_m=0.0, wear=0.3, grain=0.3, scratch=0.4, dust=0.6, sheen=0.3),
    "rubber": dict(coat=(0.020, 0.020, 0.020), coat_r=0.8, coat_m=0.0, worn=(0.05, 0.05, 0.05), worn_r=0.6,
                   worn_m=0.0, wear=0.4, grain=1.2, scratch=0.2, dust=1.2, sheen=0.2),
    "brass": dict(coat=(0.72, 0.50, 0.20), coat_r=0.3, coat_m=1.0, worn=(0.80, 0.62, 0.32), worn_r=0.22,
                  worn_m=1.0, wear=0.4, grain=0.05, scratch=0.8, dust=0.5, sheen=0.4),
    "glass_dark": dict(coat=(0.010, 0.012, 0.016), coat_r=0.05, coat_m=0.0, worn=(0.02, 0.02, 0.02), worn_r=0.08,
                       worn_m=0.0, wear=0.0, grain=0.0, scratch=0.15, dust=0.5, sheen=0.1),
    "paint_white": dict(coat=(0.75, 0.75, 0.72), coat_r=0.5, coat_m=0.0, worn=(0.3, 0.3, 0.3), worn_r=0.4,
                        worn_m=0.5, wear=0.5, grain=0.2, scratch=0.5, dust=0.8, sheen=0.3),
}
CLASS_PARAMS["wood"] = dict(coat=(0.40, 0.16, 0.045), coat_r=0.34, coat_m=0.0, worn=(0.50, 0.33, 0.17), worn_r=0.62,
                            worn_m=0.0, wear=0.75, grain=0.25, scratch=0.7, dust=0.9, sheen=0.7, wood=1.0)
CLASS_PARAMS["leather"] = dict(coat=(0.075, 0.042, 0.024), coat_r=0.55, coat_m=0.0, worn=(0.21, 0.13, 0.075), worn_r=0.5,
                               worn_m=0.0, wear=0.8, grain=1.3, scratch=0.5, dust=1.0, sheen=0.6)
for _c in CLASS_PARAMS.values():
    _c.setdefault("wood", 0.0)
PARAM_ORDER = ["wood", "coat", "coat_r", "coat_m", "worn", "worn_r", "worn_m", "wear", "grain", "scratch", "dust", "sheen"]


# ---------------------------------------------------------------- tiny node DSL
class N:
    def __init__(self, tree):
        self.t = tree

    def node(self, kind, **props):
        n = self.t.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.t.links.new(v, sock)
        elif v is not None:
            if isinstance(v, (tuple, list)) and len(v) == 3 and sock.type == "RGBA":
                v = (*v, 1)
            sock.default_value = v

    def math(self, op, x, y=None, z=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.set(n.inputs[0], x)
        self.set(n.inputs[1], y)
        self.set(n.inputs[2], z)
        return n.outputs[0]

    def add(self, x, y): return self.math("ADD", x, y)
    def sub(self, x, y): return self.math("SUBTRACT", x, y)
    def mul(self, x, y): return self.math("MULTIPLY", x, y)
    def mx(self, x, y): return self.math("MAXIMUM", x, y)
    def mn(self, x, y): return self.math("MINIMUM", x, y)
    def sat(self, x): return self.math("ADD", x, 0.0, clamp=True)
    def inv(self, x): return self.math("SUBTRACT", 1.0, x)

    def lerp(self, x, y, f):
        return self.add(x, self.mul(self.sub(y, x), f))

    def smooth(self, v, lo, hi, to0=0.0, to1=1.0):
        n = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        self.set(n.inputs["Value"], v)
        self.set(n.inputs["From Min"], lo)
        self.set(n.inputs["From Max"], hi)
        self.set(n.inputs["To Min"], to0)
        self.set(n.inputs["To Max"], to1)
        return n.outputs[0]

    def cmix(self, x, y, f):
        n = self.node("ShaderNodeMix", data_type="RGBA")
        n.clamp_factor = True
        self.set(n.inputs["Factor_Float"] if "Factor_Float" in n.inputs else n.inputs[0], f)
        ia = [s for s in n.inputs if s.identifier == "A_Color"][0]
        ib = [s for s in n.inputs if s.identifier == "B_Color"][0]
        self.set(ia, x)
        self.set(ib, y)
        return [s for s in n.outputs if s.identifier == "Result_Color"][0]

    def cscale(self, col, f):
        n = self.node("ShaderNodeVectorMath", operation="SCALE")
        self.set(n.inputs[0], col)
        self.set(n.inputs["Scale"], f)
        return n.outputs[0]

    def dot(self, x, y):
        n = self.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
        self.set(n.inputs[0], x)
        self.set(n.inputs[1], y)
        return n.outputs["Value"]

    def mapping(self, vec, scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0)):
        n = self.node("ShaderNodeMapping")
        self.set(n.inputs["Vector"], vec)
        n.inputs["Scale"].default_value = scale
        n.inputs["Rotation"].default_value = rot
        n.inputs["Location"].default_value = loc
        return n.outputs[0]

    def noise(self, vec, scale, detail=2.0, rough=0.5, dist=0.0):
        n = self.node("ShaderNodeTexNoise")
        self.set(n.inputs["Vector"], vec)
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = dist
        return n.outputs[0]

    def voronoi(self, vec, scale, feature="F1", rand=1.0):
        n = self.node("ShaderNodeTexVoronoi", feature=feature)
        self.set(n.inputs["Vector"], vec)
        n.inputs["Scale"].default_value = scale
        n.inputs["Randomness"].default_value = rand
        return n.outputs["Distance"]

    def attr(self, name):
        n = self.node("ShaderNodeAttribute", attribute_name=name)
        return n.outputs["Fac"] if "Fac" in n.outputs else n.outputs[2]

    def sep(self, vec):
        n = self.node("ShaderNodeSeparateXYZ")
        self.set(n.inputs[0], vec)
        return n.outputs


# ---------------------------------------------------------------- decal sheets
def _font():
    for f in (r"C:\Windows\Fonts\bahnschrift.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
        if os.path.exists(f):
            return bpy.data.fonts.load(f)
    return None


CH = {"paint": (1, 0, 0), "raise": (0, 1, 0), "recess": (0, 0, 1)}


def render_sheets(cfg, work):
    """Render every decal sheet of the config to an RGB mask image.  R paint, G raised, B recessed.
    sheet: dict(name, origin(x,y,z), right(vec), up(vec), w, h, res_w, facing(vec), depth=(d0,d1), items=[...])
    item:  ("text", a, b, size, string, ch[, align]) | ("circle", a, b, r, ch) | ("ring", a, b, r, width, ch)
           | ("rect", a, b, w, h, angle_deg, ch) | ("slot", a, b, length, width, angle_deg, ch)
    """
    out = []
    main = bpy.context.window.scene if bpy.context.window else bpy.context.scene
    for sh in cfg.get("sheets", []):
        s = bpy.data.scenes.new("sheet_" + sh["name"])
        font = _font()
        mats = {}
        for k, c in CH.items():
            m = bpy.data.materials.new("ch_" + k)
            m.use_nodes = True
            nt = m.node_tree
            nt.nodes.clear()
            o = nt.nodes.new("ShaderNodeOutputMaterial")
            e = nt.nodes.new("ShaderNodeEmission")
            e.inputs[0].default_value = (*c, 1)
            nt.links.new(e.outputs[0], o.inputs[0])
            mats[k] = m
        zc = 0.0

        def link(o, k):
            nonlocal zc
            zc += 0.001
            o.location.z = zc
            o.data.materials.append(mats[k])
            s.collection.objects.link(o)

        for it in sh["items"]:
            kind = it[0]
            if kind == "text":
                _, x, y, size, string, ch = it[:6]
                cu = bpy.data.curves.new("t", "FONT")
                cu.body = string
                cu.size = size
                cu.align_x = it[6] if len(it) > 6 else "CENTER"
                cu.align_y = "CENTER"
                if font:
                    cu.font = font
                o = bpy.data.objects.new("t", cu)
                o.location = (x, y, 0)
                if len(it) > 7:
                    o.rotation_euler = (0, 0, math.radians(it[7]))
                link(o, ch)
            elif kind in ("circle", "ring"):
                x, y, r = it[1:4]
                ch = it[-1]
                me = bpy.data.meshes.new("c")
                vs, fs = [], []
                seg = 48
                r0 = r - it[4] if kind == "ring" else 0.0
                for i in range(seg):
                    an = 2 * math.pi * i / seg
                    vs.append((math.cos(an) * r, math.sin(an) * r, 0))
                    vs.append((math.cos(an) * r0, math.sin(an) * r0, 0))
                for i in range(seg):
                    j = (i + 1) % seg
                    fs.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
                me.from_pydata(vs, [], fs)
                o = bpy.data.objects.new("c", me)
                o.location = (x, y, 0)
                link(o, ch)
            elif kind in ("rect", "slot"):
                _, x, y, w, h, ang, ch = it
                me = bpy.data.meshes.new("r")
                if kind == "rect":
                    vs = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
                    fs = [(0, 1, 2, 3)]
                else:  # stadium
                    vs = []
                    r = h / 2
                    half = max(0.0, w / 2 - r)
                    for i in range(17):
                        an = -math.pi / 2 + math.pi * i / 16
                        vs.append((half + math.cos(an) * r, math.sin(an) * r, 0))
                    for i in range(17):
                        an = math.pi / 2 + math.pi * i / 16
                        vs.append((-half + math.cos(an) * r, math.sin(an) * r, 0))
                    fs = [tuple(range(len(vs)))]
                me.from_pydata(vs, [], fs)
                o = bpy.data.objects.new("r", me)
                o.location = (x, y, 0)
                o.rotation_euler = (0, 0, math.radians(ang))
                link(o, ch)
        cd = bpy.data.cameras.new("sc")
        cd.type = "ORTHO"
        cd.ortho_scale = max(sh["w"], sh["h"])
        cam = bpy.data.objects.new("sc", cd)
        cam.location = (sh["w"] / 2, sh["h"] / 2, 10)
        s.collection.objects.link(cam)
        s.camera = cam
        w = bpy.data.worlds.new("black")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
        s.world = w
        s.render.engine = "CYCLES"
        s.cycles.device = main.cycles.device
        s.cycles.samples = 16
        s.cycles.use_denoising = False
        s.view_settings.view_transform = "Standard"
        s.render.resolution_x = sh.get("res_w", 4096)
        s.render.resolution_y = max(16, int(round(s.render.resolution_x * sh["h"] / sh["w"] / 16)) * 16)
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_mode = "RGB"
        path = os.path.join(work, "sheet_%s.png" % sh["name"])
        s.render.filepath = path
        bpy.ops.render.render(write_still=True, scene=s.name)
        img = bpy.data.images.load(path)
        img.colorspace_settings.name = "Non-Color"
        out.append((sh, img))
        bpy.data.scenes.remove(s)
    return out


# ---------------------------------------------------------------- the surface group
def build_group(cfg, sheets):
    unit = cfg.get("unit", 0.01)       # metres per object unit
    k = 0.01 / unit                    # object units per cm
    g = bpy.data.node_groups.new("DetailSurface", "ShaderNodeTree")
    itf = g.interface
    for name in PARAM_ORDER:
        st = "NodeSocketColor" if name in ("coat", "worn") else "NodeSocketFloat"
        itf.new_socket(name, in_out="INPUT", socket_type=st)
    for name, st in (("Base", "NodeSocketColor"), ("ORM", "NodeSocketColor"), ("Normal", "NodeSocketVector")):
        itf.new_socket(name, in_out="OUTPUT", socket_type=st)
    n = N(g)
    gi = n.node("NodeGroupInput").outputs
    go = n.node("NodeGroupOutput").inputs

    opos = n.node("ShaderNodeAttribute", attribute_name="opos")
    P = n.mapping(opos.outputs["Vector"], scale=(1 / k, 1 / k, 1 / k))    # cm, assembled position
    geo = n.node("ShaderNodeNewGeometry")
    Nn = geo.outputs["Normal"]
    Nt = geo.outputs["True Normal"]

    bev = n.node("ShaderNodeBevel", samples=8)
    bev.inputs["Radius"].default_value = cfg.get("bevel", 0.0005)
    bevw = n.node("ShaderNodeBevel", samples=6)
    bevw.inputs["Radius"].default_value = cfg.get("wear_radius", 0.0009)
    ao_s = n.node("ShaderNodeAmbientOcclusion", samples=8)
    ao_s.inputs["Distance"].default_value = 0.004
    ao_l = n.node("ShaderNodeAmbientOcclusion", samples=16)
    ao_l.inputs["Distance"].default_value = cfg.get("ao_dist", 0.025)

    n_big = n.noise(P, 0.18, 3, 0.5)
    n_med = n.noise(P, 1.3, 4, 0.55)
    n_fine = n.noise(P, 22.0, 2, 0.5)
    n_wear = n.noise(P, 3.5, 6, 0.72)
    n_scuff = n.noise(P, 0.7, 7, 0.75, 0.6)

    stipple = n.attr("stipple")
    lathe = n.attr("lathe")
    bare = n.attr("bare")

    # ---- masks
    edge_any = n.inv(n.dot(bevw.outputs["Normal"], Nn))
    edge = n.smooth(edge_any, 0.015, 0.16)
    convex = n.smooth(ao_s.outputs["AO"], 0.80, 0.97)
    expo = n.smooth(ao_l.outputs["AO"], 0.55, 0.9)                       # how reachable the surface is
    cavity = n.inv(n.smooth(ao_l.outputs["AO"], 0.2, 0.7))
    w_edge = n.mul(n.mul(edge, convex), gi["wear"])
    wear = n.smooth(n.mul(w_edge, n.add(0.05, n.mul(n_wear, 1.3))), 0.52, 0.72)
    scuff = n.mul(n.mul(n.smooth(n_scuff, 0.6, 0.78), expo), n.mul(gi["wear"], 0.3))
    streak = n.noise(n.mapping(P, scale=(9, 0.12, 9), rot=(0.02, 0.03, 0.05)), 1.0, 5, 0.65)
    streak = n.mul(n.smooth(streak, 0.5, 0.78), n.mul(expo, gi["sheen"]))
    speck = n.noise(P, 34.0, 1, 0.5)
    sA = n.noise(n.mapping(P, scale=(26, 0.35, 26), rot=(0.05, 0.12, 0.07)), 1.0, 3, 0.6)
    sB = n.noise(n.mapping(P, scale=(22, 0.4, 22), rot=(0.5, 0.3, 0.45), loc=(7, 3, 1)), 1.0, 3, 0.6)
    sC = n.noise(n.mapping(P, scale=(24, 0.5, 24), rot=(-0.4, 0.2, -0.35), loc=(2, 9, 4)), 1.0, 2, 0.6)
    scr = n.mx(n.mx(n.smooth(sA, 0.71, 0.74), n.smooth(sB, 0.715, 0.74)), n.smooth(sC, 0.72, 0.745))
    scr = n.mul(n.mul(scr, gi["scratch"]), n.mul(expo, n.smooth(n_scuff, 0.3, 0.55)))
    wear_all = n.sat(n.mx(n.mx(wear, n.mul(scr, 0.75)), scuff))
    wear_all = n.mx(wear_all, bare)
    dirt = n.mul(n.smooth(n.mul(cavity, n.add(0.4, n.mul(n_med, 1.2))), 0.3, 0.85), gi["dust"])
    dust_top = n.mul(n.mul(n.smooth(n.sep(Nt)[2], 0.5, 1.0), n.smooth(n_scuff, 0.4, 0.7)), n.mul(gi["dust"], 0.10))
    dirt = n.sat(n.add(dirt, dust_top))
    # oily finger smudges lower the roughness in broad patches
    smudge = n.mul(n.smooth(n.noise(P, 0.45, 5, 0.6, 1.2), 0.5, 0.7), gi["sheen"])

    # ---- decal sheets
    paint = None
    raise_ = None
    recess = None
    sx = n.sep(P)
    for sh, img in sheets:
        O = sh["origin"]
        rel = n.node("ShaderNodeVectorMath", operation="SUBTRACT")
        n.set(rel.inputs[0], P)
        rel.inputs[1].default_value = O
        u = n.math("DIVIDE", n.dot(rel.outputs[0], tuple(sh["right"])), sh["w"])
        v = n.math("DIVIDE", n.dot(rel.outputs[0], tuple(sh["up"])), sh["h"])
        cmb = n.node("ShaderNodeCombineXYZ")
        n.set(cmb.inputs[0], u)
        n.set(cmb.inputs[1], v)
        tex = n.node("ShaderNodeTexImage", image=img, extension="CLIP", interpolation="Cubic")
        n.set(tex.inputs[0], cmb.outputs[0])
        m = n.smooth(n.dot(Nt, tuple(sh["facing"])), 0.80, 0.9)
        d = n.dot(P, tuple(sh["facing"]))
        d0, d1 = sh.get("depth", (-1e4, 1e4))
        m = n.mul(m, n.mul(n.math("GREATER_THAN", d, d0), n.math("LESS_THAN", d, d1)))
        rgb = n.node("ShaderNodeSeparateColor")
        n.set(rgb.inputs[0], tex.outputs[0])
        pr = n.mul(rgb.outputs[0], m)
        pg = n.mul(rgb.outputs[1], m)
        pb = n.mul(rgb.outputs[2], m)
        paint = pr if paint is None else n.mx(paint, pr)
        raise_ = pg if raise_ is None else n.mx(raise_, pg)
        recess = pb if recess is None else n.mx(recess, pb)
    if paint is None:
        paint = raise_ = recess = n.math("ADD", 0.0, 0.0)

    # ---- base colour
    tone = n.mul(n.add(0.6, n.mul(n_big, 0.8)), n.add(0.75, n.mul(n_med, 0.5)))
    tone = n.mul(tone, n.add(0.82, n.mul(speck, 0.36)))
    tone = n.add(tone, n.mul(streak, 0.5))
    base = n.cscale(gi["coat"], tone)
    # birch laminate: plies stacked across the gun (X), so the layers show as contour figure on the flats and as
    # tight glue lines wherever the surface curves through them
    warp = n.add(n.mul(n.sub(n.noise(P, 0.13, 2, 0.5), 0.5), 2.4), n.mul(n.sub(n.noise(P, 0.9, 3, 0.5), 0.5), 0.08))
    ply = n.math("DIVIDE", n.add(sx[0], warp), 0.16)
    fl = n.math("FLOOR", ply)
    fr = n.sub(ply, fl)
    glue = n.inv(n.smooth(n.mn(fr, n.inv(fr)), 0.0, 0.10))
    wn_ = n.node("ShaderNodeTexWhiteNoise", noise_dimensions="1D")
    n.set(wn_.inputs["W"], fl)
    fibre = n.noise(n.mapping(P, scale=(26, 1.1, 26)), 1.0, 3, 0.6)
    pores = n.smooth(n.noise(n.mapping(P, scale=(70, 3.5, 70)), 1.0, 2, 0.5), 0.60, 0.74)
    wtone = n.sat(n.add(n.mul(wn_.outputs["Value"], 0.40), n.sub(n.mul(fibre, 1.15), 0.33)))
    wcol = n.cmix((0.43, 0.155, 0.036), (0.17, 0.05, 0.012), wtone)
    wcol = n.cmix(wcol, (0.05, 0.018, 0.007), n.mul(glue, 0.6))
    wcol = n.cscale(wcol, n.mul(n.sub(1.0, n.mul(pores, 0.3)), n.add(0.8, n.mul(n_big, 0.4))))
    base = n.cmix(base, wcol, gi["wood"])
    base = n.cmix(base, gi["worn"], wear_all)
    base = n.cmix(base, (0.012, 0.011, 0.010), n.mul(recess, 0.85))            # engraving shadow / oil
    paint_m = n.mul(paint, n.add(0.55, n.mul(n_wear, 0.6)))
    base = n.cmix(base, (0.70, 0.70, 0.66), n.sat(paint_m))
    base = n.cmix(base, (0.085, 0.075, 0.062), n.mul(dirt, 0.5))
    base = n.cscale(base, n.lerp(1.0, 0.6, cavity))

    # ---- roughness / metallic
    rough = n.add(gi["coat_r"], n.add(n.mul(n.sub(n_med, 0.5), 0.3), n.mul(n.sub(speck, 0.5), 0.12)))
    rough = n.sub(rough, n.mul(streak, 0.2))
    rough = n.sub(rough, n.mul(smudge, 0.16))
    rough = n.lerp(rough, n.add(gi["worn_r"], n.mul(n.sub(n_wear, 0.5), 0.2)), wear_all)
    rough = n.lerp(rough, 0.6, n.sat(paint_m))
    rough = n.lerp(rough, 0.92, n.mul(dirt, 0.8))
    rough = n.math("MINIMUM", n.mx(rough, 0.12), 1.0)
    metal = n.lerp(gi["coat_m"], gi["worn_m"], wear_all)
    metal = n.mul(metal, n.inv(n.sat(paint_m)))
    metal = n.sat(n.mul(metal, n.inv(n.mul(dirt, 0.75))))
    ao = n.smooth(ao_l.outputs["AO"], 0.15, 0.95)

    # ---- height (roughly millimetres * 2)
    grain = n.mul(n.sub(n_fine, 0.5), n.mul(gi["grain"], 0.22))
    vor = n.voronoi(P, cfg.get("stipple_scale", 9.0))
    stip = n.mul(n.smooth(vor, 0.15, 0.5, 1.0, 0.0), n.mul(stipple, 0.9))
    lat = n.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y")
    n.set(lat.inputs["Vector"], P)
    lat.inputs["Scale"].default_value = cfg.get("lathe_scale", 5.0)
    lat.inputs["Distortion"].default_value = 0.0
    lathe_h = n.mul(n.mul(lat.outputs[1] if len(lat.outputs) > 1 else lat.outputs[0], lathe), 0.10)
    h = n.add(grain, stip)
    h = n.add(h, n.mul(gi["wood"], n.sub(n.mul(n.sub(fibre, 0.5), 0.14), n.add(n.mul(glue, 0.10), n.mul(pores, 0.16)))))
    h = n.add(h, lathe_h)
    h = n.sub(h, n.mul(wear_all, 0.10))
    h = n.sub(h, n.mul(scr, 0.25))
    h = n.add(h, n.mul(raise_, 0.7))
    h = n.sub(h, n.mul(recess, 0.9))
    h = n.add(h, n.mul(dirt, n.mul(n.sub(n_fine, 0.5), 0.3)))
    bump = n.node("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = cfg.get("bump_dist", 0.0005)
    n.set(bump.inputs["Height"], h)
    n.set(bump.inputs["Normal"], bev.outputs["Normal"])

    orm = n.node("ShaderNodeCombineColor")
    n.set(orm.inputs[0], ao)
    n.set(orm.inputs[1], rough)
    n.set(orm.inputs[2], metal)
    g.links.new(base, go["Base"])
    g.links.new(orm.outputs[0], go["ORM"])
    g.links.new(bump.outputs[0], go["Normal"])
    return g


def make_bake_material(name, group, params):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    gn = nt.nodes.new("ShaderNodeGroup")
    gn.node_tree = group
    gn.name = "G"
    for k in PARAM_ORDER:
        v = params[k]
        gn.inputs[k].default_value = (*v, 1) if isinstance(v, tuple) else v
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "OUT"
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "EM"
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.name = "BS"
    nt.links.new(gn.outputs["Normal"], bs.inputs["Normal"])
    img = nt.nodes.new("ShaderNodeTexImage")
    img.name = "TARGET"
    return m


def set_pass(m, pass_name, image):
    nt = m.node_tree
    gn, out, em, bs, tg = (nt.nodes[k] for k in ("G", "OUT", "EM", "BS", "TARGET"))
    for l in list(out.inputs[0].links):
        nt.links.remove(l)
    for l in list(em.inputs[0].links):
        nt.links.remove(l)
    if pass_name == "normal":
        nt.links.new(bs.outputs[0], out.inputs[0])
    else:
        nt.links.new(gn.outputs["Base" if pass_name == "base" else "ORM"], em.inputs[0])
        nt.links.new(em.outputs[0], out.inputs[0])
    tg.image = image
    for nd in nt.nodes:
        nd.select = False
    tg.select = True
    nt.nodes.active = tg


def make_final_material(name, imgs, glass=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    tb = nt.nodes.new("ShaderNodeTexImage")
    tb.image = imgs["base"]
    nt.links.new(tb.outputs[0], bs.inputs["Base Color"])
    to = nt.nodes.new("ShaderNodeTexImage")
    to.image = imgs["orm"]
    sp = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(to.outputs[0], sp.inputs[0])
    nt.links.new(sp.outputs[1], bs.inputs["Roughness"])
    nt.links.new(sp.outputs[2], bs.inputs["Metallic"])
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = imgs["normal"]
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tn.outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bs.inputs["Normal"])
    grp = bpy.data.node_groups.get("glTF Material Output")
    if not grp:
        grp = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        grp.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    gn = nt.nodes.new("ShaderNodeGroup")
    gn.node_tree = grp
    nt.links.new(sp.outputs[0], gn.inputs["Occlusion"])
    return m
