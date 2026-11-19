"""Soft-goods rebuilds from the measured silhouettes and original control schedules."""
import math
import numpy as np

from .geometry import ball, box, key_value, loft, moved, part, ribbon, rx, ry, shell, smooth, unit


def roll_section(amount, top):
    count, length, pitch, core = 67,.4,.007,.012
    step=length/count
    turns=2.5*amount
    rolled=2*math.pi*turns*core+math.pi*pitch*turns**2
    def integral(d):
        return 2*math.pi/pitch*math.sqrt(core**2+pitch*d/math.pi)
    centers=[np.array((0,.0105,top-.004))]
    angles=[0.]
    for i in range(count):
        lo=max(0.,length-(i+1)*step)
        hi=min(length-i*step,rolled)
        bend=integral(hi)-integral(lo) if hi>lo else 0.
        mid=angles[-1]+bend/2
        centers.append(centers[-1]+step*np.array((0,-math.sin(mid),math.cos(mid))))
        angles.append(angles[-1]+bend)
    return centers,angles


def rolltop(c,top):
    centers,angles=roll_section(c['roll'],top)
    rings=[]
    ts=np.arange(40)*math.tau/40
    for i,(center,a) in enumerate(zip(centers,angles)):
        flat=smooth((.4*i/67)/.045)
        dx=(1+.06*flat)*.175*np.cos(ts)
        dy=((1-flat)*.098+flat*.0016)*np.sin(ts)
        rings.append(center+np.column_stack((dx,dy*math.cos(a),dy*math.sin(a))))
    yield loft('collar',rings[:-2],'coated',False)
    yield loft('stiffener',rings[-3:],'webbing',False)
    # The side straps close against the fully rolled collar.
    locked=roll_section(1.,top)[0][-1]
    for s,label in ((-1,'R'),(1,'L')):
        dx=s*(.175*1.06+.012)
        tip=centers[-1]+np.array((dx,0,-.012))
        start=np.array((s*(.175*(.94+.1*c['fill'])+.011),.0105,.24))
        target=locked+np.array((dx,0,-.038))
        t=smooth(c['clip'])
        direction=unit((1-t)*np.array([s*.05,0,-1])+t*unit(target-start)+
                       np.array((s*.35*math.sin(math.pi*t),0,0)))
        end=start+direction*((1-t)*.08+t*np.linalg.norm(target-start))
        yield ribbon('side_'+label,[start,end],.029,.003,'webbing',side=(0,1,0))
        yield box('buckle_m_'+label,tip,(.014,.041,.033),'rubber')
        yield box('buckle_f_'+label,end,(.016,.044,.031),'rubber')


