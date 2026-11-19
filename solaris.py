"""AnyScene set dressing for Y-up, metre-based Solaris stages."""
import argparse
import copy
import json
import math
import os
from pathlib import Path

from pxr import Ar, Gf, Sdf, Tf, Usd, UsdGeom, UsdLux, UsdShade


PRESET_DIR = Path(__file__).resolve().with_name("solaris_presets")
ROOT = "/World/Set"
T = Sdf.ValueTypeNames
SURFACES = {
    "plaster": ((.36,.34,.29), .83, 0), "concrete": ((.15,.15,.14), .76, 0),
    "asphalt": ((.045,.048,.049), .28, 0), "steel": ((.35,.39,.40), .31, .82),
    "wood": ((.26,.135,.067), .5, 0), "glass": ((.70,.86,.89), .12, 0),
    "fabric": ((.115,.14,.15), .88, 0), "ceramic": ((.66,.61,.52), .3, 0),
    "paint": ((.27,.33,.29), .51, .16), "proxy": ((.43,.38,.24), .64, .06),
}


def presets():
    return tuple(p.stem for p in sorted(PRESET_DIR.glob("*.json")))


def specification(name):
    if name not in presets():
        raise ValueError(f"Unknown set preset {name!r}; choose one of {', '.join(presets())}")
    return json.loads((PRESET_DIR / (name + ".json")).read_text(encoding="utf-8"))


def vec(values, n=3, positive=False):
    if isinstance(values,(str,bytes)) or len(values)!=n:
        raise ValueError(f"Expected {n} coordinates: {values!r}")
    out=tuple(float(v) for v in values)
    if not all(math.isfinite(v) and (not positive or v>0) for v in out):
        raise ValueError(f"Invalid coordinates: {values!r}")
    return out


def material(stage, label, values):
    path=ROOT+"/Looks/"+Tf.MakeValidIdentifier(label)
    m=UsdShade.Material.Define(stage,path)
    color=Gf.Vec3f(*vec(values[0]))
    rough,metal=map(float,values[1:])
    preview=UsdShade.Shader.Define(stage,path+"/Preview")
    preview.CreateIdAttr("UsdPreviewSurface")
    for key,t,value in (("diffuseColor",T.Color3f,color),("roughness",T.Float,rough),("metallic",T.Float,metal)):
        preview.CreateInput(key,t).Set(value)
    m.CreateSurfaceOutput().ConnectToSource(preview.CreateOutput("surface",T.Token))
    rs=UsdShade.Shader.Define(stage,path+"/Standard")
    rs.CreateIdAttr("redshift::StandardMaterial")
    for key,t,value in (("base_color",T.Color3f,color),("refl_roughness",T.Float,rough),("metalness",T.Float,metal)):
        rs.CreateInput(key,t).Set(value)
    if label=="glass":
        preview.CreateInput("opacity",T.Float).Set(.18)
        rs.CreateInput("refr_weight",T.Float).Set(1.)
    terminal=UsdShade.Shader.Define(stage,path+"/Output")
    terminal.CreateIdAttr("redshift_usd_material")
    terminal.CreateInput("Surface",T.Token).ConnectToSource(rs.CreateOutput("outColor",T.Token))
    m.CreateSurfaceOutput("Redshift").ConnectToSource(terminal.CreateOutput("Shader",T.Token))
    return m


def _bind(geom,materials,key):
    if key not in materials:
        raise ValueError(f"Unknown set material {key!r}")
    UsdShade.MaterialBindingAPI.Apply(geom.GetPrim()).Bind(materials[key])


def shape(stage, path, dims, kind, materials, key):
    w,h,d=vec(dims,positive=True)
    if kind=="box":
        m=UsdGeom.Cube.Define(stage,path)
        m.CreateSizeAttr(1.)
    elif kind in ("cylinder","sphere"):
        m=(UsdGeom.Cylinder if kind=="cylinder" else UsdGeom.Sphere).Define(stage,path)
        m.CreateRadiusAttr(.5)
        if kind=="cylinder":
            m.CreateHeightAttr(1.)
            m.CreateAxisAttr("Y")
    else:
        raise ValueError(f"Unknown shape {kind!r}")
    m.AddTranslateOp().Set((0,h/2,0))
    m.AddScaleOp().Set((w,h,d))
    _bind(m,materials,key)


def _layout(parent, obj):
    parent.AddTranslateOp().Set(vec(obj.get("at",(0,0,0))))
    yaw=float(obj.get("yaw",0))
    if not math.isfinite(yaw):
        raise ValueError("Yaw must be finite")
    if yaw:
        parent.AddRotateYOp().Set(yaw)


