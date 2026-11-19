"""Sweep AnyMachine's six procedural rigs using Python and NumPy, outside a DCC."""
import argparse
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from houdini import rigs
from houdini.rigs import machines, spider_ik, surface_check


def poses(asset, **kwargs):
    return {m['name']: (np.asarray(m['points']), m['faces']) for m in rigs.parts(asset,**kwargs)}


def geometry_check(reference, sample):
    if reference.keys()!=sample.keys():
        raise ValueError('Part names changed')
    max_move=0.
    for key,(p,faces) in sample.items():
        initial,original=reference[key]
        if p.shape!=initial.shape or faces!=original or not np.isfinite(p).all():
            raise ValueError(f'Unstable topology or non-finite points on {key}')
        max_move=max(max_move,float(np.max(np.linalg.norm(p-initial,axis=1))))
    return max_move


def millimeters(m):
    return round(1000*float(m),6)


def graph_samples(last,step):
    return sorted(set(range(1,last+1,step))|{last})


def foot_frame(points):
    # The procedural sphere has two poles and 16 points on each of its nine latitude rings.
    # Their order survives skinning. Read the orientation from the mesh, not the gait target.
    center=(points[-1]+points[0])*.5
    vertical=machines.unit(points[-1]-points[0])
    equator=machines.unit(points[1+4*16]-center)
    basis=np.column_stack((equator,np.cross(vertical,equator),vertical))
    return center,basis


def contact(asset,clip,entry):
    data=rigs.MEASUREMENTS[asset]
    count,fps=entry['clips'][clip]
    if asset=='quadruped':
        gaits,actions=machines.quad_clips()
        _,schedule,solutions=actions[clip]
        names=list(gaits.legs)
        r=data['design']['foot_r']
    else:
        names=spider_ik.LEGS
        r=data['params']['foot_r']
        layout=machines.spider_layout(data)
    prev={}
    starts={}
    totals={}
    stance_runs=0
    target_error=ground_error=worst=step_max=0.
    for f in range(1,count+1):
        mod=poses(asset,clip=clip,frame=f)
        if asset=='spider':
            st=machines.spider_state(data['params'],layout,clip,f)
        for leg in names:
            if asset=='quadruped':
                target=actions[clip][0][f-1]['feet'][leg]
                down=schedule[f-1][leg]
                key=leg+'_foot'
            else:
                target=st['feet'][leg]
                down=st['stance'][leg]
                key='foot_'+leg
            center,basis=foot_frame(mod[key][0])
            target=np.array([target[0],target[2],-target[1]])
            target_error=max(target_error,np.linalg.norm(center-target))
            if down:
                ground_error=max(ground_error,abs(center[1]-r))
                if leg not in prev:
                    starts[leg]=center.copy()
                    totals[leg]=0.
                    stance_runs+=1
                elif asset=='spider':
                    # Fixed ankle centre. Upstream's IK target is the centre of the ball foot.
                    displacement=(center-starts[leg])[[0,2]]
                    worst=max(worst,np.linalg.norm(displacement))
                    step_max=max(step_max,np.linalg.norm((center-prev[leg][0])[[0,2]]))
                else:
                    # Track the previous frame's ground contact through the current sphere rotation.
                    old,orientation=prev[leg]
                    delta=center-old+(basis@orientation.T-np.eye(3))@np.array((0,-r,0))
                    if clip=='trot':
                        # In-place treadmill: belt moves backwards along Z.
                        delta[2]+=machines.quad_gait.DEFAULTS['step_length']/(count-1)
                    step=np.linalg.norm(delta[[0,2]])
                    totals[leg]+=step
                    step_max=max(step_max,step)
                    worst=max(worst,totals[leg])
                prev[leg]=(center,basis)
            else:
                prev.pop(leg,None)
    result=dict(stance_runs=stance_runs,frames=count,maximum_target_error_mm=millimeters(target_error),
                maximum_stance_height_error_mm=millimeters(ground_error),maximum_step_displacement_mm=millimeters(step_max))
    key='maximum_stance_center_drift_mm' if asset=='spider' else 'maximum_accumulated_rolling_slip_per_stance_mm'
    result[key]=millimeters(worst)
    result['contact_reference']='moving belt' if clip=='trot' else 'stationary ground'
    if asset=='quadruped':
        result['unreachable_frames']=sum(not sol['reach'] for sol in solutions)
    return result


