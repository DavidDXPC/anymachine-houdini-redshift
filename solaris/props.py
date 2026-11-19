"""Parametric workshop props. Y is up, +Z is the front, distances are metres."""
from math import cos, pi, sin
import numpy as np
from pxr import UsdGeom, UsdShade, Vt


class Builder:
    def __init__(self,stage,path,materials,low):
        self.stage,self.path,self.materials,self.low=stage,path,materials,low
        self.steps=8 if low else 24
        self.index=0

    def mesh(self,name,points,faces,finish):
        self.index+=1
        mesh=UsdGeom.Mesh.Define(self.stage,f"{self.path}/{name}_{self.index:03}")
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(points,dtype=np.float32)))
        mesh.CreateFaceVertexCountsAttr([len(f) for f in faces])
        mesh.CreateFaceVertexIndicesAttr([i for f in faces for i in f])
        mesh.CreateSubdivisionSchemeAttr("none")
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(self.materials[finish])
        return mesh

    def rings(self,name,rings,finish,closed_start=True,closed_end=True):
        n=len(rings[0]); faces=[]
        for layer in range(len(rings)-1):
            for i in range(n):
                a=layer*n+i;b=layer*n+(i+1)%n
                faces.append((a,b,b+n,a+n))
        if closed_start:faces.append(list(reversed(range(n))))
        if closed_end:faces.append(list(range((len(rings)-1)*n,len(rings)*n)))
        return self.mesh(name,[xyz for ring in rings for xyz in ring],faces,finish)

    def box(self,name,center,size,finish,bevel=0):
        x,y,z=center;w,h,d=np.asarray(size)*.5
        b=min(bevel,w*.45,d*.45,h*.45)
        heights=((y-h,w,d),(y+h,w,d))
        if b:
            heights=((y-h,w-b,d-b),(y-h+b,w,d),(y+h-b,w,d),(y+h,w-b,d-b))
        rings=[]
        for yy,xx,zz in heights:
            cuts=min(b,xx*.45,zz*.45)
            if cuts:
                ring=[(-xx+cuts,zz),(xx-cuts,zz),(xx,zz-cuts),(xx,-zz+cuts),
                      (xx-cuts,-zz),(-xx+cuts,-zz),(-xx,-zz+cuts),(-xx,zz-cuts)]
            else:
                ring=[(-xx,zz),(xx,zz),(xx,-zz),(-xx,-zz)]
            rings.append([(x+i,yy,z+j) for i,j in ring])
        return self.rings(name,rings,finish)

    def lathe(self,name,center,profile,finish,cap=True):
        x,y,z=center
        rings=[[(x+r*cos(2*pi*i/self.steps),y+height,z-r*sin(2*pi*i/self.steps)) for i in range(self.steps)]
               for r,height in profile]
        return self.rings(name,rings,finish,cap,cap)

    def tube(self,name,a,b,r,finish):
        a,b=np.asarray(a,float),np.asarray(b,float)
        axis=b-a; axis/=np.linalg.norm(axis)
        u=np.cross(axis,np.eye(3)[np.argmin(abs(axis))]);u/=np.linalg.norm(u)
        v=np.cross(axis,u)
        circle=[r*(u*cos(2*pi*i/self.steps)+v*sin(2*pi*i/self.steps)) for i in range(self.steps)]
        return self.rings(name,[[p+q for q in circle] for p in (a,b)],finish)


def workbench(b):
    b.box("worktop",(0,.875,0),(1.6,.05,.70),"wood",.009)
    b.box("bottom_shelf",(0,.185,0),(1.46,.03,.58),"enamel",.004)
    for x in (-.73,.73):
        for z in (-.27,.27):
            b.box("angle_leg",(x,.425,z),(.055,.85,.055),"metal")
            if not b.low:b.box("foot",(x,.015,z),(.075,.03,.075),"rubber",.003)
        b.box("apron_side",(x,.81,0),(.035,.08,.55),"enamel")
    for z in (-.275,.275): b.box("apron",(0,.81,z),(1.47,.08,.035),"enamel")
    if not b.low:
        for x in (-.68,.68):
            for z in (-.245,.245):b.lathe("bolt",(x,.899,z),[(.007,0),(.007,.002)],"metal")


def stool(b):
    b.lathe("seat",(0,.68,0),[(.165,0),(.178,.013),(.174,.04)],"wood")
    for i in range(4):
        a=pi*.25+i*pi*.5; leg=(.195*cos(a),.014,.195*sin(a)); top=(.12*cos(a),.68,.12*sin(a))
        b.tube("leg",leg,top,.013,"metal")
        if not b.low:b.lathe("foot",(leg[0],0,leg[2]),[(.018,0),(.018,.022)],"rubber")
        c=a+pi/2
        b.tube("brace",(.17*cos(a),.24,.17*sin(a)),(.17*cos(c),.24,.17*sin(c)),.009,"enamel")


