"""Polygon construction for the industrial kit. Recipes work in a right-handed Z-up frame."""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, cos, pi, sin, sqrt
import numpy as np


class Vector(np.ndarray):
    def __new__(cls, coords=(0,0,0)):
        return np.array(coords, dtype=float).view(cls)

    x = property(lambda self: self[0])
    y = property(lambda self: self[1])
    z = property(lambda self: self[2])
    length = property(lambda self: sqrt(self.dot(self)))

    def normalized(self):
        length = self.length
        return self / length if length else self.copy()

    def normalize(self):
        length = self.length
        if length:
            self /= length

    def cross(self, v):
        x, y, z = self
        a, b, c = v
        return Vector((y*c-z*b, z*a-x*c, x*b-y*a))

    def orthogonal(self):
        axis = np.argmin(np.abs(self))
        return self.cross(np.eye(3)[axis])

    def angle(self, v):
        return acos(float(np.clip(self.normalized().dot(Vector(v).normalized()), -1, 1)))

    def lerp(self, v, factor):
        return self + (v - self) * factor

    def rotation_difference(self, v):
        axis = self.cross(v)
        return Matrix.Rotation(self.angle(v), 3, axis if axis.length > 1e-10 else self.orthogonal())


class Matrix(np.ndarray):
    def __new__(cls, rows):
        return np.asarray(rows, dtype=float).view(cls)

    def __matmul__(self, rhs):
        if isinstance(rhs, Matrix):
            return Matrix(np.asarray(self) @ np.asarray(rhs))
        vec = np.asarray(rhs)
        if self.shape == (4, 4) and vec.shape == (3,):
            vec = np.append(vec, 1)
        return Vector((np.asarray(self) @ vec)[:3])

    @classmethod
    def Identity(cls, n):
        return cls(np.eye(n))

    @classmethod
    def Translation(cls, v):
        matrix = cls.Identity(4)
        matrix[:3, 3] = v
        return matrix

    @classmethod
    def Rotation(cls, angle, n, axis):
        if isinstance(axis, str):
            axis = np.eye(3)["XYZ".index(axis.upper())]
        x, y, z = Vector(axis).normalized()
        skew = np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        m = cls.Identity(n)
        m[:3,:3] = np.eye(3) + sin(angle)*skew + (1-cos(angle))*(skew @ skew)
        return m

    @classmethod
    def Diagonal(cls, values):
        return cls(np.diag(values))

    @classmethod
    def Scale(cls, factor, n, axis=None):
        m = cls.Identity(n)
        if axis is None:
            m[:3,:3] *= factor
        else:
            a = Vector(axis).normalized()
            m[:3,:3] += (factor-1)*np.outer(a,a)
        return m

    def inverted(self):
        return Matrix(np.linalg.inv(self))

    def to_matrix(self):
        return self

    def to_4x4(self):
        m = Matrix.Identity(4)
        m[:3,:3] = self[:3,:3]
        return m

    def to_3x3(self):
        return Matrix(self[:3,:3])


@dataclass(eq=False)
class Vertex:
    co: Vector
    index: int


class Vertices(list):
    def new(self, coordinate):
        point = Vertex(Vector(coordinate), len(self))
        self.append(point)
        return point


class Face(list):
    @property
    def normal(self):
        # Newell's method stays stable on faces with collinear leading edges.
        coords = np.asarray([p.co for p in self])
        return Vector(np.cross(coords, np.roll(coords,-1,axis=0)).sum(axis=0)).normalized()

    def calc_center_median(self):
        return Vector(np.mean([p.co for p in self], axis=0))

    def normal_flip(self):
        self.reverse()


class Faces(list):
    def new(self, vertices):
        face = Face(vertices)
        self.append(face)
        return face