def laptop_gap(data):
    # Vertical gap at deck/keyboard top vertices and top-face centres whose vertical lines hit the moving assembly.
    ref=poses('laptop')
    samples=[]
    for name,(points,faces) in ref.items():
        if name not in ('base','trackpad','spacebar') and not name.startswith('key_'):
            continue
        idx=np.array([i for i,p in enumerate(points) if p[1]>=points[:,1].max()-1e-9])
        samples.extend(points[idx])
        samples.append(points[idx].mean(axis=0))
    samples=np.asarray(samples)
    gaps=[]
    for amount in data:
        model=poses('laptop',controls={'open':amount})
        lowest=math.inf
        for name in ('lid','screen','display_bezel'):
            vertices,faces=model[name]
            for face in faces:
                for j in range(1,len(face)-1):
                    a,b,c=vertices[[face[0],face[j],face[j+1]]]
                    ab,ac=b-a,c-a
                    ab2,ac2=ab[[0,2]],ac[[0,2]]
                    det=ab2[0]*ac2[1]-ab2[1]*ac2[0]
                    if abs(det)<1e-13:
                        continue
                    d=samples[:,[0,2]]-a[[0,2]]
                    u=(d[:,0]*ac2[1]-d[:,1]*ac2[0])/det
                    v=(ab2[0]*d[:,1]-ab2[1]*d[:,0])/det
                    inside=(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)
                    if inside.any():
                        clearance=a[1]+u*ab[1]+v*ac[1]-samples[:,1]
                        lowest=min(lowest,clearance[inside].min())
        if np.isfinite(lowest):
            gaps.append((lowest,float(amount)))
    return dict(closed_vertical_gap_mm=millimeters(gaps[0][0]),
                minimum_sampled_vertical_gap_mm=millimeters(min(gaps)[0]),open_at_minimum=min(gaps)[1],
                positions=len(data),deck_samples=len(samples),positions_with_projected_overlap=len(gaps))


def bag_coupling(asset,entry,intervals):
    pairs={'rolltop':[('roll','clip'),('fill','roll'),('fill','strap_length')],
           'daypack':[('zip','fill'),('zip','pocket_fill'),('fill','strap_length')],
           'rucksack':[('fill','lid_open'),('fill','strap_length')]}[asset]
    grid=np.linspace(0,1,intervals+1)
    ref=poses(asset)
    results={}
    for a,b in pairs:
        low=(math.inf,None,None,None)
        max_buckle=0.
        for x,y in itertools.product(grid,repeat=2):
            settings={a:x,b:y}
            g=poses(asset,controls=settings)
            geometry_check(ref,g)
            for label,(p,_) in g.items():
                value=p[:,1].min()
                if value<low[0]:
                    low=(value,label,x,y)
            if asset=='rolltop' and (entry['controls']|settings)['clip']==1 and (entry['controls']|settings)['roll']==1:
                for leg in ('L','R'):
                    female=g['buckle_f_'+leg][0].mean(axis=0)
                    male=g['buckle_m_'+leg][0].mean(axis=0)
                    max_buckle=max(max_buckle,np.linalg.norm((female-male)[[0,2]]))
        item=dict(states=len(grid)**2,minimum_vertex_height_mm=millimeters(low[0]),part=low[1],
                  floor_respected=bool(low[0]>=-1e-9),topology_stable=True,
                  controls_at_minimum={a:float(low[2]),b:float(low[3])})
        if asset=='rolltop':
            item['closed_buckle_horizontal_misalignment_mm']=millimeters(max_buckle)
        results[a+' + '+b]=item
    return results