def asset_path(key, obj, spec, base):
    supplied=obj.get("file") or spec.get("assets",{}).get(key)
    if supplied:
        p=(base/supplied).resolve()
        if not p.is_file() or p.suffix.lower() not in (".usd",".usda",".usdc",".usdz"):
            raise ValueError(f"Missing or unsupported explicit USD asset for {key}: {p}")
        return p
    for ext in (".usd",".usdc",".usda",".usdz"):
        p=base/"assets"/(key+ext)
        if p.is_file():
            return p.resolve()
    return None


def fit_reference(stage,path,file,obj,layer_dir):
    source=Usd.Stage.Open(os.fspath(file))
    root=source.GetDefaultPrim() if source else None
    if not root:
        raise ValueError(f"USD model needs a default prim: {file.name}")
    authored=str(file)
    if layer_dir:
        try:
            authored=os.path.relpath(file,layer_dir)
        except ValueError:  # Distinct Windows volumes.
            pass
    outer=UsdGeom.Xform.Define(stage,path+"/Fit")
    axis=UsdGeom.GetStageUpAxis(source)
    units=UsdGeom.GetStageMetersPerUnit(source)
    bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),["default","render","proxy"]).ComputeWorldBound(root).ComputeAlignedRange()
    if bounds.IsEmpty():
        raise ValueError(f"Empty bound for {file.name}")
    lo,hi=bounds.GetMin(),bounds.GetMax()
    if axis==UsdGeom.Tokens.z:
        lo,hi=Gf.Vec3d(lo[0],lo[2],-hi[1]),Gf.Vec3d(hi[0],hi[2],-lo[1])
    span=(hi-lo)*units
    factor=units
    if obj.get("fit","height")!="native":
        dims=vec(obj["dims"],positive=True)
        if obj.get("fit")=="max":
            measured,wanted=max(span),max(dims)
        else:
            measured,wanted=span[1],dims[1]
        if measured<=0:
            raise ValueError(f"Cannot normalise flat asset {file.name}")
        factor*=wanted/measured
    center=Gf.Vec3d((lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2)
    outer.AddTranslateOp().Set(-center*factor)
    outer.AddScaleOp().Set((factor,)*3)
    if axis==UsdGeom.Tokens.z:
        outer.AddRotateXOp().Set(-90)
    child=UsdGeom.Xform.Define(stage,path+"/Fit/Asset")
    child.GetPrim().GetReferences().AddReference(authored.replace(os.sep,"/"))
    child.GetPrim().SetInstanceable(True)


def practical(stage,path,item):
    kind=item.get("kind","area")
    if kind=="area":
        light=UsdLux.RectLight.Define(stage,path)
        w,h=vec(item.get("size",(1.,.5)),2,True)
        light.CreateWidthAttr(w)
        light.CreateHeightAttr(h)
    elif kind=="point":
        light=UsdLux.SphereLight.Define(stage,path)
        light.CreateRadiusAttr(float(item.get("radius",.06)))
    elif kind=="dome":
        light=UsdLux.DomeLight.Define(stage,path)
    elif kind=="sun":
        light=UsdLux.DistantLight.Define(stage,path)
        light.CreateAngleAttr(float(item.get("angle",2)))
    else:
        raise ValueError(f"Unknown light kind {kind!r}")
    light.CreateIntensityAttr(float(item.get("intensity",1)))
    light.CreateColorAttr(Gf.Vec3f(*vec(item.get("color",(1,1,1)))))
    eye=Gf.Vec3d(*vec(item.get("at",(0,0,0))))
    if "look_at" in item:
        target=Gf.Vec3d(*vec(item["look_at"]))
        delta=target-eye
        if delta.GetLength()<1e-8:
            raise ValueError("A light cannot aim at its own position")
        up=Gf.Vec3d(0,1,0) if abs(delta.GetNormalized()[1])<.98 else Gf.Vec3d(0,0,1)
        light.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(eye,target,up).GetInverse())
    else:
        light.AddTranslateOp().Set(eye)


