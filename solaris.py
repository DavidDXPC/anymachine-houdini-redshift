"""AnyShot for Houdini Solaris and Redshift. Standalone: python solaris.py --help."""
import argparse
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import zlib

import numpy as np
from pxr import Gf, Tf, Usd, UsdGeom, UsdRender

if __package__:
    from .solaris_clearance import Clearance
else:
    from solaris_clearance import Clearance


MOVES = {"static", "dolly", "push_in", "truck", "crane", "pedestal", "pan", "tilt",
         "orbit", "dolly_zoom", "walkthrough", "path", "walk", "reveal", "zoom"}
SENSORS = {"s35": 24.89, "ff": 36.0}
ASPECTS = {"2.39": 2.39, "2.35": 2.35, "1.85": 1.85, "16:9": 16/9, "1.78": 16/9, "4:3": 4/3}


def _ease(t, mode):
    t = min(1., max(0., t))
    if mode == "linear":
        return t
    if mode == "in":
        return 1 - math.cos(t*math.pi/2)
    if mode == "out":
        return math.sin(t*math.pi/2)
    if mode == "inout":
        return .5 - .5*math.cos(t*math.pi)
    raise ValueError(f"Unknown ease {mode!r}")


def _keys(items):
    pairs = sorted(items, key=lambda item: item[0])
    ts = np.array([float(t) for t, value in pairs])
    if not np.isfinite(ts).all() or np.any((ts < 0) | (ts > 1)) or np.any(np.diff(ts) <= 0):
        raise ValueError("Key times must be unique and lie in [0,1]")
    return ts, [value for t, value in pairs]


def _interpolate(keys, t, ease="linear", curve=False):
    ts, values = keys
    if t <= ts[0] or len(ts) == 1:
        return values[0]
    if t >= ts[-1]:
        return values[-1]
    i = int(ts.searchsorted(t, side="right") - 1)
    u = _ease((t-ts[i]) / (ts[i+1]-ts[i]), ease)
    p, q = values[i:i+2]
    if not curve or len(values) == 2:
        return p*(1-u) + q*u
    a = values[i-1] if i else 2*p-q
    b = values[i+2] if i+2 < len(values) else 2*q-p
    return .5*(2*p + (-a+q)*u + (2*a-5*p+4*q-b)*u*u + (-a+3*p-3*q+b)*u*u*u)


class Locations:
    """Resolve metre-based numeric inputs and track bounds on the current USD frame."""
    def __init__(self, stage, input_axes):
        self.stage = stage
        self.meters = UsdGeom.GetStageMetersPerUnit(stage)
        self.axis = str(UsdGeom.GetStageUpAxis(stage)).upper()
        self.input_axes = input_axes.upper()
        if self.input_axes not in ("Y", "Z") or self.axis not in ("Y", "Z"):
            raise ValueError("World up axis must be Y or Z")
        self.names = {}
        for prim in stage.Traverse(Usd.TraverseInstanceProxies()):
            self.names.setdefault(prim.GetName(), []).append(prim)

    def frame(self, n):
        self.time = Usd.TimeCode(n)
        self.cache = UsdGeom.BBoxCache(self.time, ["default","render"], useExtentsHint=False)
        self.xforms = UsdGeom.XformCache(self.time)
        self.resolved = {}

    def vector(self, xyz):
        v = np.asarray(xyz, dtype=float)
        if v.shape != (3,) or not np.isfinite(v).all():
            raise ValueError(f"Invalid coordinate {xyz!r}")
        if self.input_axes != self.axis:
            x,y,z = v
            v = np.array((x,z,-y) if self.axis == "Y" else (x,-z,y))
        return v / self.meters

    def point(self, value, offset=None):
        if isinstance(value, dict):
            return self.point(value.get("prim", value.get("obj", value.get("pos"))), value.get("offset", offset))
        if isinstance(value, str):
            if value not in self.resolved:
                options = self.names.get(value, ())
                if value.startswith("/"):
                    prim = self.stage.GetPrimAtPath(value)
                    if not prim:
                        raise ValueError(f"Missing target prim {value!r}")
                elif len(options) == 1:
                    prim = options[0]
                else:
                    raise ValueError(f"Target {value!r} matches {len(options)} prims; provide its USD path")
                box = self.cache.ComputeWorldBound(prim).ComputeAlignedRange()
                center = self.xforms.GetLocalToWorldTransform(prim).ExtractTranslation() if box.IsEmpty() else box.GetMidpoint()
                self.resolved[value] = np.array(center)
            point = self.resolved[value]
        else:
            point = self.vector(value)
        return point + self.vector(offset) if offset is not None else point


