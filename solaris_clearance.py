"""Camera-to-surface clearance in OpenUSD. Points and distances use stage units."""
import numpy as np
from pxr import Sdf, Usd, UsdGeom


def _triangle_distances(p, a, b, c):
    """Squared distance to each triangle, including edges and degenerate faces."""
    ab, ac, ap = b - a, c - a, p - a
    normal = np.cross(ab, ac)
    n2 = np.einsum("ij,ij->i", normal, normal)
    signed = np.einsum("ij,ij->i", ap, normal)
    safe = np.maximum(n2, np.finfo(float).tiny)
    q = p - normal * (signed / safe)[:, None]
    inside = n2 > 0
    edge_min = np.full(len(a), np.inf)
    for x, y in ((a,b),(b,c),(c,a)):
        edge = y - x
        rel = p - x
        t = np.einsum("ij,ij->i", rel, edge) / np.maximum(np.einsum("ij,ij->i", edge, edge), 1e-30)
        dist = rel - edge * t.clip(0, 1)[:, None]
        edge_min = np.minimum(edge_min, np.einsum("ij,ij->i", dist, dist))
        inside &= np.einsum("ij,ij->i", np.cross(edge, q-x), normal) >= -1e-14*n2
    return np.where(inside, signed**2 / safe, edge_min)


def _included(path, roots):
    return any(path == root or path.startswith(root.rstrip("/") + "/") for root in roots)


class Clearance:
    def __init__(self, stage, include=None, exclude=()):
        for paths in (include,exclude):
            if paths is None:
                continue
            if isinstance(paths,str) or any(not Sdf.Path(p).IsAbsolutePath() for p in paths):
                raise ValueError("Clearance selectors must be lists of absolute USD prim paths")
            missing = [p for p in paths if not stage.GetPrimAtPath(p)]
            if missing:
                raise ValueError(f"Missing clearance prims: {missing}")
        self.items = []
        self.stage = stage
        for prim in stage.Traverse(Usd.TraverseInstanceProxies()):
            path = str(prim.GetPath())
            if not prim.IsA(UsdGeom.Gprim) or _included(path, exclude):
                continue
            if include is not None and not _included(path, include):
                continue
            if not include and prim.IsA(UsdGeom.Points):
                continue
            im = UsdGeom.Imageable(prim)
            if im.ComputePurpose() in ("guide", "proxy"):
                continue
            self.items.append(prim)
        self.local_meshes = {}

    def _triangles(self, prim, time):
        mesh = UsdGeom.Mesh(prim)
        if not mesh:
            return None
        attrs = mesh.GetPointsAttr(), mesh.GetFaceVertexCountsAttr(), mesh.GetFaceVertexIndicesAttr(), mesh.GetHoleIndicesAttr()
        stable = not any(attr.ValueMightBeTimeVarying() for attr in attrs)
        path = prim.GetPath()
        if stable and path in self.local_meshes:
            return self.local_meshes[path]
        points = np.asarray(attrs[0].Get(time), dtype=float)
        counts = attrs[1].Get(time)
        indices = np.asarray(attrs[2].Get(time), dtype=int)
        holes = set(attrs[3].Get(time) or ())
        triangles, start = [], 0
        for face_index, count in enumerate(counts):
            if count >= 3 and face_index not in holes:
                face = indices[start:start+count]
                triangles.extend((face[0], face[i], face[i+1]) for i in range(1, count-1))
            start += count
        result = points, np.asarray(triangles, dtype=int).reshape(-1,3)
        if stable:
            self.local_meshes[path] = result
        return result

    def hits(self, eye, frame, radius, meters):
        """Exact distances to mesh triangles; analytic primitives use conservative bounds."""
        t = Usd.TimeCode(frame)
        cache = UsdGeom.BBoxCache(t, ["default", "render"], useExtentsHint=False)
        xforms = UsdGeom.XformCache(t)
        hits = []
        p = np.array(eye)
        for prim in self.items:
            if UsdGeom.Imageable(prim).ComputeVisibility(t) == "invisible":
                continue
            box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
            if box.IsEmpty():
                continue
            distance = np.linalg.norm(np.maximum(np.maximum(np.array(box.GetMin()) - p, p - box.GetMax()), 0))
            if distance >= radius:
                continue
            data = self._triangles(prim, t)
            if data is not None:
                points, indices = data
                if not len(indices):
                    continue
                m = np.asarray(xforms.GetLocalToWorldTransform(prim))
                world = points @ m[:3,:3] + m[3,:3]
                a, b, c = world[indices].transpose(1,0,2)
                distance = float(np.sqrt(_triangle_distances(p, a, b, c).min()))
            if distance < radius:
                hits.append(dict(frame=frame, prim=str(prim.GetPath()), distance_m=float(distance*meters)))
        return hits
