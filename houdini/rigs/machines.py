"""Measured rigid mechanisms and contact-aware animation in source-space metres."""
import math
from functools import lru_cache

import numpy as np
from . import spider_ik, quad_gait
from .geometry import ball, box, key_value, moved, ribbon, rod, rx, shell, unit


def laptop(data, c, clip, f):
    opening = c['open']
    if clip == 'open_param':
        opening = (f-1)/24
    elif clip == 'open_close':
        opening = key_value(f,[(1,0),(8,0),(44,1),(54,1),(90,0),(96,0)],True)
    axis = np.array(data['joint']['axis_origin_m'])
    width,depth,height=data['base_dims_m']
    front = data['y_back_bottom_shell']-depth
    cy = front+depth/2
    yield shell('base',[(0,cy,0,width*.47,depth*.47),
                        (0,cy,.002,width*.5,depth*.5),
                        (0,cy,height-.001,width*.5,depth*.5),
                        (0,cy,height,width*.493,depth*.49)],'aluminium',12,48)
    for r,row in enumerate((13,13,13,12,12)):
        step=.019
        for i in range(row):
            key = box(f'key_{r}_{i}',((i-(row-1)/2)*step,axis[1]-.027-.017*r,height+.0004),
                      (.017,.014,.0008),'rubber')
            yield key
    yield box('spacebar',(0,axis[1]-.113,height+.0004),(.11,.012,.0008),'rubber')
    yield box('trackpad',(0,front+.029,height+.00015),(.111,.047,.0003),'steel')
    lid=data['lid_built']
    w,l,h=lid['W'],lid['L'],lid['t']
    radius=.0038
    rotation=rx(-math.radians(135*opening))
    for i,(left,right) in enumerate(((-.125,-.088),(-.087,-.053),(.053,.087),(.088,.125))):
        yield rod(f'hinge_{i}',axis+[left,0,0],axis+[right,0,0],radius,'steel')
    # Front surfaces face down at rest; turning around +X in negative sense opens them.
    z=height+data['closed_gap_mm']/1000
    lid_center=(0,axis[1]-l*.5,z+h*.5)
    yield moved(box('lid',lid_center,(w,l,h),'aluminium'),rotation,axis)
    yield moved(box('display_bezel',(0,lid_center[1],z-.00015),(w-.005,l-.005,.0003),'rubber'),rotation,axis)
    screen=box('screen',(0,lid_center[1],z-.00036),(w-.016,l-.019,.00012),'display')
    # Top of the display is furthest from its hinge. Preserve that orientation in every pose.
    screen['uv']=[(0.,1.),(1.,1.),(1.,0.),(0.,0.)]*2
    yield moved(screen,rotation,axis)


def posed(mesh, transform):
    mesh['points'] = mesh['points'] @ transform[:3,:3].T + transform[:3,3]
    return mesh


def quad_spec(data):
    design = data['design']
    raw = data['measured_legs'].values()
    thigh = np.mean([np.array(x['knee'])-x['hip'] for x in raw],axis=0)
    shin = np.mean([np.array(x['foot'][1:])-x['knee'] for x in raw],axis=0)
    z = design['z_hip']
    hips = design['y_hip']
    legs = {}
    for name in quad_gait.LEGS:
        s = -1 if name.endswith('L') else 1
        legs[name] = dict(s=s,haa_pivot=(s*design['haa_pivot_x'],hips[name[0]],z),
                          hfe=(s*design['leg_plane_x'],hips[name[0]],z))
    return dict(body_head=(0,(hips['H']+hips['F'])/2,z),legs=legs,
                geometry=dict(t0=thigh,s0=shin,foot_r=design['foot_r'],
                              limits_rad={k:np.radians(v) for k,v in design['limits_deg'].items()}))


@lru_cache(maxsize=1)
def quad_clips():
    from . import MEASUREMENTS
    return quad_gait.build_all(quad_spec(MEASUREMENTS['quadruped']),quad_gait.DEFAULTS)


def slider_angle(limits, value):
    return limits[0]+value*(limits[1]-limits[0])


