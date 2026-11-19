"""Author an editable, metre-based Solaris stage directly through OpenUSD."""
from itertools import chain
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdLux, UsdRender, UsdShade, Vt

from . import industrial, materials, rigs, stilt_asset

RENDERER = "HdRedshiftRendererPlugin"
EXTERNAL = ("mps5", "svd", "val")
VIEWS = {"hero": (1.4, .85, 1.7), "front": (0, 0, 1), "rear": (0, 0, -1),
         "left": (-1, 0, 0), "right": (1, 0, 0), "top": (0, 1, 0), "bottom": (0, -1, 0)}


def catalog(glb):
    items = {name: dict(family="rig", **entry) for name, entry in rigs.catalog().items()}
    items["stilt"] = dict(family="skeleton", controls={}, clips=stilt_asset.clips(glb))
    for name in industrial.names():
        items[name] = dict(family="industrial", controls={}, clips={})
    for name in EXTERNAL:
        items[name] = dict(family="external", controls={}, clips={})
    return items


def _points(value):
    array = np.asarray(value, dtype=np.float32)
    if array.ndim != 2 or array.shape[1] != 3 or not np.isfinite(array).all():
        raise ValueError("Invalid mesh points")
    return Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(array))


def geometry(stage, asset, controls, clip, frames, screen_texture=None):
    """Write stable topology once and animate only the changing point samples."""
    UsdGeom.Xform.Define(stage, "/Machine")
    UsdGeom.Scope.Define(stage, "/Machine/Parts")
    is_static = asset in industrial.names()
    surfaces, targets = {}, {}
    for sample_index, (frame, time) in enumerate(frames):
        parts = industrial.parts(asset) if is_static else rigs.parts(asset, controls, clip, frame)
        used = set()
        for part in parts:
            key = Tf.MakeValidIdentifier(part["name"])
            if key in used:
                raise ValueError(f"Duplicate mesh name after USD conversion: {part['name']}")
            used.add(key)
            points = _points(part["points"])
            if sample_index == 0:
                faces = part["faces"]
                mesh = UsdGeom.Mesh.Define(stage, "/Machine/Parts/" + key)
                mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
                mesh.CreateFaceVertexCountsAttr([len(face) for face in faces])
                indices = np.fromiter(chain.from_iterable(faces), dtype=np.int32)
                if not len(indices) or indices.min() < 0 or indices.max() >= len(points):
                    raise ValueError(f"Invalid face indices in {key}")
                mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(indices))
                if "uv" in part:
                    interpolation = UsdGeom.Tokens.faceVarying if "uv_indices" in part else UsdGeom.Tokens.vertex
                    uv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, interpolation)
                    uv.Set(Vt.Vec2fArray.FromNumpy(np.asarray(part["uv"], dtype=np.float32)))
                    if "uv_indices" in part:
                        uv.SetIndices(part["uv_indices"])
                name = part["material"]
                if name not in surfaces:
                    spec = industrial.surface(name, asset) if is_static else materials.finish(name)
                    if name == "display" and screen_texture:
                        spec.update(base_texture=screen_texture, base=(1, 1, 1))
                    surfaces[name] = materials.material(stage, name, spec)
                UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(surfaces[name])
                targets[key] = (mesh, len(points))
            mesh, size = targets[key]
            if len(points) != size:
                raise ValueError(f"Changing topology in {key} at frame {frame}")
            mesh.GetPointsAttr().Set(points, time)
            mesh.CreateExtentAttr().Set(UsdGeom.PointBased.ComputeExtent(points), time)
        if used != set(targets):
            raise ValueError(f"Mesh set changed in {asset} at frame {frame}")


def external(stage, filename):
    source = Usd.Stage.Open(str(filename))
    if not source or not source.GetDefaultPrim():
        raise ValueError("The supplied USD asset needs a default prim")
    origin = UsdGeom.Xform.Define(stage, "/Machine")
    data = UsdGeom.Xform.Define(stage, "/Machine/Source")
    data.GetPrim().GetReferences().AddReference(str(filename).replace(chr(92), "/"))
    factor = UsdGeom.GetStageMetersPerUnit(source)
    origin.AddScaleOp().Set(Gf.Vec3f(factor))
    if UsdGeom.GetStageUpAxis(source) == UsdGeom.Tokens.z:
        origin.AddRotateXOp().Set(-90)


def init(stage):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1)


def bounds(stage, time=Usd.TimeCode.Default()):
    cache = UsdGeom.BBoxCache(time, ["default", "render", "proxy"], useExtentsHint=False)
    box = cache.ComputeWorldBound(stage.GetPrimAtPath("/Machine")).ComputeAlignedRange()
    if box.IsEmpty():
        raise ValueError("The asset has no visible geometry at the selected frame")
    return box


