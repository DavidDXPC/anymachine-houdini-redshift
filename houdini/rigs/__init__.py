"""Procedural AnyMachine rigs. Frames are one-based. Public meshes are Y-up in metres."""
import copy
import json
import math
from pathlib import Path

from . import bags, machines

ROOT = Path(__file__).resolve().parent
MEASUREMENTS = json.loads((ROOT/'measurements.json').read_text(encoding='utf-8'))
BAG_TIMING = json.loads((ROOT/'bag_timing.json').read_text(encoding='utf-8'))


def _catalog():
    quad = MEASUREMENTS['quadruped']
    joint_ranges=quad['design']['limits_deg']
    quad_controls={leg+'_'+joint: -low/(high-low) for leg in machines.quad_gait.LEGS
                   for joint,(low,high) in joint_ranges.items()}
    spider_controls={'crouch':0.}
    for leg in machines.spider_ik.LEGS:
        spider_controls.update({leg+'_'+joint:.5 for joint in ('coxa','femur','tibia')})
    result={
        'laptop':dict(controls={'open':0.},clips={'open_param':(25,24),'open_close':(96,24)}),
        'quadruped':dict(controls=quad_controls,clips={name:(count,30) for name,count in quad['actions'].items()}),
        'spider':dict(controls=spider_controls,clips={'walk':(25,24),'walk_demo':(97,24),'idle':(73,24),'crouch':(25,24)})
    }
    for name,extra in (('daypack',{'zip':0.,'pocket_fill':0.}),('rolltop',{'roll':1.,'clip':1.}),
                       ('rucksack',{'lid_open':0.})):
        controls=dict(fill=.6,strap_length=.4,**extra)
        timing=BAG_TIMING[name]
        last=max([f for f,_ in timing['keys']]+[b for _,b in timing['bob']])+8
        clips={'demo':(last,24),**{key+'_param':(25,24) for key in controls}}
        result[name]=dict(controls=controls,clips=clips)
    return result


CATALOG=_catalog()


def catalog():
    return copy.deepcopy(CATALOG)


def parts(asset, controls=None, clip=None, frame=1):
    entry=CATALOG[asset]
    values=entry['controls'].copy()
    for key,val in (controls or {}).items():
        if key not in values:
            raise ValueError(f'Unknown control {key!r} on {asset!r}')
        val=float(val)
        if not math.isfinite(val):
            raise ValueError(f'Invalid control {key!r}')
        values[key]=min(1.,max(0.,val))
    if clip is not None:
        if clip not in entry['clips']:
            raise ValueError(f'Unknown clip {clip!r} on {asset!r}')
        frame=min(entry['clips'][clip][0],max(1,float(frame)))
    if asset in BAG_TIMING:
        geometry=bags.bag(asset,values,clip,frame,BAG_TIMING[asset])
    else:
        build={'laptop':machines.laptop,'spider':machines.spider,'quadruped':machines.quadruped}[asset]
        geometry=build(MEASUREMENTS[asset],values,clip,frame)
    for mesh in geometry:
        points=mesh['points'][:,[0,2,1]].copy()
        points[:,2]*=-1
        yield dict(mesh, points=points.tolist())
