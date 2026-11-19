"""Author a cohesive static prop library in a metre-based, Y-up Solaris stage."""
from math import isfinite
from pathlib import Path

from pxr import Gf, Kind, Sdf, Tf, Usd, UsdGeom
from . import gltf, looks, props

ROOT = "/World/Kit"


def _number(value, name):
    v=float(value)
    if not isfinite(v):
        raise ValueError(f"{name} must be finite")
    return v


def _vec(value, name, *, positive=False):
    if not isinstance(value,(tuple,list)) or len(value)!=3:
        raise ValueError(f"{name} must be an XYZ triple")
    v=tuple(_number(x,name) for x in value)
    if positive and min(v)<=0:
        raise ValueError(f"{name} must contain positive metre dimensions")
    return Gf.Vec3d(*v)


def _path(base,value):
    path=(base/value).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _bounds(prim):
    bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),["default","render","proxy"])
    r=bbox.ComputeWorldBound(prim).ComputeAlignedRange()
    if r.IsEmpty():raise ValueError(f"No renderable geometry under {prim.GetPath()}")
    return r


def _external(stage,path,filename,item):
    content=UsdGeom.Xform.Define(stage,path)
    if filename.suffix.lower() in {".gltf",".glb"}:
        gltf.load(stage,path+"/Model",filename,item.get("strip_root_rotation",False))
        units=1.; up="Y"
    else:
        if filename.suffix.lower() not in {".usd",".usda",".usdc",".usdz"}:
            raise ValueError(f"Unsupported static mesh source {filename.suffix}")
        src=Usd.Stage.Open(str(filename))
        if not src:raise ValueError(f"Cannot read USD source {filename}")
        target=src.GetPrimAtPath(item["prim"]) if item.get("prim") else src.GetDefaultPrim()
        if not target:raise ValueError("Supply a USD default prim or an explicit prim path")
        model=stage.OverridePrim(path+"/Model")
        model.GetReferences().AddReference(filename.as_posix(),target.GetPath())
        units=UsdGeom.GetStageMetersPerUnit(src);up=UsdGeom.GetStageUpAxis(src)
    units=_number(item.get("meters_per_unit",units),"meters_per_unit")
    if units<=0:raise ValueError("meters_per_unit must be positive")
    orient=Gf.Matrix4d(1)
    if up=="Z":orient=Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(1,0,0),-90))
    yaw=_number(item.get("source_yaw",-90 if str(item.get("gen","")).startswith("tripo") else 0),"source_yaw")
    op=content.AddTransformOp()
    op.Set(orient*Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0,1,0),yaw))*Gf.Matrix4d().SetScale(units))
    return content