def _position_keys(keys, field, loc, default):
    positions = []
    for k in keys:
        value = k.get(field+"_obj", k.get(field))
        positions.append(loc.point(value, k.get(field+"_offset")) if value is not None else None)
    first = next((p for p in positions if p is not None), None)
    if first is None:
        if default is None:
            raise ValueError(f"The shot requires a {field} or {field}_obj")
        first = loc.point(default)
    filled = []
    for k, p in zip(keys, positions):
        first = p if p is not None else first
        filled.append((k.get("t", 0), first))
    return _keys(filled)


def _scalar(keys, field, t, mode, default):
    curve = [(k.get("t", 0), float(k[field])) for k in keys if field in k]
    return _interpolate(_keys(curve), t, mode) if curve else default


def _shot_keys(shot):
    if shot.get("keys"):
        return sorted(shot["keys"], key=lambda k:k.get("t", 0))
    start = {"t": 0, "pos": shot.get("eye"), "aim": shot.get("target")}
    if shot.get("end_eye") is None and shot.get("end_target") is None and "end_lens" not in shot:
        return [start]
    end = dict(t=1, pos=shot.get("end_eye",start["pos"]), aim=shot.get("end_target",start["aim"]))
    if "end_lens" in shot:
        start["lens"] = shot.get("lens",35)
        end["lens"] = shot["end_lens"]
    return [start,end]


def _evaluate(shot, loc, frame, elapsed, count, fps, start_distance):
    t = elapsed / max(1, count-1)
    loc.frame(frame)
    mode = shot.get("ease","inout")
    u = _ease(t,mode)
    keys = _shot_keys(shot)
    move = shot.get("move","static")
    if move == "orbit":
        o = shot["orbit"]
        center = loc.point(o.get("center_obj",o.get("center", shot.get("target"))), o.get("center_offset"))
        angle = math.radians(o.get("start_deg",0)+(o.get("end_deg",90)-o.get("start_deg",0))*u)
        r = float(o["radius"])
        if r <= 0:
            raise ValueError("Orbit radius must be positive")
        dx = (r*math.cos(angle),0,-r*math.sin(angle)) if loc.input_axes == "Y" else (r*math.cos(angle),r*math.sin(angle),0)
        eye = center + loc.vector(dx)
        if "height" in o:
            eye[1 if loc.axis == "Y" else 2] = o["height"] / loc.meters
        target = loc.point(o.get("aim_obj",o.get("aim")),o.get("aim_offset")) if "aim" in o or "aim_obj" in o else center
    else:
        eyes = _position_keys(keys, "pos", loc, shot.get("eye"))
        aims = _position_keys(keys, "aim", loc, shot.get("target"))
        eye = _interpolate(eyes, u, curve=True)
        target = _interpolate(aims, u, curve=True)
    lens = _scalar(keys,"lens",t,mode,shot.get("lens",35))
    if move == "dolly_zoom":
        subject = loc.point(shot["subject"]) if "subject" in shot else target
        distance = float(np.linalg.norm(subject-eye))
        if distance < 1e-8:
            raise ValueError("Dolly zoom starts or ends on the subject")
        if start_distance is None:
            start_distance = distance
        lens = _scalar(keys,"lens",0,mode,shot.get("lens",35))*distance/start_distance
    roll = _scalar(keys,"roll",t,mode,shot.get("roll",0))
    fstop = (_interpolate(_keys([(k["t"],k["v"]) for k in shot["fstop_keys"]]),t,mode)
             if shot.get("fstop_keys") else shot.get("fstop",2.8))
    f = shot.get("focus",{"mode":"track_aim"})
    f = dict(mode="point",pos=f) if not isinstance(f,dict) else f
    fm = f.get("mode", "point")
    if fm == "rack":
        curve = _keys([(k["t"],loc.point(k.get("obj",k.get("pos")),k.get("offset"))) for k in f["keys"]])
        focus = _interpolate(curve,t,f.get("ease","inout"))
    elif fm in ("point","track"):
        focus = loc.point(f.get("obj",f.get("pos")),f.get("offset"))
    elif fm in ("none","track_aim"):
        focus = target
    else:
        raise ValueError(f"Unknown focus mode {fm!r}")
    up = np.array((0,1,0) if loc.axis == "Y" else (0,0,1),dtype=float)
    forward = target-eye
    if np.linalg.norm(forward) < 1e-7:
        raise ValueError(f"Camera and target coincide at frame {frame}")
    forward /= np.linalg.norm(forward)
    if abs(forward @ up) > .999:
        up = np.array((0,0,-1) if loc.axis == "Y" else (0,1,0),dtype=float)
    right = np.cross(forward,up)
    right /= np.linalg.norm(right)
    up = np.cross(right,forward)
    handheld = shot.get("handheld",0)
    if handheld:
        settings = handheld if isinstance(handheld,dict) else {}
        profile = settings.get("profile",handheld if isinstance(handheld,str) else "subtle")
        strength = float(settings.get("strength", handheld if isinstance(handheld,(int,float)) else 1.))
        if profile not in ("none","walk","subtle"):
            raise ValueError(f"Unknown handheld profile {profile!r}")
        if profile != "none":
            phase = (zlib.crc32(shot["name"].encode()) % 360)*math.pi/180
            omega = (1.65 if profile == "walk" else .49)*2*math.pi*elapsed/fps
            amplitude = (.021 if profile == "walk" else .003)*strength/loc.meters
            eye = eye + amplitude*(.5*right*math.sin(omega/2+phase)+up*math.sin(omega+phase))
            roll += (.42 if profile == "walk" else .10)*strength*math.sin(omega/2+phase)
    angle = math.radians(roll)
    up = up*math.cos(angle) - right*math.sin(angle)
    orientation = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*eye+forward),Gf.Vec3d(*up)).GetInverse().ExtractRotationQuat()
    distance = float((focus-eye) @ forward)
    if fm != "none" and distance <= 0:
        raise ValueError(f"Focus target behind the camera at frame {frame}")
    if not math.isfinite(lens) or lens <= 0 or not math.isfinite(fstop) or fstop <= 0:
        raise ValueError("Lens and f-stop must be finite and positive")
    sensor = shot.get("sensor","s35")
    aperture = SENSORS[sensor] if isinstance(sensor,str) else float(sensor)
    res = shot.get("res", [1920,1080])
    aspect = shot.get("aspect",res[0]/res[1])
    aspect = ASPECTS[str(aspect)] if str(aspect) in ASPECTS else float(aspect)
    if aperture <= 0 or aspect <= 0:
        raise ValueError("Invalid camera aperture or aspect")
    to_camera_units = .01/loc.meters
    return dict(eye=Gf.Vec3d(*eye), rotation=orientation, lens=lens*to_camera_units,
                focus=max(distance,.001/loc.meters), fstop=0. if fm=="none" else float(fstop),
                ha=aperture*to_camera_units, va=aperture/aspect*to_camera_units), start_distance


