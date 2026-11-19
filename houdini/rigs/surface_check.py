"""Compare sampled polygon surfaces using the triangle separating-axis test."""
from itertools import combinations
import numpy as np


def triangles(mesh):
    vertices=np.asarray(mesh['points'])
    indices=[(face[0],face[i],face[i+1]) for face in mesh['faces'] for i in range(1,len(face)-1)]
    return vertices[np.asarray(indices)]


def hits(a,b,tolerance=1e-9):
    """Includes touching. Fan-triangulates polygon faces. Does not detect pure containment."""
    a_lo,a_hi=a.min(axis=1),a.max(axis=1)
    b_lo,b_hi=b.min(axis=1),b.max(axis=1)
    if np.any(a_lo.min(axis=0)>b_hi.max(axis=0)+tolerance) or np.any(b_lo.min(axis=0)>a_hi.max(axis=0)+tolerance):
        return False
    for i,t in enumerate(a):
        candidates=b[((b_hi>=a_lo[i]-tolerance)&(b_lo<=a_hi[i]+tolerance)).all(axis=1)]
        if not len(candidates):
            continue
        ea=np.roll(t,-1,axis=0)-t
        eb=np.roll(candidates,-1,axis=1)-candidates
        na=np.cross(ea[0],ea[1])
        nb=np.cross(eb[:,0],eb[:,1])
        if np.linalg.norm(na)<1e-15:
            continue
        legal=np.linalg.norm(nb,axis=1)>1e-15
        # Edge cross products handle skew triangles. The in-plane axes handle coplanar triangles.
        axes=np.concatenate((np.tile(na,(len(eb),1,1)),nb[:,None,:],
                             np.cross(ea[None,:,None,:],eb[:,None,:,:]).reshape(len(eb),9,3),
                             np.broadcast_to(np.cross(na,ea),(len(eb),3,3)),np.cross(nb[:,None,:],eb)),axis=1)
        norm=np.linalg.norm(axes,axis=-1)
        pa=np.einsum('mki,pi->mkp',axes,t)
        pb=np.einsum('mki,mpi->mkp',axes,candidates)
        separated=(pa.max(axis=2)<pb.min(axis=2)-tolerance*norm)|(pb.max(axis=2)<pa.min(axis=2)-tolerance*norm)
        if np.any(legal & ~separated.any(axis=1)):
            return True
    return False


def selected_pairs(asset, meshes):
    if asset=='laptop':
        for moving in ('lid','display_bezel','screen'):
            for fixed in meshes:
                if fixed in ('base','trackpad','spacebar') or fixed.startswith('key_'):
                    yield moving,fixed
    elif asset in ('quadruped','spider'):
        # Pairs between limbs only; exclude each limb's own joints and intended mating faces.
        items=[k for k in meshes if k.endswith(('_shin','_thigh')) or k.startswith(('coxa_','femur_','tibia_'))]
        for a,b in combinations(items,2):
            if (a.split('_')[0] if asset=='quadruped' else a.split('_')[1]) != (
                    b.split('_')[0] if asset=='quadruped' else b.split('_')[1]):
                yield a,b
    else:
        for other in meshes:
            if other in ('panel','zip_pull','lid','collar') or other.startswith(('buckle_m_','buckle_f_')):
                yield 'body',other


def inspect(asset, meshes):
    meshes={m['name']:m for m in meshes}
    cached={}
    collisions=[]
    for a,b in selected_pairs(asset,meshes):
        for name in (a,b):
            if name not in cached:
                cached[name]=triangles(meshes[name])
        if hits(cached[a],cached[b]):
            collisions.append([a,b])
    return collisions
