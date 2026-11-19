"""Export the civil procedural kits and rigs as self-contained glTF 2 binaries."""
import json
import os
from pathlib import Path
import shutil
import struct
from tempfile import NamedTemporaryFile

import numpy as np
from pxr import Gf

from . import industrial, materials, rigs
from .industrial.surfaces import _TO_ACESCG


_TO_LINEAR_SRGB = np.linalg.inv(_TO_ACESCG)


class BinaryGLTF:
    def __init__(self, name):
        self.bin = bytearray()
        self.doc = {
            "asset": {"version": "2.0", "generator": "AnyMachine Houdini"},
            "scene": 0, "scenes": [{"name": name, "nodes": [0]}],
            "nodes": [{"name": name, "children": []}], "meshes": [], "materials": [],
            "accessors": [], "bufferViews": [],
        }

    def accessor(self, values, kind, component, target=None, bounds=False):
        dtype = {5123: "<u2", 5125: "<u4", 5126: "<f4"}[component]
        width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[kind]
        values = np.ascontiguousarray(values, dtype=dtype).reshape(-1, width)
        self.bin.extend(b"\0" * (-len(self.bin) % 4))
        view = dict(buffer=0, byteOffset=len(self.bin), byteLength=values.nbytes)
        if target:
            view["target"] = target
        a = dict(bufferView=len(self.doc["bufferViews"]), componentType=component,
                 count=len(values), type=kind)
        if bounds:
            a.update(min=values.min(axis=0).tolist(), max=values.max(axis=0).tolist())
        self.doc["bufferViews"].append(view)
        self.doc["accessors"].append(a)
        self.bin.extend(values.tobytes())
        return len(self.doc["accessors"]) - 1

    def png_texture(self, filename):
        image = Path(filename)
        data = image.read_bytes()
        self.bin.extend(b"\0" * (-len(self.bin) % 4))
        view = len(self.doc["bufferViews"])
        self.doc["bufferViews"].append(dict(buffer=0, byteOffset=len(self.bin), byteLength=len(data)))
        self.bin.extend(data)
        images = self.doc.setdefault("images", [])
        textures = self.doc.setdefault("textures", [])
        textures.append({"source": len(images)})
        images.append(dict(name=image.stem, bufferView=view, mimeType="image/png"))
        return len(textures) - 1

    def write(self, handle):
        self.doc["buffers"] = [{"byteLength": len(self.bin)}]
        header = json.dumps(self.doc, allow_nan=False, separators=(",", ":")).encode("utf-8")
        header += b" " * (-len(header) % 4)
        self.bin.extend(b"\0" * (-len(self.bin) % 4))
        handle.write(struct.pack("<4sII", b"glTF", 2, 28 + len(header) + len(self.bin)))
        handle.write(struct.pack("<I4s", len(header), b"JSON"))
        handle.write(header)
        handle.write(struct.pack("<I4s", len(self.bin), b"BIN\0"))
        handle.write(self.bin)

    def material(self, name, spec):
        pbr = dict(baseColorFactor=[*spec["base"], 1.0], metallicFactor=spec["metal"],
                   roughnessFactor=spec["rough"])
        if spec.get("base_texture"):
            pbr["baseColorTexture"] = {"index": self.png_texture(spec["base_texture"])}
        mat = dict(name=name, pbrMetallicRoughness=pbr, doubleSided=True)
        extensions = {}
        if spec.get("transmission"):
            extensions["KHR_materials_transmission"] = {"transmissionFactor": spec["transmission"]}
        radiance = np.array(spec.get("emission", (0, 0, 0))) * spec.get("emission_weight", 0)
        if np.any(radiance):
            strength = max(1.0, radiance.max())
            mat["emissiveFactor"] = (radiance / strength).tolist()
            if strength > 1:
                extensions["KHR_materials_emissive_strength"] = {"emissiveStrength": float(strength)}
        if extensions:
            mat["extensions"] = extensions
            self.doc["extensionsUsed"] = sorted(set(self.doc.get("extensionsUsed", ())) | extensions.keys())
        self.doc["materials"].append(mat)
        return len(self.doc["materials"]) - 1