class CameraWriter:
    def __init__(self,stage,path):
        self.camera = UsdGeom.Camera.Define(stage,path)
        self.camera.ClearXformOpOrder()
        xform = UsdGeom.Xformable(self.camera)
        self.position = xform.AddTranslateOp().GetAttr()
        self.rotation = xform.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).GetAttr()
        self.camera.SetResetXformStack(True)
        self.attrs = dict(lens=self.camera.CreateFocalLengthAttr(),focus=self.camera.CreateFocusDistanceAttr(),
                          fstop=self.camera.CreateFStopAttr(),ha=self.camera.CreateHorizontalApertureAttr(),
                          va=self.camera.CreateVerticalApertureAttr())
        for attr in (self.position,self.rotation,*self.attrs.values()):
            attr.Clear()

    def sample(self, time, values):
        self.position.Set(values["eye"],time)
        self.rotation.Set(values["rotation"],time)
        for key, attr in self.attrs.items():
            attr.Set(float(values[key]),time)


def author(stage, spec, base_dir):
    """Append cameras to a stage, and return the cut camera and measured shot timings."""
    if isinstance(spec, (str,Path)):
        spec = json.loads((Path(base_dir)/spec).read_text(encoding="utf-8-sig"))
    defaults = spec.get("defaults", {})
    fps = float(spec.get("fps", defaults.get("fps",24)))
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("fps must be positive")
    plans = spec["shots"]
    if not plans:
        raise ValueError("The manifest needs a shot")
    loc = Locations(stage,spec.get("input_axes",str(UsdGeom.GetStageUpAxis(stage))))
    options = spec.get("clearance",{})
    if options.get("on_hit","error") not in ("error","report"):
        raise ValueError("clearance.on_hit must be error or report")
    clearance = Clearance(stage,options.get("include"),options.get("exclude",()))
    radius = float(options.get("meters",.45)) / loc.meters
    if radius < 0 or not math.isfinite(radius):
        raise ValueError("Clearance must be finite and nonnegative")
    checked, used, reports, hits = [], {"Cut"}, [], []
    start = 1
    for item in plans:
        shot = dict(defaults, **item)
        name = Tf.MakeValidIdentifier(shot["name"])
        if name in used:
            raise ValueError(f"Repeated or reserved camera name {name!r}")
        used.add(name)
        duration = shot.get("frames",round(fps*shot.get("seconds",1)))
        count = int(duration)
        if count != duration or ("fps" in item and item["fps"] != fps):
            raise ValueError("Use whole frames and a single frame rate for the cut")
        if count < 1 or shot.get("move","static") not in MOVES:
            raise ValueError(f"Invalid duration or move in {name}")
        motion, start_distance = [], None
        for i in range(count):
            pose,start_distance = _evaluate(shot,loc,start+i,i,count,fps,start_distance)
            motion.append(pose)
            if radius > 0:
                hits.extend(clearance.hits(pose["eye"],start+i,radius,loc.meters))
        checked.append((name,start,motion))
        reports.append(dict(name=shot["name"],camera="/World/Shots/"+name,first=start,last=start+count-1))
        start += count
    if hits and options.get("on_hit","error") == "error":
        first = min(hits,key=lambda h:h["distance_m"])
        raise ValueError(f"Camera clearance {first['distance_m']:.4f} m at frame {first['frame']} against {first['prim']}")
    UsdGeom.Scope.Define(stage,"/World/Shots")
    cut = CameraWriter(stage,"/World/Shots/Cut")
    prev = None
    for name, first, motion in checked:
        camera = CameraWriter(stage,"/World/Shots/"+name)
        if prev is not None:
            cut.sample(first-.00001,prev)
        for i,pose in enumerate(motion):
            camera.sample(first+i,pose)
            cut.sample(first+i,pose)
        prev = motion[-1]
    stage.SetStartTimeCode(1)
    stage.SetEndTimeCode(start-1)
    stage.SetTimeCodesPerSecond(fps)
    stage.SetFramesPerSecond(fps)
    return dict(camera="/World/Shots/Cut",frames=start-1,fps=fps,shots=reports,clearance_hits=hits)