def run_asset(asset,entry,control_steps,clip_step,surfaces):
    ref=poses(asset)
    values=np.linspace(0.,1.,control_steps+1)
    for name,(p,faces) in ref.items():
        if not faces or not len(p) or not np.isfinite(p).all() or any(len(f)<3 or min(f)<0 or max(f)>=len(p) for f in faces):
            raise ValueError(f'Invalid rest topology in {name}')
    result={'parts':len(ref),'controls':{},'clips':{}}
    for key in entry['controls']:
        motion=0.
        previous=None
        for value in values:
            geometry=poses(asset,controls={key:value})
            geometry_check(ref,geometry)
            if previous:
                motion=max(motion,geometry_check(previous,geometry))
            previous=geometry
        for value,extreme in ((-.3,0),(1.4,1)):
            difference=geometry_check(poses(asset,controls={key:extreme}),poses(asset,controls={key:value}))
            if difference>1e-9:
                raise ValueError(f'Out-of-range value survived clamp of {key}')
        if motion<=1e-9:
            raise ValueError(f'Control {key} never moved geometry')
        result['controls'][key]={'states':len(values),'clamp_checked':True,'largest_sample_step_mm':millimeters(motion)}
    for clip,(count,fps) in entry['clips'].items():
        frames=graph_samples(count,clip_step)
        initial=poses(asset,clip=clip,frame=1)
        motion=0.
        for frame in frames:
            motion=max(motion,geometry_check(initial,poses(asset,clip=clip,frame=frame)))
        if len(frames)==count and motion<=1e-9:
            raise ValueError(f'Clip {clip} never moved geometry')
        item=dict(frames=count,fps=fps,sampled_frames=len(frames),maximum_displacement_from_first_mm=millimeters(motion))
        if asset in ('quadruped','spider'):
            item['contact']=contact(asset,clip,entry)
        result['clips'][clip]=item
    if asset=='laptop':
        result['lid_clearance']=laptop_gap(values)
    if asset in rigs.BAG_TIMING:
        result['coupled_controls']=bag_coupling(asset,entry,4)
    if surfaces:
        settings=[('rest',{},None,1)]
        if asset in rigs.BAG_TIMING:
            for key in entry['controls']:
                settings.append((key+'_opposite',{key:float(entry['controls'][key]<.5)},None,1))
        elif asset=='laptop':
            settings.extend((str(key),{'open':key},None,1) for key in (.5,1.))
        else:
            settings.extend((c,{},c,1+(n-1)//3) for c,(n,_) in entry['clips'].items())
        result['selected_surface_intersections']={label:surface_check.inspect(asset,list(rigs.parts(asset,controls,clip,frm)))
                                                  for label,controls,clip,frm in settings}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset',choices=rigs.catalog(),action='append',help='Repeat to select rigs; default is all six.')
    parser.add_argument('--control-steps',type=int,default=20,help='Intervals per normalized control, including both endpoints.')
    parser.add_argument('--clip-step',type=int,default=1,help='Frame stride for topology sampling. Contact always uses every frame.')
    parser.add_argument('--surfaces',action='store_true',help='Measure triangle intersections for selected part pairs in representative poses.')
    parser.add_argument('--json',type=Path,help='Write the full report here. The default prints JSON to stdout.')
    args=parser.parse_args()
    if args.control_steps<1 or args.clip_step<1:
        parser.error('Sample intervals and stride must be positive.')
    catalog=rigs.catalog()
    report={'units':'metres in the mesh, millimetres in the report','assets':{},
            'measurement_scope':'Procedural polygon poses before USD export. Ground is Y=0. Spider uses fixed centre drift. '
            'Quadruped uses the material contact point of a rolling ball. Laptop gap samples vertical projections of deck points. '
            'Bag coupling sweeps a 5 x 5 grid and measures floor clearance and, on a closed rolltop, horizontal buckle alignment. '
            'Optional triangle intersections are sampled surface contacts including touching; they exclude pure containment, '
            'untested pairs, self-intersection, and frames or parameter values outside each sample.'}
    for asset in args.asset or catalog:
        print(f'Checking {asset}...',file=sys.stderr,flush=True)
        report['assets'][asset]=run_asset(asset,catalog[asset],args.control_steps,args.clip_step,args.surfaces)
    output=json.dumps(report,indent=2,allow_nan=False)
    if args.json:
        args.json.write_text(output+'\n',encoding='utf-8')
    else:
        print(output)


if __name__=='__main__':
    main()