def author(stage,spec,base_dir):
    """Replace only /World/Set. Coordinates and dimensions are Y-up XYZ metres; positions are bottom centres."""
    if not isinstance(spec,dict):
        raise ValueError("A set specification must be a JSON object")
    plan=specification(spec["preset"]) if "preset" in spec else {}
    plan.update(copy.deepcopy({k:v for k,v in spec.items() if k!="preset"}))
    if not any(k in plan for k in ("architecture","props","lights")):
        raise ValueError("Set needs architecture, props or lights")
    target=stage.GetEditTarget().GetLayer()
    layer_dir=Path(target.realPath).parent if target.realPath else None
    # Build the new subtree away from the live stage so a bad model can't leave a partial set.
    context=Ar.DefaultResolverContext([str(layer_dir)]) if layer_dir else Ar.DefaultResolverContext()
    tmp=Usd.Stage.CreateInMemory("Set.usda",Ar.ResolverContext(context))
    root=UsdGeom.Xform.Define(tmp,ROOT)
    _layout(root,plan)
    root.GetPrim().SetCustomDataByKey("anyscene:label",plan.get("label","AnyScene"))
    mats=dict(SURFACES,**plan.get("materials",{}))
    looks={key:material(tmp,key,value) for key,value in mats.items()}
    base=Path(base_dir).resolve()
    report=dict(architecture=0,proxies=[],references=[],lights=0)
    for group,key in (("Architecture","architecture"),("Props","props"),("Lights","lights")):
        UsdGeom.Scope.Define(tmp,ROOT+"/"+group)
        seen=set()
        for item in plan.get(key,[]):
            identifier=Tf.MakeValidIdentifier(item["id"])
            if not identifier or identifier in seen:
                raise ValueError(f"Duplicate or empty {group} identifier: {item['id']!r}")
            seen.add(identifier)
            path=ROOT+"/"+group+"/"+identifier
            if key=="lights":
                practical(tmp,path,item)
                report["lights"]+=1
                continue
            xf=UsdGeom.Xform.Define(tmp,path)
            _layout(xf,item)
            if key=="architecture":
                shape(tmp,path+"/Geometry",item["dims"],item.get("shape","box"),looks,item.get("material","plaster"))
                report["architecture"]+=1
                continue
            asset=item.get("asset",item["id"])
            xf.GetPrim().SetCustomDataByKey("anyscene:asset",asset)
            file=asset_path(asset,item,plan,base)
            if file:
                fit_reference(tmp,path,file,item,layer_dir)
                xf.GetPrim().SetCustomDataByKey("anyscene:representation","reference")
                report["references"].append(item["id"])
            else:
                shape(tmp,path+"/Blockout",item["dims"],item.get("shape","box"),looks,item.get("material","proxy"))
                xf.GetPrim().SetCustomDataByKey("anyscene:representation","blockout")
                report["proxies"].append(item["id"])
    # Writing through the caller's edit target preserves lights, cameras and assets owned by other tools.
    dst=stage.GetEditTarget().MapToSpecPath(Sdf.Path(ROOT))
    if dst.isEmpty:
        raise ValueError("Edit target cannot map /World/Set")
    with Sdf.ChangeBlock():
        Sdf.CreatePrimInLayer(target,dst.GetParentPath())
        if not Sdf.CopySpec(tmp.GetRootLayer(),Sdf.Path(ROOT),target,dst):
            raise RuntimeError("Could not author the set subtree")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list",action="store_true")
    parser.add_argument("--preset",choices=presets(),default="workshop")
    parser.add_argument("--spec",type=Path,help="Editable set JSON. Referenced files resolve from its folder.")
    parser.add_argument("--base-dir",type=Path,help="Asset directory base. Defaults to the spec folder or current directory.")
    parser.add_argument("--write-spec",type=Path,help="Write an editable copy of the chosen preset.")
    parser.add_argument("--output",type=Path,help="New USD layer to author.")
    a=parser.parse_args()
    if a.list:
        print("\n".join(presets()))
        return
    spec=json.loads(a.spec.read_text(encoding="utf-8")) if a.spec else specification(a.preset)
    if a.write_spec:
        with a.write_spec.open("x",encoding="utf-8") as f:
            json.dump(spec,f,indent=2)
            f.write("\n")
    if a.output:
        if a.output.exists():
            parser.error("Choose a new output file")
        stage=Usd.Stage.CreateNew(str(a.output.resolve()))
        UsdGeom.SetStageMetersPerUnit(stage,1)
        UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.y)
        report=author(stage,spec,a.base_dir or (a.spec.parent if a.spec else Path.cwd()))
        stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
        stage.GetRootLayer().Save()
        print(f"{report['architecture']} architectural parts, {len(report['references'])} USD references, "
              f"{len(report['proxies'])} labelled blockouts and {report['lights']} lights")
    if not a.output and not a.write_spec:
        parser.error("Choose --list, --write-spec or --output")


if __name__=="__main__":
    main()
