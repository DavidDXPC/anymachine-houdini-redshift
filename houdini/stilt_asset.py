"""Read the published Stilt GLB into a native Solaris skeleton, mesh and animation."""
from functools import lru_cache
import json
from pathlib import Path
import struct
import tempfile

import numpy as np
from pxr import Gf, Sdf, Tf, UsdGeom, UsdShade, UsdSkel, Vt


FPS = 24
ROOT = "/Machine"
DTYPES = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class StiltGLB:
    def __init__(self, filename):
        with open(filename, "rb") as src:
            magic, version, total = struct.unpack("<4sII", src.read(12))
            if (magic, version) != (b"glTF", 2):
                raise ValueError("Stilt requires a binary glTF 2 asset")
            size, kind = struct.unpack("<I4s", src.read(8))
            if kind != b"JSON":
                raise ValueError("Missing GLB JSON chunk")
            self.doc = json.loads(src.read(size))
            size, kind = struct.unpack("<I4s", src.read(8))
            self.binary = src.read(size)
            if kind != b"BIN\0" or len(self.binary) != size or src.tell() != total:
                raise ValueError("Incomplete GLB binary chunk")

    def accessor(self, index):
        acc = self.doc["accessors"][index]
        view = self.doc["bufferViews"][acc["bufferView"]]
        dtype = np.dtype(DTYPES[acc["componentType"]])
        width = WIDTHS[acc["type"]]
        stride = view.get("byteStride", width * dtype.itemsize)
        return np.ndarray((acc["count"], width), dtype=dtype, buffer=self.binary,
                          offset=view.get("byteOffset", 0) + acc.get("byteOffset", 0),
                          strides=(stride, dtype.itemsize))

    def image(self, index):
        image = self.doc["images"][index]
        view = self.doc["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        extension = {"image/jpeg": ".jpg", "image/png": ".png"}[image["mimeType"]]
        name = Tf.MakeValidIdentifier(image["name"]) + extension
        return name, memoryview(self.binary)[start:start + view["byteLength"]]


@lru_cache(maxsize=2)
def _load(filename, timestamp, size):
    return StiltGLB(filename)


def _source(glb):
    path = Path(glb).resolve()
    stat = path.stat()
    return _load(str(path), stat.st_mtime_ns, stat.st_size)


def prepare(glb, folder):
    """Extract the two sets of embedded textures. An interrupted write is retryable."""
    src = _source(glb)
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    for index in range(len(src.doc["images"])):
        name, data = src.image(index)
        path = target / name
        if path.is_file() and path.stat().st_size == len(data) and path.read_bytes() == data:
            continue
        with tempfile.NamedTemporaryFile(dir=target, delete=False) as tmp:
            tmp.write(data)
        tmp_path = Path(tmp.name)
        try:
            tmp_path.replace(path)
        finally:
            tmp_path.unlink(missing_ok=True)


def clips(glb):
    src = _source(glb)
    result = {}
    for anim in src.doc["animations"]:
        samplers = anim["samplers"]
        end = max(src.doc["accessors"][s["input"]]["max"][0] for s in samplers)
        result[anim["name"]] = (round(end * FPS), FPS)
    return result


def _material_specs(src, folder):
    def texture(info):
        image = src.doc["textures"][info["index"]]["source"]
        name, _ = src.image(image)
        return (Path(folder) / name).as_posix()

    for mat in src.doc["materials"]:
        pbr = mat["pbrMetallicRoughness"]
        emission = mat.get("emissiveFactor", [0, 0, 0])
        spec = dict(base=pbr.get("baseColorFactor", [1, 1, 1, 1])[:3],
                    metal=pbr.get("metallicFactor", 1.0), rough=pbr.get("roughnessFactor", 1.0),
                    emission=emission, emission_weight=mat.get("extensions", {}).get(
                        "KHR_materials_emissive_strength", {}).get("emissiveStrength", 1.0))
        for key, info in (("base_texture", pbr.get("baseColorTexture")),
                          ("orm_texture", pbr.get("metallicRoughnessTexture")),
                          ("normal_texture", mat.get("normalTexture"))):
            if info is not None:
                spec[key] = texture(info)
        yield mat["name"], spec


def _joint_order(doc, skin):
    nodes = doc["nodes"]
    parents = {child: i for i, n in enumerate(nodes) for child in n.get("children", [])}
    joints = set(skin["joints"])
    order, paths = [], []

    def visit(index, prefix):
        name = Tf.MakeValidIdentifier(nodes[index]["name"])
        path = f"{prefix}/{name}" if prefix else name
        paths.append(path)
        order.append(index)
        for child in nodes[index].get("children", []):
            if child in joints:
                visit(child, path)

    for index in skin["joints"]:
        if parents.get(index) not in joints:
            visit(index, "")
    return order, paths


def _rest_components(doc, order):
    nodes = [doc["nodes"][i] for i in order]
    defaults = {"translation": (0, 0, 0), "rotation": (0, 0, 0, 1), "scale": (1, 1, 1)}
    return {key: np.array([n.get(key, default) for n in nodes], dtype=np.float32)
            for key, default in defaults.items()}


def _vec3(values):
    return Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(values, dtype=np.float32))


