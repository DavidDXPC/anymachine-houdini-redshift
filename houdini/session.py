"""Construct a portable Houdini scene in a separate hython process."""
import hashlib
from pathlib import Path
import shutil

from pxr import Gf, Sdf, Usd, UsdUtils

from . import materials, scene, stilt_asset


def _install_loader(node, folder, call):
    # Namespace each on-disk runtime independently when the artist switches HIPs.
    script = f"""import hashlib, importlib.util, pathlib, sys
import hou
node = hou.pwd()
data = pathlib.Path(hou.expandString("$HIP")) / {folder!r}
package = data / "runtime"
module_name = "anymachine_" + hashlib.sha1(str(package).encode()).hexdigest()
if module_name not in sys.modules:
    spec = importlib.util.spec_from_file_location(module_name, package / "__init__.py",
        submodule_search_locations=[str(package)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
from importlib import import_module
runtime = import_module(module_name + ".session")
{call}
"""
    node.parm("python").set(script)


def live_machine(node, data, asset, keys):
    import hou
    clip = node.parm("clip").evalAsString() or None
    controls = {key: node.evalParm("control_" + key) for key in keys}
    if asset == "stilt":
        stage = node.editableStage()
        stilt_asset.author(stage, data / "stilt.glb", data / "textures", clip, materials.material)
        return
    current = hou.frame() if clip or any(node.parm("control_"+k).isTimeDependent() for k in keys) else None
    time = Usd.TimeCode(current) if current is not None else Usd.TimeCode.Default()
    stage = node.editableStage()
    scene.geometry(stage, asset, controls, clip, [(current or 1, time)],
                   screen_texture=(data / "runtime/rigs/screen_ui.png").as_posix())


def live_studio(node, bounds):
    view = node.parm("angle").evalAsString()
    size = [node.evalParm("width"), node.evalParm("height")]
    box = Gf.Range3d(Gf.Vec3d(*bounds[0]), Gf.Vec3d(*bounds[1]))
    scene.studio(node.editableStage(), box, view, size, "./beauty.exr", set_metadata=False)


def _spares(node, items):
    group = node.parmTemplateGroup()
    for parm in items:
        group.append(parm)
    node.setParmTemplateGroup(group)


def build(path, args, entry, controls, glb):
    import hou
    if hou.isUIAvailable() or hou.applicationVersion()[0] != 22:
        raise RuntimeError("Use Houdini 22 hython in a separate process")
    # Houdini determines its native file extension from the active licence.
    licence = hou.licenseCategory()
    expected = {hou.licenseCategoryType.Indie: ".hiplc",
                hou.licenseCategoryType.Apprentice: ".hipnc"}.get(licence, ".hip")
    if path.suffix.lower() != expected:
        raise ValueError(f"This Houdini licence saves {expected} scenes")
    data = path.with_name(path.stem + "_data")
    data.mkdir()
    shutil.copytree(Path(__file__).parent, data / "runtime",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # Establish $HIP before any Python LOP evaluates its relative companion path.
    hou.hipFile.setName(str(path))
    stage_net = hou.node("/stage")
    if args.asset in scene.EXTERNAL:
        package = data / "source.usdz"
        if not UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str(args.source)), str(package)):
            raise RuntimeError("Could not package the supplied USD")
        machine = stage_net.createNode("pythonscript", "MACHINE")
        _install_loader(machine, data.name, "runtime.scene.external(node.editableStage(), data / 'source.usdz')")
    else:
        if args.asset == "stilt":
            shutil.copyfile(glb, data / "stilt.glb")
            stilt_asset.prepare(data / "stilt.glb", data / "textures")
        machine = stage_net.createNode("pythonscript", "MACHINE")
        clip_names = ("", *entry["clips"])
        spares = [hou.StringParmTemplate("clip", "Animation", 1, default_value=(args.clip or "",),
                                         menu_items=clip_names, menu_labels=("Manual pose", *entry["clips"]))]
        for key, default in controls.items():
            spares.append(hou.FloatParmTemplate("control_" + key, key.replace("_", " ").title(),
                                               1, default_value=(default,), min=0, max=1,
                                               min_is_strict=True, max_is_strict=True))
        _spares(machine, spares)
        _install_loader(machine, data.name, f"runtime.live_machine(node, data, {args.asset!r}, {tuple(controls)!r})")
    count, fps = entry["clips"].get(args.clip, (1, 24))
    hou.setFps(fps)
    hou.playbar.setFrameRange(1, max(count, 1))
    hou.playbar.setPlaybackRange(1, max(count, 1))
    hou.setFrame(1)
    source = machine.stage()
    if machine.errors() or not source:
        raise RuntimeError(f"Could not build {args.asset}: {machine.errors()}")
    box = scene.bounds(source, Usd.TimeCode(1))
    # Use representative poses for a fixed camera; no camera bob while scrubbing.
    if args.clip:
        for f in sorted({1, count, *(max(1, int(count * i / 8)) for i in range(1, 8))}):
            hou.setFrame(f)
            box.UnionWith(scene.bounds(machine.stage(), Usd.TimeCode(f)))
        hou.setFrame(1)
    studio = stage_net.createNode("pythonscript", "STUDIO")
    studio.setInput(0, machine)
    choices = tuple(scene.VIEWS)
    _spares(studio, [hou.StringParmTemplate("angle", "Camera", 1, default_value=(args.view,),
                                           menu_items=choices, menu_labels=tuple(i.title() for i in choices)),
                     hou.IntParmTemplate("width", "Width", 1, default_value=(args.size[0],), min=1, min_is_strict=True),
                     hou.IntParmTemplate("height", "Height", 1, default_value=(args.size[1],), min=1, min_is_strict=True)])
    limits = [tuple(box.GetMin()), tuple(box.GetMax())]
    _install_loader(studio, data.name, f"runtime.live_studio(node, {limits!r})")
    out = stage_net.createNode("null", "OUT")
    out.setInput(0, studio)
    out.setDisplayFlag(True)
    target = stage_net.createNode("usdrender_rop", "REDSHIFT")
    target.setInput(0, out)
    delegates = target.parm("renderer").menuItems()
    if scene.RENDERER not in delegates:
        raise RuntimeError("Install the Redshift Solaris plug-in for this Houdini build")
    target.parm("renderer").set(scene.RENDERER)
    target.parm("rendersettings").set("/Render/Settings")
    target.parm("outputimage").set("$HIP/render/" + path.stem + ".$F4.exr")
    target.parm("mkpath").set(1)
    writer = stage_net.createNode("usd_rop", "EXPORT_USD")
    writer.setInput(0, out)
    writer.parm("lopoutput").set("$HIP/" + path.stem + ".usd")
    if args.clip:
        for rop in (target, writer):
            rop.parm("trange").set(1)
            rop.parmTuple("f").set((1, count, 1))
    stage_net.layoutChildren()
    if not out.stage() or studio.errors():
        raise RuntimeError(f"Studio construction failed: {studio.errors()}")
    hou.hipFile.save(str(path))