def daypack(c,top,width,depth):
    # The edge of the sewn panel follows the U path from the lower right to lower left.
    cols,rows=37,53
    fractions=np.linspace(0,1,rows)
    widths=width*(1-.21*fractions**4-.045*(1-fractions)**3)
    zbase=.06
    zroof=top-.076
    ys,zs=np.full(rows,-depth*.94),zbase+fractions*(zroof-zbase)
    x=np.linspace(-1,1,cols)
    panel=[]
    for w,y,z,t in zip(widths,ys,zs,fractions):
        row=np.column_stack((x*w, y-.014*(1-x*x)*math.sin(math.pi*t)**.7, np.full(cols,z)))
        row[:,2]+=.012*(1-x*x)*t*t
        panel.append(row)
    panel=np.array(panel)
    path=np.concatenate((panel[:,-1],panel[-1,-2::-1],panel[-2::-1,0]),axis=0)
    distances=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    travel=c['zip']*distances[-1]
    # Pin within 15 cm of still-closed teeth. Interpolate the original 12 in-between poses.
    def ease(values):
        u=np.clip(values,0,1)
        return u*u*(3-2*u)
    def shape(amount):
        posed=panel.copy()
        zipped=path[distances > amount*distances[-1]+.01]
        opening=math.radians(98)*smooth((amount-.1)/.9)**1.15
        for row in posed:
            nearest=np.linalg.norm(row[:,None]-zipped,axis=2).min(axis=1) if len(zipped) else np.ones(cols)
            weight=ease(nearest/.15)*ease((row[:,2]-zbase+.005)/.065)
            sag=math.radians(16)*math.sin(opening)*ease((row[:,2]-zbase)/(.4-zbase))
            angle=weight*(opening+sag)
            dz=row[:,2]-zbase
            dy=row[:,1]+depth*.94
            row[:,1]=-depth*.94+dy*np.cos(angle)-dz*np.sin(angle)
            row[:,2]=np.maximum(.003,zbase+dy*np.sin(angle)+dz*np.cos(angle))
        return posed
    k=12*c['zip']
    lo=math.floor(k)
    blend=k-lo
    posed=shape(lo/12)
    if blend:
        posed+=blend*(shape((lo+1)/12)-posed)
    thickness=ease(np.minimum(np.minimum(.117-np.abs(panel[:,:,0]),panel[:,:,2]-.03),
                              .193-panel[:,:,2])/.035)*c['pocket_fill']
    posed[:,:,1]-=.022*thickness
    posed[:,:,2]+=.002*thickness
    faces=[]
    for j in range(rows-1):
        for i in range(cols-1):
            a=j*cols+i
            faces.append((a,a+1,a+1+cols,a+cols))
    yield part('panel','canvas',posed.reshape((-1,3)),faces)
    # A continuous track at the opening, with slider sampled by arc length.
    yield ribbon('zip_track',path,.006,.003,'webbing',side=(0,1,0))
    slider=np.array([np.interp(travel,distances,path[:,i]) for i in range(3)])
    slider[1]-=.008
    yield box('zip_slider',slider,(.012,.008,.02),'steel')
    end=slider+np.array((.002,-.012,-.032))
    yield ribbon('zip_cord',[slider,end],.004,.003,'webbing')
    yield box('zip_pull',end,(.012,.004,.019),'rubber')


def rucksack(c,top,width,depth):
    # The five links peel off the collar progressively, with the tip trailing the root.
    hinge=np.array((0,.1065,top-.035))
    profile=np.array([(.015,.465),(.035,.530),(.020,.585),(-.020,.612),(-.075,.612),(-.135,.585)])
    lengths=np.linalg.norm(np.diff(profile,axis=0),axis=1)
    closed=(93.6,130.8,160.1,181.2,-157.4)
    raised=(72.9,105.3,146.,180.,-155.8)
    centers=[hinge]
    for i,(l,lo,hi) in enumerate(zip(lengths,closed,raised)):
        opening=c['lid_open']
        if opening>.65:
            a=hi-(50+30*(i/4)**1.3)*(opening-.65)/.35
        else:
            t=opening/.65
            a=lo+(hi-lo)*t**(1+.9*i/4)-14*math.sin(math.pi*t)*(i/4)**1.5
        a=math.radians(a)
        centers.append(centers[-1]+np.array((0,math.cos(a)*l,math.sin(a)*l)))
    yield ribbon('lid',centers,[width*v for v in (1.47,1.91,1.98,1.95,1.82,1.58)],.008,'canvas')
    for s,label in ((-1,'R'),(1,'L')):
        end=centers[-1]+np.array((s*width*.58,-.006,-.003))
        buckle=np.array((end[0],min(end[1]-.012,-depth-.009),max(.032,end[2]-.098)))
        yield ribbon('lidstrap_'+label,[end,(end+buckle)*.5+np.array((0,-.008,0)),buckle],.026,.004,'webbing')
        yield box('buckle_m_'+label,buckle,(.043,.013,.035),'rubber')
        yield box('buckle_f_'+label,(s*width*.58,-depth-.011,top-.265),(.046,.015,.037),'rubber')