def _build_item(stage,path,item,base,materials):
    asset=UsdGeom.Xform.Define(stage,path)
    Usd.ModelAPI(asset.GetPrim()).SetKind(Kind.Tokens.component)
    asset.GetPrim().SetDisplayName(str(item.get("label",item["id"])))
    if item.get("why"):asset.GetPrim().SetDocumentation(str(item["why"]))
    if item.get("tags"):asset.GetPrim().SetCustomDataByKey("tags",", ".join(map(str,item["tags"])))
    source=item.get("source",item.get("glb"))
    kind=item.get("kind",None if source else item["id"])
    if source and item.get("kind") not in (None,"external"):
        raise ValueError(f"{item['id']}: choose a procedural kind or a source")
    if not source and kind not in props.RECIPES:
        raise ValueError(f"Unknown prop kind {kind!r}. Supply a local source or use {', '.join(props.RECIPES)}")
    variant=asset.GetPrim().GetVariantSets().AddVariantSet("lod")
    low_source=item.get("lod1_source")
    if source and not low_source:
        f=_path(base,source);sibling=f.with_name(f.stem+"_lod1"+f.suffix)
        if sibling.is_file():low_source=str(sibling)
    levels=("high","low") if not source or low_source else ("high",)
    requested=item.get("lod","high")
    if requested not in levels:raise ValueError(f"{item['id']} has LOD choices {levels}")
    transform=asset.AddTransformOp()
    metrics={}
    for level in levels:
        transform.Set(Gf.Matrix4d(1))
        variant.AddVariant(level);variant.SetVariantSelection(level)
        with variant.GetVariantEditContext():
            path_content=path+"/Geometry"
            if source:
                _external(stage,path_content,_path(base,source if level=="high" else low_source),item)
            else:
                UsdGeom.Xform.Define(stage,path_content)
                props.RECIPES[kind](props.Builder(stage,path_content,materials,level=="low"))
            # Normalize in the source's canonical frame before placing it in the set.
            alignment=UsdGeom.Xformable(stage.GetPrimAtPath(path_content))
            box=_bounds(asset.GetPrim());lo,hi=box.GetMin(),box.GetMax()
            center=Gf.Vec3d((lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2)
            dims=hi-lo;scale=Gf.Vec3d(1)
            exact=item.get("size_m")
            if item.get("fit") is not None:
                w,d,h=_vec(item["fit"],"fit",positive=True);exact=(w,h,d)
            height=item.get("height_m",item.get("h"))
            if exact is not None and height is not None:
                raise ValueError("Choose height_m or size_m")
            if exact is not None:
                target=_vec(exact,"size_m",positive=True)
                if min(dims)<=1e-12:raise ValueError("Cannot fit a flat asset on all axes")
                scale=Gf.Vec3d(*[t/d for t,d in zip(target,dims)])
            elif height is not None:
                h=_number(height,"height_m")
                if h<=0 or dims[1]<=1e-12:raise ValueError("Positive asset height required")
                scale=Gf.Vec3d(h/dims[1])
            # xformOpOrder is outside-to-inside. Insert normalization ahead of units and up-axis.
            ops=alignment.GetOrderedXformOps()
            norm=alignment.AddTransformOp(opSuffix="bottomCenter")
            norm.Set(Gf.Matrix4d().SetTranslate(-center)*Gf.Matrix4d().SetScale(scale))
            alignment.SetXformOpOrder([norm]+ops)
            size=[a*b for a,b in zip(dims,scale)]
            contents=list(Usd.PrimRange(asset.GetPrim()))
            meshes=[UsdGeom.Mesh(prim) for prim in contents if prim.IsA(UsdGeom.Mesh)]
            tris=sum(sum(max(0,n-2) for n in mesh.GetFaceVertexCountsAttr().Get() or [])
                     for mesh in meshes)
            other=sum(1 for prim in contents if prim.IsA(UsdGeom.Gprim) and not prim.IsA(UsdGeom.Mesh))
            metrics[level]={"triangles":None if other else tris,"mesh_triangles":tris,
                            "non_mesh_primitives":other,"size_m":size}
    position=_vec(item.get("position",(0,0,0)),"position")
    yaw=_number(item.get("yaw",0),"yaw")
    variant.SetVariantSelection(requested)
    transform.Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0,1,0),yaw))*Gf.Matrix4d().SetTranslate(position))
    return {"id":item["id"],"kind":kind or "external","prim":path,
            "lod":requested,"levels":metrics,"position":list(position),"yaw":yaw}


def author(stage,spec,base_dir):
    """Replace /World/Kit atomically after validating and composing every item.

    Return per-item dimensions and triangle counts for both LODs. Local source and
    style-reference paths are resolved relative to base_dir.
    """
    if not isinstance(spec,dict) or not spec.get("items"):raise ValueError("A kit requires items")
    if stage.HasAuthoredMetadata("upAxis") and UsdGeom.GetStageUpAxis(stage)!="Y":raise ValueError("Kit target requires Y up")
    if stage.HasAuthoredMetadata("metersPerUnit") and UsdGeom.GetStageMetersPerUnit(stage)!=1:raise ValueError("Kit target requires metres")
    base=Path(base_dir).resolve()
    staging=Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(staging,UsdGeom.Tokens.y);UsdGeom.SetStageMetersPerUnit(staging,1.)
    UsdGeom.Xform.Define(staging,"/World")
    kit=UsdGeom.Xform.Define(staging,ROOT)
    Usd.ModelAPI(kit.GetPrim()).SetKind(Kind.Tokens.assembly)
    kit.GetPrim().SetDisplayName(str(spec.get("name","Kit")))
    refs=spec.get("references",[])
    if not isinstance(refs,list) or len(refs)>4:raise ValueError("Use zero to four local style references")
    for ref in refs:_path(base,ref)
    style=spec.get("style",{})
    if isinstance(style,str):style={"description":style}
    if style.get("description"):kit.GetPrim().SetDocumentation(str(style["description"]))
    mats=looks.palette(staging,ROOT+"/Looks",style)
    rows=[];ids={"Looks"}
    for item in spec["items"]:
        iid=item["id"]
        if not isinstance(iid,str) or not Sdf.Path.IsValidIdentifier(iid) or iid in ids:
            raise ValueError(f"Invalid or duplicate USD item identifier {iid!r}")
        ids.add(iid)
        rows.append(_build_item(staging,ROOT+"/"+iid,item,base,mats))
    world=stage.GetPrimAtPath("/World")
    if not world or not world.IsDefined():
        UsdGeom.Xform.Define(stage,"/World")
    dest=stage.GetEditTarget().GetLayer()
    with Sdf.ChangeBlock():
        if not Sdf.CopySpec(staging.GetRootLayer(),ROOT,dest,ROOT):
            raise RuntimeError("Could not publish the kit on the target stage")
    UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.y);UsdGeom.SetStageMetersPerUnit(stage,1.)
    return dict(name=spec.get("name","Kit"),reference_count=len(refs),references=refs,
                style=style,items=rows)