def main(argv=None):
    p = argparse.ArgumentParser(description="Author an editable Solaris cut camera from a shot manifest")
    p.add_argument("manifest",type=Path)
    p.add_argument("output",type=Path)
    p.add_argument("--scene",type=Path,help="Existing local USD stage. Output layers it read-only.")
    p.add_argument("--settings",help="USD RenderSettings prim to bind to the cut camera")
    args = p.parse_args(argv)
    if args.scene and args.output.resolve() == args.scene.resolve():
        p.error("Choose a separate output for the camera layer")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(dir=args.output.parent,suffix=args.output.suffix,delete=False) as tmp:
        candidate = Path(tmp.name)
    try:
        stage = Usd.Stage.CreateNew(str(candidate))
        if args.scene:
            source = Usd.Stage.Open(str(args.scene))
            stage.GetRootLayer().subLayerPaths.append(os.path.relpath(args.scene.resolve(),args.output.parent.resolve()).replace(os.sep,"/"))
            UsdGeom.SetStageMetersPerUnit(stage,UsdGeom.GetStageMetersPerUnit(source))
            UsdGeom.SetStageUpAxis(stage,UsdGeom.GetStageUpAxis(source))
            if source.GetDefaultPrim():
                stage.SetDefaultPrim(stage.GetPrimAtPath(source.GetDefaultPrim().GetPath()))
        else:
            UsdGeom.SetStageMetersPerUnit(stage,1.)
            UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.y)
        result = author(stage,args.manifest.resolve(),args.manifest.parent)
        if args.settings:
            settings = UsdRender.Settings.Get(stage,args.settings)
            if not settings:
                p.error("Missing USD RenderSettings prim")
            settings.CreateCameraRel().SetTargets([result["camera"]])
        stage.GetRootLayer().Save()
        del stage
        os.replace(candidate,args.output)
        print(json.dumps(result,indent=2))
    finally:
        candidate.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