def studio(stage, box, view, size, output, set_metadata=True):
    """Frame the same bounding sphere in every view. Camera local forward is -Z."""
    UsdGeom.Scope.Define(stage, "/Studio")
    center = box.GetMidpoint()
    radius = max(box.GetSize().GetLength() * 0.5, 0.001)
    direction = Gf.Vec3d(*VIEWS[view]).GetNormalized()
    up = Gf.Vec3d(0, 0, -1) if abs(direction[1]) > .99 else Gf.Vec3d(0, 1, 0)
    camera = UsdGeom.Camera.Define(stage, "/Studio/Camera")
    distance = radius * 4.8 * max(1, size[0] / size[1])
    view_matrix = Gf.Matrix4d().SetLookAt(center + direction * distance, center, up)
    camera.AddTransformOp().Set(view_matrix.GetInverse())
    camera.CreateClippingRangeAttr((max(.0001, distance - radius * 2), distance + radius * 3))
    camera.CreateFocalLengthAttr(50)
    camera.CreateHorizontalApertureAttr(36)
    camera.CreateVerticalApertureAttr(36 * size[1] / size[0])
    if view != "hero":
        camera.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
        camera.CreateHorizontalApertureAttr(radius * 22 * max(1, size[0] / size[1]))
        camera.CreateVerticalApertureAttr(radius * 22 * max(1, size[1] / size[0]))
    for name, rotation, intensity, angle in (("Key", (-38, 32, 0), 2.3, 18),
                                              ("Rim", (-18, -145, 0), 1.4, 14)):
        light = UsdLux.DistantLight.Define(stage, "/Studio/" + name)
        light.CreateIntensityAttr(intensity)
        light.CreateAngleAttr(angle)
        light.AddRotateXYZOp().Set(Gf.Vec3f(*rotation))
    UsdLux.DomeLight.Define(stage, "/Studio/Fill").CreateIntensityAttr(.4)
    UsdGeom.Scope.Define(stage, "/Render")
    settings = UsdRender.Settings.Define(stage, "/Render/Settings")
    product = UsdRender.Product.Define(stage, "/Render/Beauty")
    product.CreateProductNameAttr(str(output))
    product.CreateProductTypeAttr("raster")
    var = UsdRender.Var.Define(stage, "/Render/Vars/Beauty")
    var.CreateDataTypeAttr("color4f")
    var.CreateSourceNameAttr("color")
    var.CreateSourceTypeAttr("raw")
    for prefix in ("driver:parameters:aov:", "driver:parameters:aov:husk:"):
        var.GetPrim().CreateAttribute(prefix + "name", Sdf.ValueTypeNames.String).Set("rgba")
        var.GetPrim().CreateAttribute(prefix + "format", Sdf.ValueTypeNames.Token).Set("color4h")
        var.GetPrim().CreateAttribute(prefix + "multiSampled", Sdf.ValueTypeNames.Bool).Set(False)
    for role in ("source", "output"):
        product.GetPrim().CreateAttribute("driver:parameters:husk:" + role + "_colorspace",
                                          Sdf.ValueTypeNames.String).Set("ACEScg")
    product.CreateOrderedVarsRel().SetTargets([var.GetPath()])
    settings.CreateProductsRel().SetTargets([product.GetPath()])
    settings.CreateCameraRel().SetTargets([camera.GetPath()])
    settings.CreateResolutionAttr(Gf.Vec2i(*size))
    settings.CreateRenderingColorSpaceAttr("ACEScg")
    settings.GetPrim().CreateAttribute("redshift:global:RS_OCIOColorSpace", Sdf.ValueTypeNames.String).Set("ACEScg")
    if set_metadata:
        stage.SetMetadata("renderSettingsPrimPath", str(settings.GetPath()))


def compact_report(stage, frame=1):
    machine = stage.GetPrimAtPath("/Machine")
    if not machine:
        raise ValueError("Missing /Machine")
    pieces = [UsdGeom.Mesh(p) for p in Usd.PrimRange(machine) if p.IsA(UsdGeom.Mesh)]
    if not pieces:
        raise ValueError("No meshes under /Machine")
    time = Usd.TimeCode(frame)
    faces = points = 0
    for mesh in pieces:
        positions = mesh.GetPointsAttr().Get(time)
        counts = mesh.GetFaceVertexCountsAttr().Get(time)
        indices = mesh.GetFaceVertexIndicesAttr().Get(time)
        ok, reason = UsdGeom.Mesh.ValidateTopology(indices, counts, len(positions))
        if not ok:
            raise ValueError(f"{mesh.GetPath()}: {reason}")
        faces += len(counts)
        points += len(positions)
    return dict(meshes=len(pieces), polygons=faces, points=points,
                bounds_m=[list(v) for v in (bounds(stage, time).GetMin(), bounds(stage, time).GetMax())])
