"""Polygon primitives in source-space metres (Z up). Convert once at the public boundary."""
import math
import numpy as np


def part(name, material, points, faces):
    return dict(name=name, material=material, points=np.asarray(points, dtype=float),
                faces=[tuple(face) for face in faces])


def box(name, c, size, material):
    half = np.asarray(size) * 0.5
    corners = np.array([(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                        (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)])
    return part(name, material, c + corners * half,
                [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])


def loft(name, rings, material, caps=True):
    rings = np.asarray(rings)
    levels, count, _ = rings.shape
    faces = []
    for row in range(levels - 1):
        for i in range(count):
            j = (i + 1) % count
            a = row * count
            faces.append((a+i,a+j,a+count+j,a+count+i))
    if caps:
        faces += [tuple(reversed(range(count))), tuple(range((levels-1)*count, levels*count))]
    return part(name, material, rings.reshape((-1,3)), faces)


def shell(name, levels, material, exponent=3.2, segments=32):
    """Rounded section shell. Each level contains center and half-width/half-depth."""
    t = np.arange(segments) * (2*math.pi/segments)
    shape = np.stack((np.cos(t), np.sin(t)), axis=-1)
    shape = np.sign(shape) * abs(shape)**(2/exponent)
    rings = [np.column_stack((x+rx*shape[:,0], y+ry*shape[:,1], np.full(segments,z)))
             for x,y,z,rx,ry in levels]
    return loft(name, rings, material)


def unit(v):
    v = np.asarray(v,dtype=float)
    return v / max(1e-12, np.linalg.norm(v))


def rod(name, a, b, radius, material, end_radius=None, segments=16):
    a, b = np.array(a), np.array(b)
    axis = unit(b-a)
    ref = (0,0,1) if abs(axis[2]) < .9 else (1,0,0)
    u = unit(np.cross(ref,axis))
    v = np.cross(axis,u)
    t = np.arange(segments) * (2*math.pi/segments)
    ring = np.outer(np.cos(t),u) + np.outer(np.sin(t),v)
    return loft(name, (a+radius*ring,b+(radius if end_radius is None else end_radius)*ring), material)


def ball(name, center, radius, material, sides=16, levels=10):
    center = np.array(center)
    radii = np.broadcast_to(radius,3)
    # Real poles keep the tessellation manifold.
    points = [(0,0,-1)]
    for j in range(1,levels):
        lat = math.pi*j/levels - math.pi/2
        for i in range(sides):
            lon = 2*math.pi*i/sides
            points.append((math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)))
    top = len(points)
    points.append((0,0,1))
    faces = [(0,1+(i+1)%sides,1+i) for i in range(sides)]
    for j in range(levels-2):
        a = 1+j*sides
        for i in range(sides):
            k=(i+1)%sides
            faces.append((a+i,a+k,a+sides+k,a+sides+i))
    faces += [(top-sides+i,top-sides+(i+1)%sides,top) for i in range(sides)]
    return part(name,material,center+np.asarray(points)*radii,faces)


def ribbon(name, centers, widths, thickness, material, side=(1,0,0)):
    """Sweep a strap on fixed-width axis with section normal from its tangent."""
    path = np.asarray(centers,dtype=float)
    widths = np.broadcast_to(widths,len(path))
    rings = []
    for i,p in enumerate(path):
        tangent = unit(path[min(i+1,len(path)-1)]-path[max(i-1,0)])
        normal = unit(np.cross(side,tangent))
        half_side = unit(np.cross(tangent,normal))*widths[i]/2
        half_normal = normal*thickness/2
        rings.append([p-half_side-half_normal,p-half_side+half_normal,
                      p+half_side+half_normal,p+half_side-half_normal])
    return loft(name,rings,material)


def moved(mesh, rot, origin, offset=(0,0,0)):
    origin = np.asarray(origin)
    mesh = dict(mesh)
    mesh['points'] = (mesh['points']-origin) @ np.asarray(rot).T + origin + offset
    return mesh


def rx(a):
    c,s=math.cos(a),math.sin(a)
    return np.array(((1,0,0),(0,c,-s),(0,s,c)))


def ry(a):
    c,s=math.cos(a),math.sin(a)
    return np.array(((c,0,s),(0,1,0),(-s,0,c)))


def smooth(x):
    x=min(1,max(0,x))
    return x*x*(3-2*x)


def key_value(frame, keys, ease=False):
    for (fa,a),(fb,b) in zip(keys,keys[1:]):
        if frame <= fb:
            t = min(1,max(0,(frame-fa)/(fb-fa)))
            return a + (b-a)*(smooth(t) if ease else t)
    return keys[-1][1]