def _triangles(face, points):
    """Ear-clip concave ngons; use the direct fan for convex polygons."""
    if len(face) == 3:
        return [tuple(face)]
    ids = list(dict.fromkeys(face))
    if len(ids) < 3:
        return []
    xyz = points[ids]
    n = np.cross(xyz - xyz[0], np.roll(xyz, -1, axis=0) - xyz[0]).sum(axis=0)
    flat = np.delete(xyz, np.argmax(abs(n)), axis=1)
    x, y = flat.T
    sign = np.sign(np.sum(x * np.roll(y, -1) - y * np.roll(x, -1)))
    eps = max(float(np.ptp(flat, axis=0).max())**2 * 1e-12, 1e-24)

    def side(a, b, c):
        ab, ac = flat[b] - flat[a], flat[c] - flat[a]
        return (ab[0]*ac[1] - ab[1]*ac[0]) * sign

    active = list(range(len(ids)))
    if all(side(i - 1, i, (i + 1) % len(ids)) >= -eps for i in active):
        return [(ids[0], ids[i], ids[i + 1]) for i in range(1, len(ids) - 1)]
    tris = []
    while len(active) > 3:
        for k, b in enumerate(active):
            a, c = active[k - 1], active[(k + 1) % len(active)]
            if side(a, b, c) <= eps:
                continue
            if any(side(a, b, j) >= -eps and side(b, c, j) >= -eps and side(c, a, j) >= -eps
                   for j in active if j not in (a, b, c)):
                continue
            tris.append((ids[a], ids[b], ids[c]))
            active.pop(k)
            break
        else:
            # A collinear boundary vertex carries no area; drop it before the next ear.
            k = min(range(len(active)), key=lambda i: abs(side(active[i-1], active[i],
                                                               active[(i+1) % len(active)])))
            active.pop(k)
    tris.append(tuple(ids[i] for i in active))
    return tris


def _indices(faces, points):
    triangles = []
    for face in faces:
        triangles.extend(_triangles(face, points))
    if not triangles:
        raise ValueError("The part contains no triangular surface")
    return triangles


