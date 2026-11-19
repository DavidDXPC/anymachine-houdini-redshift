"""UsdPreviewSurface and Redshift Solaris terminals for kit finishes."""
from pxr import Gf, Sdf, UsdShade

T = Sdf.ValueTypeNames
PALETTE = {
    "enamel": ("536e71", 0.22, 0.34), "metal": ("a0a6a5", 0.9, 0.31),
    "dark": ("272d32", 0.30, 0.42), "wood": ("ad8356", 0., 0.47),
    "rubber": ("242526", 0., 0.78), "accent": ("db9a49", 0.16, 0.36),
    "ceramic": ("e9e1d2", 0., 0.21), "glass": ("eaf7f8", 0., 0.11),
    "screen": ("1b3138", 0.1, 0.22),
}


def ap1(rgb):
    matrix = ((.613097, .339523, .047380), (.070194, .916354, .013452), (.020616, .109570, .869815))
    return tuple(sum(a*b for a,b in zip(row,rgb)) for row in matrix)


def hex_color(value):
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError("Palette colours must use six sRGB hex digits")
    srgb = [int(value[i:i+2],16)/255 for i in (0,2,4)]
    return ap1([v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in srgb])


def shader(stage,path,name):
    node = UsdShade.Shader.Define(stage,path)
    node.CreateIdAttr(name)
    return node


def material(stage,path,color,metal,rough,emission=(0,0,0),transmission=0,
             textures=None,alpha=1,alpha_mode="OPAQUE",cutoff=.5):
    mat = UsdShade.Material.Define(stage,path)
    rs = shader(stage,path+"/Standard","redshift::StandardMaterial")
    usd = shader(stage,path+"/Preview","UsdPreviewSurface")
    base=Gf.Vec3f(*color)
    for node,name,value,kind in (
        (rs,"base_color",base,T.Color3f),(usd,"diffuseColor",base,T.Color3f),
        (rs,"metalness",metal,T.Float),(usd,"metallic",metal,T.Float),
        (rs,"refl_roughness",rough,T.Float),(usd,"roughness",rough,T.Float),
        (rs,"emission_color",Gf.Vec3f(*emission),T.Color3f),
        (rs,"emission_weight",float(max(emission)>0),T.Float),
        (usd,"emissiveColor",Gf.Vec3f(*emission),T.Color3f),
        (rs,"refr_weight",transmission,T.Float),
    ):
        node.CreateInput(name,kind).Set(value)
    if alpha_mode != "OPAQUE":
        usd.CreateInput("opacity",T.Float).Set(alpha)
        rs.CreateInput("opacity_color",T.Color3f).Set(Gf.Vec3f(alpha))
        if alpha_mode=="MASK":
            usd.CreateInput("opacityThreshold",T.Float).Set(cutoff)
    if textures:
        st = shader(stage,path+"/UV","UsdPrimvarReader_float2")
        st.CreateInput("varname",T.Token).Set("st")
        for key,filename in textures.items():
            raw = key in ("orm","normal")
            tex = shader(stage,path+"/"+key,"UsdUVTexture")
            tex.CreateInput("file",T.Asset).Set(Sdf.AssetPath(filename))
            tex.CreateInput("sourceColorSpace",T.Token).Set("raw" if raw else "sRGB")
            tex.CreateInput("wrapS",T.Token).Set("repeat")
            tex.CreateInput("wrapT",T.Token).Set("repeat")
            tex.CreateInput("st",T.Float2).ConnectToSource(st.CreateOutput("result",T.Float2))
            rs_tex=shader(stage,path+"/RS_"+key,"redshift::TextureSampler")
            rs_tex.CreateInput("tex0",T.Asset).Set(Sdf.AssetPath(filename))
            rs_tex.CreateInput("tex0_colorSpace",T.String).Set("Raw" if raw else "sRGB")
            if key=="base":
                tex.CreateInput("scale",T.Float4).Set(Gf.Vec4f(*color, alpha))
                usd.GetInput("diffuseColor").ConnectToSource(tex.CreateOutput("rgb",T.Float3))
                rs.GetInput("base_color").ConnectToSource(rs_tex.CreateOutput("outColor",T.Color3f))
                if alpha_mode!="OPAQUE":
                    usd.GetInput("opacity").ConnectToSource(tex.CreateOutput("a",T.Float))
                    rs.GetInput("opacity_color").ConnectToSource(rs_tex.CreateOutput("outA",T.Float))
            elif key=="orm":
                tex.CreateInput("scale",T.Float4).Set(Gf.Vec4f(1,rough,metal,1))
                usd.GetInput("roughness").ConnectToSource(tex.CreateOutput("g",T.Float))
                usd.GetInput("metallic").ConnectToSource(tex.CreateOutput("b",T.Float))
                splitter=shader(stage,path+"/Channels","redshift::RSColorSplitter")
                splitter.CreateInput("input",T.Color4f).ConnectToSource(rs_tex.CreateOutput("outColor",T.Color3f))
                rs.GetInput("metalness").ConnectToSource(splitter.CreateOutput("outB",T.Float))
                rs.GetInput("refl_roughness").ConnectToSource(splitter.CreateOutput("outG",T.Float))
            elif key=="normal":
                tex.CreateInput("scale",T.Float4).Set(Gf.Vec4f(2,2,2,1))
                tex.CreateInput("bias",T.Float4).Set(Gf.Vec4f(-1,-1,-1,0))
                usd.CreateInput("normal",T.Normal3f).ConnectToSource(tex.CreateOutput("rgb",T.Float3))
                bump=shader(stage,path+"/Bump","redshift::BumpMap")
                bump.CreateInput("inputType",T.Token).Set("1")
                bump.CreateInput("input",T.Color3f).ConnectToSource(rs_tex.CreateOutput("outColor",T.Color3f))
                rs.CreateInput("bump_input",T.Int).ConnectToSource(bump.CreateOutput("out",T.Vector3f))
    terminal=shader(stage,path+"/Output","redshift_usd_material")
    terminal.CreateInput("Surface",T.Token).ConnectToSource(rs.CreateOutput("outColor",T.Token))
    mat.CreateSurfaceOutput("Redshift").ConnectToSource(terminal.CreateOutput("Shader",T.Token))
    mat.CreateSurfaceOutput().ConnectToSource(usd.CreateOutput("surface",T.Token))
    return mat


def palette(stage,root,style):
    colors=style.get("palette",{})
    unknown=set(colors)-set(PALETTE)
    if unknown:
        raise ValueError("Unknown palette roles: "+", ".join(sorted(unknown)))
    wear=float(style.get("wear",0))
    if not 0<=wear<=1:
        raise ValueError("wear must be in [0,1]")
    result={}
    for name,(hex_value,metal,rough) in PALETTE.items():
        color=hex_color(colors.get(name,hex_value))
        result[name]=material(stage,root+"/"+name,color,metal,min(1.,rough+.15*wear),
                              color if name=="screen" else (0,0,0),.95 if name=="glass" else 0)
    return result

