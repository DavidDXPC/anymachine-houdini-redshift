"""Clip the painted aircraft panels along the reference livery boundaries in model space."""
from collections import defaultdict
import numpy as np

from .geometry import Mesh, Part


def _waterline(x):
    t = max(0.0, min(1.0, (x + 1.2) / -5.1))
    return 1.035 + 1.62 * t * t * (3 - 2*t)


def _boundaries(p):
    x, _, z = p
    belt = x - (2.02 - .42*(z-1.0))
    water = z - _waterline(x)
    return (
        x-3.99, belt+.27, belt-.27, x-.86+.25*(z-2.5), z-2.49,
        water, water+.012, water-.012, x+6.12, z-2, x+6.1,
        z-2.72, z-3.38, x+6.42+.44*(z-2.72), x+7.26+.20*(z-2.72),
    )


def _color(p):
    nose, left, right, cowl, top, water, lower, upper, tail, tail_z, stripe, lo, hi, l, r = _boundaries(p)
    if nose > 0:
        return "livery_nose"
    if lower > 0 > upper and stripe > 0:
        return "livery_pinstripe"
    tail_patch = lo > 0 > hi and l < 0 < r
    if (water < 0 or (tail < 0 and tail_z > 0)) and not tail_patch:
        return "livery_navy"
    if (left > 0 > right) or (cowl > 0 and top > 0):
        return "livery_orange"
    return "white"


def _split(vertices, cut):
    distances = [v[1][cut] for v in vertices]
    if min(distances) >= -1.e-9 or max(distances) <= 1.e-9:
        return (vertices,)
    positive, negative = [], []
    prev = vertices[-1]
    for point in vertices:
        a,b = prev[1][cut], point[1][cut]
        if (a < -1.e-9 and b > 1.e-9) or (b < -1.e-9 and a > 1.e-9):
            pos = prev[0] + (point[0] - prev[0])*(a/(a-b))
            hit = pos, _boundaries(pos)
            positive.append(hit)
            negative.append(hit)
        if b >= -1.e-9:
            positive.append(point)
        if b <= 1.e-9:
            negative.append(point)
        prev = point
    return tuple(poly for poly in (positive,negative) if len(poly) >= 3)


def paint_panels(pieces):
    result = []
    for part in pieces:
        if part.material != "white":
            result.append(part)
            continue
        vertices = [(p, _boundaries(p)) for p in part.points]
        grouped = defaultdict(Mesh)
        lookup = defaultdict(dict)
        for face in part.faces:
            patches = [[vertices[i] for i in face]]
            for cut in range(len(vertices[0][1])):
                patches = [new for poly in patches for new in _split(poly,cut)]
            for patch in patches:
                color = _color(np.mean([v[0] for v in patch], axis=0))
                mesh, table = grouped[color], lookup[color]
                poly = []
                for p,_ in patch:
                    key = tuple(np.round(p,9))
                    if key not in table:
                        table[key] = mesh.verts.new(p)
                    if not poly or poly[-1] is not table[key]:
                        poly.append(table[key])
                if len(set(poly)) >= 3:
                    mesh.faces.new(poly)
        for color,mesh in grouped.items():
            name = part.name if color == "white" else part.name + "_" + color
            result.append(Part(mesh,name,color,part.tag,None))
    return result