def shoulder_straps(name, c, height, depth, jiggle):
    factor=c['strap_length']
    # Padded section stays a fixed length. Increasing exposed web takes length from the tail.
    ztop,zbot,padded,web_min,web_max,total,lift0,lift1={
        'rucksack':(.445,.045,.50,.07,.21,.34,.05,.16),
        'rolltop':(.36,.03,.44,.06,.20,.32,.05,.14),
        'daypack':(.37,.03,.42,.06,.19,.30,.04,.13)
    }[name]
    length=web_min+(web_max-web_min)*factor
    ts=np.linspace(0,1,161)[:,None]
    for side,sg in (('L',1),('R',-1)):
        start=np.array((sg*.065,depth+.008,ztop))
        end=np.array((sg*.13,depth+.008,zbot))
        u=np.linspace(0,1,10)
        def curve(beta):
            a=start+[sg*.01,.9*beta,lift0]
            b=end+[sg*.01,beta,lift1]
            pts=(1-ts)**3*start+3*(1-ts)**2*ts*a+3*(1-ts)*ts**2*b+ts**3*end
            return pts,np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
        lo,hi=0.,.8
        for _ in range(28):
            mid=(lo+hi)*.5
            pts,arc=curve(mid)
            if arc[-1]<padded+length: lo=mid
            else: hi=mid
        pts,arc=curve((lo+hi)*.5)
        centers=np.column_stack([np.interp(u*padded,arc,pts[:,i]) for i in range(3)])
        pad_tip=centers[-1]
        yield ribbon('strap_'+side,centers,.062*(.6+.4*np.clip(u/.12,0,1)),.015,'canvas')
        yield box('adjuster_'+side,pad_tip,(.043,.016,.024),'rubber')
        yield ribbon('webbing_'+side,[pad_tip,end],.024,.003,'webbing')
        # Route excess web onto the ground. Keep its arc length while the adjuster travels.
        anchor=pad_tip+np.array((0,.012,0))
        radius=min(.023,max(.001,anchor[2]-.003))
        drop=max(0.,anchor[2]-.003-radius)
        tail=[]
        for distance in np.linspace(0,total-length,21):
            straight=min(distance,drop)
            remaining=max(0.,distance-drop)
            angle=min(math.pi/2,remaining/radius)
            ground_length=max(0.,remaining-radius*math.pi/2)
            dy=radius*(1-math.cos(angle))+ground_length
            dz=-straight-radius*math.sin(angle)
            tail.append(anchor+np.array((.013*jiggle*distance/(total-length),dy,dz)))
        yield ribbon('tail_'+side,tail,.021,.003,'webbing')


def bag(name,c,clip,frame,timing):
    if clip and clip.endswith('_param'):
        c[clip[:-6]]=(frame-1)/24.
    offset=np.zeros(3)
    sway=jiggle=0.
    if clip=='demo':
        state=dict(c)
        curves={key:[] for key in c}
        for n,changes in timing['keys']:
            state.update(changes)
            for key in c:
                curves[key].append((n,state[key]))
        c={key:key_value(frame,keys,True) for key,keys in curves.items()}
        for a,b in timing['bob']:
            if a<=frame<=b:
                u=(frame-a)/(b-a)
                t=(frame-a)/24.
                env=math.sin(math.pi*u)**.7
                sway=math.radians(7)*env*math.sin(math.tau*1.4*t)
                offset=(.04*env*math.sin(math.tau*.9*t),0,
                        .10*env+.025*env*math.sin(math.tau*2.2*t))
                jiggle=env*math.sin(math.tau*2.2*t-.7)
    height,width,depth={'daypack':(.44,.148,.094),'rolltop':(.385,.175,.098),
                        'rucksack':(.50,.177,.127)}[name]
    top=height+.053*(c['fill']-.6)
    d=depth*(.82+.30*c['fill'])
    w=width*(.94+.10*c['fill'])
    profile=[]
    for t in np.linspace(0,1,28):
        taper=1-.15*(1-t)**8-(.06 if name=='rolltop' else .19)*t**6
        wrinkle=.0025*max(0,(.6-c['fill'])/.6)*math.sin(math.tau*t*height/.05)
        profile.append((0,.012 if name=='rolltop' else 0,t*top,taper*w+wrinkle,taper*d+wrinkle))
    body=shell('body',profile,'coated' if name=='rolltop' else 'canvas',3.5)
    models=[body]
    if name=='rolltop':
        models+=list(rolltop(c,top))
    elif name=='rucksack':
        models+=list(rucksack(c,top,w,d))
    else:
        # Body ends at the zipper plane, exposing a dark lining when the panel unzips.
        body['points'][:,1]=np.maximum(body['points'][:,1],-d*.87)
        models.append(ball('liner',(0,-d*.83,top*.48),(w*.84,.007,top*.40),'lining'))
        models+=list(daypack(c,top,w,d))
    models+=list(shoulder_straps(name,c,top,d,jiggle))
    for model in models:
        yield moved(model,ry(sway)@rx(sway*.6),(0,0,0),offset)