def _add_part(doc, part, material):
    p = np.asarray(part["points"], dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
        raise ValueError(f"Invalid points for {part['name']}")
    indices = _indices(part["faces"], p)
    p_accessor = doc.accessor(p, "VEC3", 5126, 34962, bounds=True)
    i_accessor = doc.accessor(indices, "SCALAR", 5123 if len(p) <= 65535 else 5125, 34963)
    primitive = dict(attributes={"POSITION": p_accessor}, indices=i_accessor, material=material)
    if "uv" in part:
        uv = np.array(part["uv"], dtype=np.float32)
        if uv.shape != (len(p), 2) or "uv_indices" in part:
            raise ValueError(f"{part['name']} needs one GLB UV per point")
        uv[:, 1] = 1 - uv[:, 1]
        primitive["attributes"]["TEXCOORD_0"] = doc.accessor(uv, "VEC2", 5126, 34962)
    mesh = dict(name=part["name"], primitives=[primitive])
    node = dict(name=part["name"], mesh=len(doc.doc["meshes"]))
    doc.doc["nodes"][0]["children"].append(len(doc.doc["nodes"]))
    doc.doc["nodes"].append(node)
    doc.doc["meshes"].append(mesh)
    return p


def _channel(doc, animation, times, node, path, values, kind):
    sampler = dict(input=times, output=doc.accessor(values, kind, 5126), interpolation="LINEAR")
    animation["channels"].append(dict(sampler=len(animation["samplers"]), target=dict(node=node, path=path)))
    animation["samplers"].append(sampler)


def _rotations(row_matrices):
    rotations = []
    for matrix in row_matrices:
        q = Gf.Matrix3d(matrix.tolist()).ExtractRotation().GetQuat()
        value = np.array([*q.GetImaginary(), q.GetReal()])
        if rotations and rotations[-1] @ value < 0:
            value *= -1
        rotations.append(value)
    return np.array(rotations)


def _fit_rigid(samples):
    """Find the proper rigid transform mapping the first sample into each pose."""
    centers = samples.mean(axis=1)
    reference = samples[0] - centers[0]
    centered = samples - centers[:, None, :]
    cov = reference.T @ centered
    u, _, vt = np.linalg.svd(cov)
    u[:, :, -1] *= np.linalg.det(u @ vt)[:, None]
    rot = u @ vt
    translate = centers - centers[0] @ rot
    # Inverse of row-vector rotation after undoing translation.
    local = (samples - translate[:, None, :]) @ rot.transpose(0, 2, 1)
    return translate, rot, local - samples[0]


def _motion(doc, animation, times, node_index, values):
    samples = np.asarray(values, dtype=np.float64)
    tolerance = 2e-6 * max(1., float(np.ptp(samples[0], axis=0).max()))
    if np.max(abs(samples - samples[0])) < tolerance:
        return
    translate, rotate, delta = _fit_rigid(samples)
    if np.max(abs(translate)) > tolerance:
        _channel(doc, animation, times, node_index, "translation", translate, "VEC3")
    if np.max(abs(rotate - np.eye(3))) > 1e-7:
        _channel(doc, animation, times, node_index, "rotation", _rotations(rotate), "VEC4")
    if np.max(abs(delta)) <= tolerance:
        return
    # Factor only the non-rigid residual. Repeated poses and correlated cloth motion
    # share targets instead of allocating one full target per part per frame.
    rows = delta.reshape(len(delta), -1)
    eigenvalues, vectors = np.linalg.eigh(rows @ rows.T)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues, vectors = eigenvalues[order], vectors[:, order]
    # The discarded Frobenius norm bounds every scalar residual.
    tail = np.cumsum(np.maximum(eigenvalues[::-1], 0.0))[::-1]
    rank = max(1, int(np.count_nonzero(tail > tolerance**2)))
    weights = vectors[:, :rank]
    basis = (weights.T @ rows).reshape(rank, -1, 3)
    mesh = doc.doc["meshes"][doc.doc["nodes"][node_index]["mesh"]]
    mesh["primitives"][0]["targets"] = [
        {"POSITION": doc.accessor(target, "VEC3", 5126, 34962, bounds=True)} for target in basis]
    mesh["weights"] = [0.] * rank
    _channel(doc, animation, times, node_index, "weights", weights, "SCALAR")


def _build(asset, controls, clip):
    doc = BinaryGLTF(asset)
    static = asset in industrial.names()
    if not static and asset not in rigs.catalog():
        raise ValueError(f"No procedural GLB source for {asset!r}")
    if static and (controls or clip):
        raise ValueError(f"{asset!r} is a static model")
    if clip:
        count, fps = rigs.catalog()[asset]["clips"][clip]
    else:
        count, fps = 1, 24
    lookup, samples, ids = {}, {}, {}
    source = industrial.parts(asset) if static else rigs.parts(asset, controls, clip, 1)
    for part in source:
        key, mat = part["name"], part["material"]
        if key in ids:
            raise ValueError(f"Duplicate mesh name {key!r}")
        if mat not in lookup:
            if static:
                finish = industrial.surface(mat, asset)
                finish["base"] = np.clip(_TO_LINEAR_SRGB @ finish["base"], 0, 1).tolist()
                if "emission" in finish:
                    finish["emission"] = np.maximum(_TO_LINEAR_SRGB @ finish["emission"], 0).tolist()
            else:
                finish = materials.finish(mat)
                if asset == "laptop" and mat == "display":
                    finish.update(base=(1, 1, 1), base_texture=Path(rigs.__file__).with_name("screen_ui.png"))
            lookup[mat] = doc.material(mat, finish)
        ids[key] = len(doc.doc["nodes"])
        points = _add_part(doc, part, lookup[mat])
        if clip:
            samples[key] = [points.astype(np.float32)]
    if not ids:
        raise ValueError(f"No geometry for {asset!r}")
    if clip:
        for frame in range(2, count + 1):
            seen = set()
            for part in rigs.parts(asset, controls, clip, frame):
                key = part["name"]
                pts = np.asarray(part["points"], dtype=np.float32)
                if key not in samples or key in seen or pts.shape != samples[key][0].shape:
                    raise ValueError(f"Topology changed at frame {frame} in {key!r}")
                seen.add(key)
                samples[key].append(pts)
            if seen != ids.keys():
                raise ValueError(f"Part set changed at frame {frame}")
        times = doc.accessor(np.arange(count) / fps, "SCALAR", 5126, bounds=True)
        anim = dict(name=clip, channels=[], samplers=[])
        for key in ids:
            _motion(doc, anim, times, ids[key], samples.pop(key))
        if anim["channels"]:
            doc.doc["animations"] = [anim]
    return doc


def export(path, asset, controls=None, clip=None, stilt_glb=None):
    """Write an atomic standalone GLB. Stilt preserves all original actions and maps."""
    target = Path(path)
    source = Path(stilt_glb) if asset == "stilt" else None
    if source is not None:
        if controls:
            raise ValueError("Stilt stores its controls in the original skeleton")
        if clip:
            from .stilt_asset import clips
            if clip not in clips(source):
                raise ValueError(f"Unknown Stilt clip {clip!r}")
        if source.resolve() == target.resolve():
            return target
    doc = _build(asset, controls, clip) if source is None else None
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        candidate = Path(tmp.name)
    try:
        if source is None:
            with candidate.open("wb") as handle:
                doc.write(handle)
        else:
            shutil.copyfile(source, candidate)
        os.replace(candidate, target)
    finally:
        candidate.unlink(missing_ok=True)
    return target
