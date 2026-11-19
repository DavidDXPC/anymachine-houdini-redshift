"""Assemble the four native modules into one portable, layered Solaris production."""
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

from pxr import Gf, Sdf, Usd, UsdGeom, UsdUtils

from . import materials, scene, stilt_asset

REPO = Path(__file__).resolve().parents[1]


def _new(path, fps):
    stage = Usd.Stage.CreateNew(str(path))
    scene.init(stage)
    stage.SetFramesPerSecond(fps)
    stage.SetTimeCodesPerSecond(fps)
    return stage


def _name(value):
    if not isinstance(value, str) or not value or not Sdf.Path.IsValidIdentifier(value):
        raise ValueError(f"Invalid USD identifier: {value!r}")
    return value


def _save_module(folder, name, author, spec, base, fps):
    """Package external file dependencies alongside the scene, independent of the checkout."""
    path = folder / (name + ".usdc")
    stage = _new(path, fps)
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/World").GetPrim())
    report = author(stage, spec, base)
    stage.GetRootLayer().Save()
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(path))
    if unresolved:
        raise ValueError(f"{name}: missing dependencies {unresolved}")
    if len(layers) > 1 or assets:
        package = path.with_suffix(".usdz")
        if not UsdUtils.CreateNewUsdzPackage(str(path), str(package)):
            raise RuntimeError(f"Could not package {name}")
        return package.name, report
    return path.name, report


def _machine_assets(folder, machines, fps, base):
    path = folder / "machines.usdc"
    stage = _new(path, fps)
    group = UsdGeom.Xform.Define(stage, "/World/Machines")
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    glb = REPO / "assets/stilt.glb"
    catalog = scene.catalog(glb)
    seen = set()
    for entry in machines:
        asset = entry["asset"]
        name = _name(entry.get("id", asset))
        if name in seen:
            raise ValueError(f"Duplicate machine ID {name}")
        seen.add(name)
        info = catalog[asset]
        clip = entry.get("clip")
        count, rate = info["clips"][clip] if clip else (1, fps)
        controls = dict(info["controls"])
        for key, value in entry.get("controls", {}).items():
            if key not in controls or not 0 <= float(value) <= 1:
                raise ValueError(f"{name}: invalid control {key}={value}")
            controls[key] = float(value)
        asset_folder = folder / "machines" / name
        asset_folder.mkdir(parents=True)
        meshfile = asset_folder / "geometry.usdc"
        machine = _new(meshfile, rate)
        if asset == "stilt":
            stilt_asset.prepare(glb, asset_folder / "textures")
            stilt_asset.author(machine, glb, "textures", clip, materials.material)
        elif asset in scene.EXTERNAL:
            source = (base / entry["source"]).resolve(strict=True)
            packaged = asset_folder / "source.usdz"
            if not UsdUtils.CreateNewUsdzPackage(str(source), str(packaged)):
                raise ValueError(f"Could not package {source}")
            scene.external(machine, packaged)
            machine.GetPrimAtPath("/Machine/Source").GetReferences().SetReferences([Sdf.Reference("source.usdz")])
        else:
            texture = None
            if asset == "laptop":
                texture = "screen_ui.png"
                shutil.copyfile(REPO / "houdini/rigs/screen_ui.png", asset_folder / texture)
            samples = ((i, Usd.TimeCode(i)) for i in range(1, count+1)) if clip else [(1, Usd.TimeCode.Default())]
            scene.geometry(machine, asset, controls, clip, samples, screen_texture=texture)
        machine.SetDefaultPrim(machine.GetPrimAtPath("/Machine"))
        machine.GetRootLayer().Save()
        placement = UsdGeom.Xform.Define(stage, group.GetPath().AppendChild(name))
        placement.AddTranslateOp().Set(Gf.Vec3d(*entry.get("position", (0, 0, 0))))
        placement.AddRotateYOp().Set(float(entry.get("yaw", 0)))
        # Put the reference below the placement so a source's own transforms survive.
        model = stage.OverridePrim(placement.GetPath().AppendChild("Model"))
        model.GetReferences().AddReference(meshfile.relative_to(folder).as_posix(),
            layerOffset=Sdf.LayerOffset(1 - fps / rate))
    stage.GetRootLayer().Save()
    return path.name


def compile_stage(spec, base, output):
    from family.anykit import solaris as kit
    from family.anyscene import solaris as sets
    from family.anyshot import solaris as shots

    fps = float(spec["direction"].get("fps", 24))
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("fps must be positive")
    size = spec.get("resolution", [960, 540])
    if len(size) != 2 or any(type(n) is not int or n < 1 for n in size):
        raise ValueError("resolution requires two positive integers")
    folder = output / "layers"
    folder.mkdir()
    set_layer, set_report = _save_module(folder, "set", sets.author, spec["scene"], base, fps)
    kit_layer, kit_report = _save_module(folder, "kit", kit.author, spec["kit"], base, fps)
    layers = [set_layer, kit_layer, _machine_assets(folder, spec.get("machines", []), fps, base)]
    # Direct against the composed geometry. Save only the authored camera opinions here.
    cameras = _new(folder / "shots.usda", fps)
    cameras.GetRootLayer().subLayerPaths = list(reversed(layers))
    timing = shots.author(cameras, spec["direction"], base)
    camera_path = str(timing["camera"])
    count = int(timing["frames"])
    if count < 1 or not cameras.GetPrimAtPath(camera_path).IsA(UsdGeom.Camera):
        raise ValueError("AnyShot did not produce a cut camera")
    cameras.GetRootLayer().subLayerPaths = []
    cameras.GetRootLayer().Save()
    layers.append("shots.usda")
    render = _new(folder / "render.usda", fps)
    scene.render_settings(render, camera_path, size, "./renders/beauty.exr")
    render.GetRootLayer().Save()
    layers.append("render.usda")
    production = _new(output / "production.usda", fps)
    production.GetRootLayer().subLayerPaths = ["layers/" + name for name in reversed(layers)]
    production.SetDefaultPrim(production.GetPrimAtPath("/World"))
    production.SetStartTimeCode(1)
    production.SetEndTimeCode(count)
    production.SetMetadata("renderSettingsPrimPath", "/Render/Settings")
    production.GetRootLayer().Save()
    report = dict(scene=set_report, kit=kit_report, machines=spec.get("machines", []), direction=timing)
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return layers, fps, count