class Mesh:
    def __init__(self):
        self.verts = Vertices()
        self.faces = Faces()

    def orient_outward(self):
        if not self.faces:
            return
        center = Vector(np.mean([v.co for v in self.verts], axis=0))
        # The ring lofts have consistent winding; test one exterior side.
        for f in self.faces:
            facing = f.normal.dot(f.calc_center_median() - center)
            if abs(facing) > 1e-9:
                if facing < 0:
                    for side in self.faces:
                        side.reverse()
                return


class Part:
    def __init__(self, mesh, name, material, tag, xf):
        self.name, self.material, self.tag = name, material, tag
        self.points = np.asarray([v.co for v in mesh.verts], dtype=float).reshape(-1,3)
        self.faces = [[v.index for v in face] for face in mesh.faces if len(face) >= 3]
        if xf is not None:
            self.transform(xf)

    def transform(self, matrix):
        self.points = self.points @ np.asarray(matrix[:3, :3]).T + np.asarray(matrix[:3, 3])

    def flip_normals(self):
        for f in self.faces:
            f.reverse()

    def output(self, matrix=None):
        points = self.points
        if matrix is not None:
            points = points @ np.asarray(matrix[:3,:3]).T + np.asarray(matrix[:3,3])
        return dict(name=self.name, points=(points[:,(0,2,1)] * (1,1,-1)).tolist(),
                    faces=self.faces, material=self.material)


def box_mesh(mn, mx, bevel, skip, axes, bevel_all, flip):
    """Clip a box at selected edge planes; preserve selectively omitted sides."""
    mn, mx = np.minimum(mn,mx), np.maximum(mn,mx)
    indices = [[0,4,6,2],[1,3,7,5],[0,1,5,4],[2,6,7,3],[0,2,3,1],[4,5,7,6]]
    corners = [np.where([(i>>k)&1 for k in range(3)],mx,mn) for i in range(8)]
    polys = [(side, [corners[i] for i in face]) for side,face in zip(("-x","+x","-y","+y","-z","+z"),indices)]
    widths = mx-mn
    for axis in range(3):
        if bevel <= 0 or (axes and 'xyz'[axis] not in axes):
            continue
        a,b = (axis+1)%3, (axis+2)%3
        cut = min(bevel,min(widths[a],widths[b])*0.49)
        if cut <= 0:
            continue
        for s in (-1,1):
            for t in (-1,1):
                adjacent = [("-" if sign < 0 else "+") + 'xyz'[k] for k,sign in ((a,s),(b,t))]
                if not bevel_all and any(label in skip for label in adjacent):
                    continue
                normal = np.zeros(3); normal[a],normal[b]=s,t
                distance = s*(mn[a] if s<0 else mx[a])+t*(mn[b] if t<0 else mx[b])-cut
                boundary, clipped = {}, []
                for label, poly in polys:
                    keep=[]
                    for prev,p in zip(poly[-1:] + poly[:-1],poly):
                        h0,h1 = np.dot(prev,normal)-distance,np.dot(p,normal)-distance
                        if (h0>1e-9)!=(h1>1e-9):
                            q = prev + (p-prev)*(h0/(h0-h1))
                            keep.append(q); boundary[tuple(np.round(q,10))]=q
                        if h1<=1e-9:
                            keep.append(p)
                    if len(keep)>=3:
                        clipped.append((label,keep))
                edge = list(boundary.values())
                if len(edge)>=3:
                    center=np.mean(edge,axis=0)
                    u=np.eye(3)[axis]; v=np.cross(normal,u)
                    edge.sort(key=lambda p: np.arctan2(np.dot(p-center,v),np.dot(p-center,u)))
                    clipped.append(("",edge))
                polys=clipped
    mesh, table = Mesh(), {}
    for label, poly in polys:
        if label and label in skip:
            continue
        face=[]
        for p in poly:
            key=tuple(np.round(p,10))
            if key not in table:
                table[key]=mesh.verts.new(p)
            if not face or table[key] is not face[-1]:
                face.append(table[key])
        if len(face)>1 and face[0] is face[-1]:
            face.pop()
        if len(set(face))>=3:
            mesh.faces.new(reversed(face) if flip else face)
    return mesh