def _quat(values):
    return Vt.QuatfArray.FromNumpy(np.ascontiguousarray(values, dtype=np.float32))


def _scale(values):
    return Vt.Vec3hArray.FromNumpy(np.ascontiguousarray(values, dtype=np.float16))


def _slerp(a, b, alpha):
    dot = (a * b).sum(axis=1, keepdims=True)
    b = np.where(dot < 0.0, -b, b)
    theta = np.arccos(np.clip(np.abs(dot), 0.0, 1.0))
    sin_theta = np.sin(theta)
    safe = np.where(sin_theta > 1e-6, sin_theta, 1.0)
    spherical = (np.sin((1 - alpha) * theta) * a + np.sin(alpha * theta) * b) / safe
    mixed = np.where(sin_theta > 1e-6, spherical, a * (1 - alpha) + b * alpha)
    return mixed / np.linalg.norm(mixed, axis=1, keepdims=True)


def _key_data(src, anim):
    channels, times = [], set()
    for channel in anim["channels"]:
        sampler = anim["samplers"][channel["sampler"]]
        values = src.accessor(sampler["output"])
        # All original key times lie on whole frames. GLB stores seconds as float32.
        frames = np.rint(src.accessor(sampler["input"]).ravel() * FPS).astype(np.float64)
        mode = sampler.get("interpolation", "LINEAR")
        times.update(frames)
        if mode == "STEP":
            changing = np.any(values[1:] != values[:-1], axis=1)
            # USD interpolates the joint array as a whole. Preserve mixed step/linear
            # samplers with a held sample immediately before each discontinuity.
            times.update(frames[1:][changing] - 1e-5)
        elif mode != "LINEAR":
            raise ValueError(f"Unexpected Stilt interpolation {mode}")
        channels.append((channel["target"], mode, frames, values))
    return channels, np.array(sorted(times))


def _animation(stage, src, anim, order, paths, rest):
    channels, times = _key_data(src, anim)
    node_slot = {node: i for i, node in enumerate(order)}
    arrays = {key: np.repeat(values[None, :, :], len(times), axis=0) for key, values in rest.items()}
    for target, mode, frames, values in channels:
        lo = np.clip(np.searchsorted(frames, times, side="right") - 1, 0, len(frames) - 1)
        chosen = values[lo]
        if mode == "LINEAR":
            hi = np.minimum(lo + 1, len(frames) - 1)
            alpha = np.clip((times - frames[lo]) / np.maximum(frames[hi] - frames[lo], 1), 0, 1)[:, None]
            if target["path"] == "rotation":
                chosen = _slerp(chosen, values[hi], alpha)
            else:
                chosen = chosen * (1 - alpha) + values[hi] * alpha
        arrays[target["path"]][:, node_slot[target["node"]], :] = chosen
    animation = UsdSkel.Animation.Define(stage, f"{ROOT}/Clips/{Tf.MakeValidIdentifier(anim['name'])}")
    animation.CreateJointsAttr(paths)
    attrs = ((animation.CreateTranslationsAttr(), "translation", _vec3),
             (animation.CreateRotationsAttr(), "rotation", _quat),
             (animation.CreateScalesAttr(), "scale", _scale))
    for attr, key, encode in attrs:
        for time, value in zip(times, arrays[key]):
            attr.Set(encode(value), float(time))
    return animation