def build_hip(folder, layers, fps, count):
    import hou
    if hou.isUIAvailable() or hou.applicationVersion()[0] != 22:
        raise RuntimeError("Use Houdini 22 hython to build the HIP")
    ext = {hou.licenseCategoryType.Indie: "hiplc", hou.licenseCategoryType.Apprentice: "hipnc"}.get( hou.licenseCategory(), "hip")
    hip = folder / ("production." + ext)
    hou.hipFile.setName(str(hip))
    net = hou.node("/stage")
    upstream = None
    for name, layer in zip(("ANYSCENE", "ANYKIT", "ANYMACHINE", "ANYSHOT", "BEAUTY"), layers):
        node = net.createNode("sublayer", name)
        node.parm("filepath1").set("$HIP/layers/" + layer)
        if upstream:
            node.setInput(0, upstream)
        upstream = node
    out = net.createNode("null", "OUT")
    out.setInput(0, upstream)
    out.setDisplayFlag(True)
    target = net.createNode("usdrender_rop", "REDSHIFT")
    target.setInput(0, out)
    if scene.RENDERER not in target.parm("renderer").menuItems():
        raise RuntimeError("Redshift Solaris delegate is unavailable for this build")
    target.parm("renderer").set(scene.RENDERER)
    target.parm("rendersettings").set("/Render/Settings")
    target.parm("outputimage").set("$HIP/renders/beauty.$F4.exr")
    target.parm("trange").set(1)
    target.parmTuple("f").set((1, count, 1))
    target.parm("mkpath").set(1)
    hou.setFps(fps)
    hou.playbar.setFrameRange(1,count)
    hou.playbar.setPlaybackRange(1,count)
    hou.setFrame(1)
    net.layoutChildren()
    if not out.stage() or not out.stage().GetPrimAtPath("/Render/Settings"):
        raise RuntimeError("Failed to compose the Solaris network")
    hou.hipFile.save(str(hip))
    return target


def run(args):
    specfile = args.manifest.resolve(strict=True)
    spec = json.loads(specfile.read_text(encoding="utf-8-sig"))
    dest = args.output.resolve()
    if dest.exists():
        raise FileExistsError(f"Choose a new output folder: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent, prefix=".family-") as scratch:
        folder = Path(scratch) / "delivery"
        folder.mkdir()
        layers, fps, count = compile_stage(spec, specfile.parent, folder)
        if args.hip or args.render:
            rop = build_hip(folder, layers, fps, count)
            if args.render:
                if not 1 <= args.frame <= count:
                    raise ValueError(f"Frame must be between 1 and {count}")
                first, last = (args.frame, args.frame) if args.render == "still" else (1,count)
                rop.render(frame_range=(first,last), verbose=True)
                for frame in range(first, last+1):
                    image = folder / "renders" / f"beauty.{frame:04}.exr"
                    if not image.is_file() or image.stat().st_size == 0:
                        raise RuntimeError(f"Missing render {image.name}")
                if args.render == "video":
                    encode_video(folder, fps, count, args.display, args.view)
        if dest.exists():
            raise FileExistsError(dest)
        folder.rename(dest)
    print(f"{dest / 'production.usda'} | {count} frames at {fps:g} fps")


def encode_video(folder, fps, count, display, view):
    """Apply the production OCIO display transform before encoding the review."""
    import subprocess
    import hou
    config = hou.getenv("OCIO")
    if not config or not Path(config).is_file():
        raise ValueError("Video review requires the show's OCIO config")
    converter = Path(hou.getenv("HFS")) / "bin" / ("hoiiotool.exe" if os.name == "nt" else "hoiiotool")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for video review")
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        for frame in range(1,count+1):
            subprocess.run([str(converter), "--colorconfig", config, str(folder/"renders"/f"beauty.{frame:04}.exr"),
                            "--iscolorspace", "ACEScg", "--ociodisplay", display, view, "--ch", "R,G,B",
                            "-d", "uint8", "-o",str(Path(tmp)/f"{frame:04}.png")],check=True)
        subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-framerate",str(fps),"-start_number","1",
                        "-i",str(Path(tmp)/"%04d.png"),"-vf","pad=ceil(iw/2)*2:ceil(ih/2)*2",
                        "-pix_fmt","yuv420p","-c:v","libx264",str(folder/"review.mp4")],check=True)
