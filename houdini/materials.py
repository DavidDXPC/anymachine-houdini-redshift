"""Solaris materials for the Redshift Hydra delegate and the viewport."""
from pathlib import Path

from pxr import Gf, Sdf, Tf, UsdGeom, UsdShade

T = Sdf.ValueTypeNames
PALETTE = {
    "canvas": ((0.12, 0.19, 0.10), 0.0, 0.83),
    "lining": ((0.08, 0.075, 0.065), 0.0, 0.78),
    "webbing": ((0.035, 0.031, 0.026), 0.0, 0.86),
    "steel": ((0.43, 0.45, 0.47), 0.92, 0.31),
    "aluminium": ((0.60, 0.62, 0.65), 0.94, 0.29),
    "rubber": ((0.025, 0.024, 0.022), 0.0, 0.73),
    "ceramic": ((0.77, 0.73, 0.65), 0.0, 0.26),
    "display": ((0.012, 0.024, 0.038), 0.05, 0.16),
    "coated": ((0.075, 0.092, 0.10), 0.18, 0.35),
    "brass": ((0.61, 0.39, 0.12), 0.88, 0.29),
    "orange": ((0.80, 0.18, 0.02), 0.04, 0.43),
    "white": ((0.76, 0.76, 0.72), 0.02, 0.41),
}
ALIASES = {
    "galv": "steel", "chrome": "aluminium", "stainless": "steel",
    "tire": "rubber", "tyre": "rubber", "void": "rubber", "dark": "rubber",
    "paintw": "white", "black": "rubber", "glass": "display",
}


def finish(name):
    from .industrial.lighting import FLAT, LIT

    key = name.lower()
    if key.startswith("lit_") and key[4:] in LIT:
        lamp = LIT[key[4:]]
        return dict(base=lamp["off"], metal=0, rough=lamp["rough"],
                    emission=lamp["rgb"], emission_weight=lamp["strength"])
    key = key.removesuffix("_t")
    base, metal, rough = PALETTE.get(ALIASES.get(key, key), ((0.37, 0.39, 0.39), 0.1, 0.47))
    return dict(base=FLAT.get(key, base), metal=metal, rough=rough)


def _shader(stage, path, node_id):
    node = UsdShade.Shader.Define(stage, path)
    node.CreateIdAttr(node_id)
    return node


def _texture(stage, path, filename, uv, space):
    tex = _shader(stage, path, "UsdUVTexture")
    tex.CreateInput("file", T.Asset).Set(Sdf.AssetPath(Path(filename).as_posix()))
    tex.CreateInput("sourceColorSpace", T.Token).Set(space)
    tex.CreateInput("wrapS", T.Token).Set("repeat")
    tex.CreateInput("wrapT", T.Token).Set("repeat")
    tex.CreateInput("st", T.Float2).ConnectToSource(uv)
    return tex


def _rs_texture(stage, path, filename, color_space):
    tex = _shader(stage, path, "redshift::TextureSampler")
    tex.CreateInput("tex0", T.Asset).Set(Sdf.AssetPath(Path(filename).as_posix()))
    tex.CreateInput("tex0_colorSpace", T.String).Set(color_space)
    return tex.CreateOutput("outColor", T.Color3f)


def material(stage, name, spec):
    """Author the Solaris RS material terminal and a portable viewport preview."""
    UsdGeom.Scope.Define(stage, "/Machine/Looks")
    path = "/Machine/Looks/" + Tf.MakeValidIdentifier(name)
    mat = UsdShade.Material.Define(stage, path)
    base = Gf.Vec3f(*spec["base"])
    emission = Gf.Vec3f(*spec.get("emission", (0, 0, 0)))
    weight = spec.get("emission_weight", 0)
    preview = _shader(stage, path + "/Preview", "UsdPreviewSurface")
    color = preview.CreateInput("diffuseColor", T.Color3f)
    color.Set(base)
    metal = preview.CreateInput("metallic", T.Float)
    metal.Set(spec["metal"])
    rough = preview.CreateInput("roughness", T.Float)
    rough.Set(spec["rough"])
    preview.CreateInput("emissiveColor", T.Color3f).Set(emission * weight)
    mat.CreateSurfaceOutput().ConnectToSource(preview.CreateOutput("surface", T.Token))
    if any(spec.get(kind + "_texture") for kind in ("base", "orm", "normal")):
        uv = _shader(stage, path + "/UV", "UsdPrimvarReader_float2")
        uv.CreateInput("varname", T.String).Set("st")
        result = uv.CreateOutput("result", T.Float2)
        if spec.get("base_texture"):
            tex = _texture(stage, path + "/Albedo", spec["base_texture"], result, "sRGB")
            color.ConnectToSource(tex.CreateOutput("rgb", T.Float3))
        if spec.get("orm_texture"):
            tex = _texture(stage, path + "/ORM", spec["orm_texture"], result, "raw")
            rough.ConnectToSource(tex.CreateOutput("g", T.Float))
            metal.ConnectToSource(tex.CreateOutput("b", T.Float))
        if spec.get("normal_texture"):
            tex = _texture(stage, path + "/Normal", spec["normal_texture"], result, "raw")
            tex.CreateInput("scale", T.Float4).Set((2, 2, 2, 1))
            tex.CreateInput("bias", T.Float4).Set((-1, -1, -1, 0))
            preview.CreateInput("normal", T.Normal3f).ConnectToSource(tex.CreateOutput("rgb", T.Float3))
    rs = _shader(stage, path + "/RS_Standard", "redshift::StandardMaterial")
    rs_color = rs.CreateInput("base_color", T.Color3f)
    rs_color.Set(base)
    rs_metal = rs.CreateInput("metalness", T.Float)
    rs_metal.Set(spec["metal"])
    rs_rough = rs.CreateInput("refl_roughness", T.Float)
    rs_rough.Set(spec["rough"])
    if spec.get("transmission"):
        rs.CreateInput("refr_weight", T.Float).Set(spec["transmission"])
        preview.CreateInput("opacity", T.Float).Set(0.22)
    rs.CreateInput("emission_color", T.Color3f).Set(emission)
    rs.CreateInput("emission_weight", T.Float).Set(weight)
    if spec.get("base_texture"):
        tex = _rs_texture(stage, path + "/RS_Albedo", spec["base_texture"], "sRGB")
        rs_color.ConnectToSource(tex)
    if spec.get("orm_texture"):
        orm = _rs_texture(stage, path + "/RS_ORM", spec["orm_texture"], "Raw")
        split = _shader(stage, path + "/RS_Channels", "redshift::RSColorSplitter")
        split.CreateInput("input", T.Color4f).ConnectToSource(orm)
        rs_rough.ConnectToSource(split.CreateOutput("outG", T.Float))
        rs_metal.ConnectToSource(split.CreateOutput("outB", T.Float))
    if spec.get("normal_texture"):
        texture = _rs_texture(stage, path + "/RS_Normal", spec["normal_texture"], "Raw")
        bump = _shader(stage, path + "/RS_Bump", "redshift::BumpMap")
        bump.CreateInput("inputType", T.Token).Set("1")
        bump.CreateInput("input", T.Color3f).ConnectToSource(texture)
        rs.CreateInput("bump_input", T.Int).ConnectToSource(bump.CreateOutput("out", T.Vector3f))
    terminal = _shader(stage, path + "/RS_Output", "redshift_usd_material")
    terminal.CreateInput("Surface", T.Token).ConnectToSource(rs.CreateOutput("outColor", T.Token))
    mat.CreateSurfaceOutput("Redshift").ConnectToSource(terminal.CreateOutput("Shader", T.Token))
    return mat