def quadruped(data,c,clip,f):
    spec=quad_spec(data)
    if clip:
        gaits,actions=quad_clips()
        pose=actions[clip][2][int(f)-1]
        body=pose['M']
        angles=pose['ang']
    else:
        gaits=quad_gait.Gaits(spec)
        body=np.eye(4)
        angles={leg:tuple(slider_angle(spec['geometry']['limits_rad'][joint],c[leg+'_'+joint])
                          for joint in ('haa','hfe','kfe')) for leg in quad_gait.LEGS}
    hw=data['body_hw']
    z0,z1=data['body_bottom'],data['body_top']
    yield posed(shell('body_shell',[(0,0,z0,.82*hw,.27),(0,0,z0+.032,hw,.317),
                                   (0,0,z1-.036,hw,.35),(0,0,z1,.78*hw,.31)],'ceramic',3.5),body)
    for name,leg in gaits.legs.items():
        a,b,k=angles[name]
        R=leg.haa_R(a)
        axis=R@np.array((leg.s,0,0))
        H=leg.P+R@(leg.H-leg.P)
        K,F,foot_rotation=leg.fk_local(a,b,k)
        # Source part planes lie in separate lateral slabs.
        def offset(point, x):
            return point+axis*(x-data['design']['leg_plane_x'])
        def cap(suffix,point,radius,x0,x1,material):
            return posed(rod(name+'_'+suffix,offset(point,x0),offset(point,x1),radius,material),body)
        yield posed(rod(name+'_haa_disc',leg.P+np.array([leg.s*.023,0,0]),
                        leg.P+np.array([leg.s*.035,0,0]),.05,'rubber'),body)
        yield cap('haa_flange',H,.022,hw+.016,hw+.025,'steel')
        yield cap('hfe_motor',H,.048,hw+.025,hw+.061,'rubber')
        yield cap('hfe_ring',H,.049,hw+.055,hw+.058,'steel')
        for suffix,p0,p1,r0,r1,x0,x1,mat in (
            ('thigh',H,K,.040,.030,hw+.063,hw+.087,'ceramic'),
            ('shin',K,F,.026,.013,hw+.039,hw+.059,'ceramic'),
            ('shin_stripe',K+.32*(F-K),K+.78*(F-K),.0065,.005,hw+.059,hw+.0605,'rubber')):
            n=unit(np.cross(axis,p1-p0))
            path=np.stack((offset(p0,(x0+x1)/2),offset(p1,(x0+x1)/2)))
            yield posed(ribbon(name+'_'+suffix,path,(r0*2,r1*2),x1-x0,mat,side=n),body)
        yield cap('knee_cap',K,.019,hw+.088,hw+.093,'rubber')
        yield cap('knee_mark',K+unit(F-K)*.009,.003,hw+.093,hw+.094,'steel')
        foot=ball(name+'_foot',F,data['design']['foot_r'],'rubber')
        yield posed(moved(foot,foot_rotation,F),body)


def spider_layout(data):
    p=data['params']
    widths={y:data['legs']['R'+str(i+1)]['yaw_axis'][0]-.006-p['rY'] for i,y in enumerate(p['hip_y'])}
    return spider_ik.layout(p,widths.__getitem__)


def spider_state(p,layout,clip,f,crouch=0.):
    if clip in ('walk','walk_demo'):
        return spider_ik.walk_state(p,layout,(f-1)/p['fps'])
    if clip=='idle':
        return spider_ik.idle_state(p,layout,(f-1)/p['fps'])
    return spider_ik.crouch_state(p,layout,(f-1)/24 if clip=='crouch' else crouch)


def spider(data,c,clip,f):
    p=data['params']
    layout=spider_layout(data)
    state=spider_state(p,layout,clip,f,c['crouch'])
    angles=spider_ik.solve_state(p,layout,state)
    pivot=np.array((0,0,p['hip_z']))
    rot=np.array(spider_ik.euler_matrix(state['body_rot']))
    drift=np.array(state['root'])+state['body_loc']
    def view(mesh):
        return moved(mesh,rot,pivot,drift)
    yield view(ball('chassis',(0,-.029,.106),(.081,.175,.039),'rubber',32,14))
    dims=data['shell']['shell_dims_m']
    yield view(ball('shell',(0,-.024,.138),np.asarray(dims)/2,'ceramic',32,14))
    for name,l in layout.items():
        yaw, elev, knee=angles[name]['yaw'],angles[name]['elev'],angles[name]['knee_rel']
        if clip is None:
            # Midpoint preserves IK, either end reaches the corresponding mechanical stop.
            values=[yaw,elev-l['e0'],knee-l['k0']]
            bounds=spider_ik.limits_local(p,l)
            for i,joint in enumerate(('coxa','femur','tibia')):
                v=2*c[name+'_'+joint]-1
                limit=bounds[joint][0 if v<0 else 1]
                values[i]+=abs(v)*(limit-values[i])
            yaw,elev,knee=values[0],l['e0']+values[1],l['k0']+values[2]
        yawrot=np.array(spider_ik.euler_matrix((0,0,yaw)))
        u=yawrot@l['u']
        a=yawrot@l['a']
        z=np.array((0.,0.,1.))
        hip=np.array(l['Y0'])
        fem=hip+u*p['L1']
        k=fem+p['L2']*(math.cos(elev)*u+math.sin(elev)*z)
        tip=k+p['L3']*(math.cos(elev+knee)*u+math.sin(elev+knee)*z)+l['c_tib']*a
        for label,begin,end,width,mat in (
            ('coxa',hip+l['c_cox']*a,fem+l['c_cox']*a,.018,'rubber'),
            ('femur',fem+l['c_fem']*a,k+l['c_fem']*a,.03,'ceramic'),
            ('tibia',k+l['c_tib']*a,tip,.023,'ceramic')):
            yield view(ribbon(label+'_'+name,[begin,end],(width,width*.68),p['wC'],mat,
                              side=unit(np.cross(a,end-begin))))
        for label,center,axis,r,length in (
            ('yaw',hip,z,p['rY'],.034),('pitch',fem,a,p['rP'],.048),('knee',k,a,p['rK'],.044)):
            yield view(rod(label+'_'+name,center-axis*length/2,center+axis*length/2,r,'steel'))
        yield view(ball('foot_'+name,tip,p['foot_r'],'rubber'))