def _mesh(stage, src, node, remap, materials):
    name = Tf.MakeValidIdentifier(node["name"])
    mesh = UsdGeom.Mesh.Define(stage, f"{ROOT}/Parts/{name}")
    prims = src.doc["meshes"][node["mesh"]]["primitives"]
    data = {key: [] for key in ("POSITION", "NORMAL", "JOINTS_0", "WEIGHTS_0", "TEXCOORD_0", "TEXCOORD_1")}
    triangles, assignments = [], []
    offset = face_start = 0
    for part in prims:
        if part.get("mode", 4) != 4:
            raise ValueError("Unexpected non-triangular Stilt primitive")
        attrs = part["attributes"]
        for key, chunks in data.items():
            chunks.append(src.accessor(attrs[key]))
        indices = src.accessor(part["indices"]).reshape(-1, 3).astype(np.int32)
        triangles.append(indices + offset)
        stop = face_start + len(indices)
        assignments.append((part["material"], face_start, stop))
        face_start = stop
        offset += len(data["POSITION"][-1])

    data = {key: np.concatenate(values) for key, values in data.items()}
    points = data["POSITION"]
    mesh.CreatePointsAttr(_vec3(points))
    mesh.CreateNormalsAttr(_vec3(data["NORMAL"]))
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(face_start, 3, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.concatenate(triangles).ravel()))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(True)
    primvars = UsdGeom.PrimvarsAPI(mesh)
    for key, uvname in (("TEXCOORD_0", "st"), ("TEXCOORD_1", "st1")):
        uv = data[key].copy()
        uv[:, 1] = 1 - uv[:, 1]  # USD texture origin is lower left.
        primvars.CreatePrimvar(uvname, Sdf.ValueTypeNames.TexCoord2fArray,
                               UsdGeom.Tokens.vertex).Set(Vt.Vec2fArray.FromNumpy(uv))
    binding = UsdSkel.BindingAPI.Apply(mesh.GetPrim())
    binding.CreateGeomBindTransformAttr(Gf.Matrix4d(1))
    binding.CreateJointIndicesPrimvar(False, 4).Set(
        Vt.IntArray.FromNumpy(remap[data["JOINTS_0"]].ravel()))
    weights = data["WEIGHTS_0"]
    binding.CreateJointWeightsPrimvar(False, 4).Set(Vt.FloatArray.FromNumpy(weights.ravel()))
    shading = UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
    if len(assignments) == 1:
        shading.Bind(materials[assignments[0][0]])
    else:
        for material_id, start, stop in assignments:
            subset = shading.CreateMaterialBindSubset(f"material_{material_id}",
                                                      Vt.IntArray.FromNumpy(np.arange(start, stop, dtype=np.int32)))
            UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(materials[material_id])
        shading.SetMaterialBindSubsetsFamilyType(UsdGeom.Tokens.partition)


def author(stage, glb, folder, clip, material_builder):
    """Author the complete selected animation and skin into the supplied USD stage."""
    src = _source(glb)
    skin = src.doc["skins"][0]
    animations = {a["name"]: a for a in src.doc["animations"]}
    if clip and clip not in animations:
        raise ValueError(f"Unknown Stilt clip {clip!r}. Available: {', '.join(animations)}")
    root = UsdSkel.Root.Define(stage, ROOT)
    UsdGeom.Scope.Define(stage, ROOT + "/Parts")
    materials = [material_builder(stage, name, spec) for name, spec in _material_specs(src, folder)]
    skeleton = UsdSkel.Skeleton.Define(stage, ROOT + "/Skeleton")
    order, paths = _joint_order(src.doc, skin)
    rest = _rest_components(src.doc, order)
    skeleton.CreateJointsAttr(paths)
    skeleton.CreateRestTransformsAttr(UsdSkel.MakeTransforms(
        _vec3(rest["translation"]), _quat(rest["rotation"]), _scale(rest["scale"])))
    old_slot = {node: i for i, node in enumerate(skin["joints"])}
    source_indices = [old_slot[node] for node in order]
    inverse_bind = src.accessor(skin["inverseBindMatrices"]).reshape(-1, 4, 4).astype(np.float64)
    # glTF column-major bytes, reshaped in C order, already use Gf's row-vector layout.
    bind = np.linalg.inv(inverse_bind[source_indices])
    skeleton.CreateBindTransformsAttr(Vt.Matrix4dArray.FromNumpy(np.ascontiguousarray(bind)))
    UsdSkel.BindingAPI.Apply(root.GetPrim()).CreateSkeletonRel().SetTargets([skeleton.GetPath()])
    if clip:
        animation = _animation(stage, src, animations[clip], order, paths, rest)
        UsdSkel.BindingAPI.Apply(skeleton.GetPrim()).CreateAnimationSourceRel().SetTargets([animation.GetPath()])
    remap = np.argsort(source_indices).astype(np.int32)
    for node in src.doc["nodes"]:
        if node.get("skin") == 0 and "mesh" in node:
            _mesh(stage, src, node, remap, materials)
    return root