def cabinet(b):
    b.box("case",(0,.45,0),(.65,.88,.48),"enamel",.014)
    b.box("plinth",(0,.025,0),(.59,.05,.44),"dark")
    for i in range(4):
        y=.15+i*.198
        b.box("drawer",(0,y,.245),(.594,.183,.028),"enamel",.004)
        b.box("pull",(0,y+.052,.275),(.15,.014,.040),"metal",.003)
        if not b.low:b.box("label",(-.195,y+.046,.260),(.074,.036,.002),"ceramic")
    b.box("top",(0,.904,0),(.66,.029,.49),"rubber",.004)


def crate(b):
    for x in (-.29,.29):
        for z in (-.19,.19):b.box("post",(x,.20,z),(.035,.4,.035),"metal")
    for i in range(3):
        y=.072+.129*i
        for z in (-.192,.192): b.box("plank",(0,y,z),(.60,.119,.02),"wood")
        for x in (-.292,.292): b.box("end",(x,y,0),(.02,.119,.36),"wood")
    b.box("bottom",(0,.024,0),(.60,.048,.4),"wood")


def shelf(b):
    for x in (-.46,.46):
        for z in (-.20,.20):b.box("upright",(x,.81,z),(.032,1.62,.032),"metal")
    for y in (.09,.60,1.10,1.60):
        b.box("shelf",(0,y,0),(.95,.032,.43),"enamel",.002)
    if not b.low:
        b.tube("crossbrace",(-.46,.10,-.20),(.46,1.59,-.20),.007,"metal")
        b.tube("crossbrace",(.46,.10,-.20),(-.46,1.59,-.20),.007,"metal")


def toolbox(b):
    b.box("body",(0,.089,0),(.43,.178,.21),"enamel",.012)
    b.box("lid",(0,.188,0),(.433,.036,.214),"accent",.009)
    for x in (-.067,.067):
        b.tube("handle_stem",(x,.205,0),(x,.251,0),.01,"dark")
    b.tube("grip",(-.067,.251,0),(.067,.251,0),.012,"rubber")
    if not b.low:
        for x in (-.125,.125):b.box("latch",(x,.171,.109),(.021,.052,.008),"metal",.002)


def desk_lamp(b):
    b.lathe("base",(0,0,0),[(.095,0),(.10,.008),(.093,.021),(.032,.034)],"enamel")
    joints=[(0,.034,0),(-.057,.238,-.038),(.052,.37,.022)]
    for a,c in zip(joints,joints[1:]):
        b.tube("arm",a,c,.009,"metal")
        if not b.low:
            b.tube("arm_link",np.array(a)+(.011,0,0),np.array(c)+(.011,0,0),.004,"metal")
    x,y,z=joints[-1]
    b.lathe("shade",(x,y-.073,z),[(.078,0),(.076,.006),(.035,.058),(.018,.069)],"enamel",False)
    b.lathe("diffuser",(x,y-.072,z),[(.07,0),(.07,.002)],"ceramic")


def mug(b):
    b.lathe("cup",(0,0,0),[(.036,0),(.037,.003),(.041,.091),(.039,.094),
                              (.036,.091),(.033,.007)],"ceramic")
    pts=[(.034,.078,0),(.051,.077,0),(.06,.064,0),(.061,.047,0),(.052,.031,0),(.035,.028,0)]
    for a,c in zip(pts,pts[1:]):b.tube("handle",a,c,.006,"ceramic")


def bottle(b):
    b.lathe("body",(0,0,0),[(.034,0),(.038,.006),(.038,.139),(.034,.15),(.016,.17),(.016,.20)],"glass")
    b.lathe("cap",(0,.197,0),[(.017,0),(.019,.002),(.019,.018),(.017,.020)],"enamel")
    if not b.low:b.lathe("label",(0,.044,0),[(.0382,0),(.0382,.065)],"ceramic",False)


def monitor(b):
    b.box("foot",(0,.012,0),(.34,.024,.19),"dark",.007)
    b.box("stem",(0,.112,-.035),(.054,.22,.04),"metal",.003)
    b.box("bezel",(0,.322,-.014),(.53,.318,.046),"dark",.009)
    b.box("screen",(0,.324,.011),(.494,.277,.003),"screen",.001)
    if not b.low:b.box("power_led",(.225,.180,.010),(.004,.003,.002),"accent")


RECIPES={f.__name__:f for f in (workbench,stool,cabinet,crate,shelf,toolbox,desk_lamp,mug,bottle,monitor)}

