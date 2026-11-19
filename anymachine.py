"""CLI. Run with Houdini 22 hython, or Python with numpy and usd-core for USD/GLB."""
import argparse
import json
import math
import os
from pathlib import Path
import tempfile

from pxr import Sdf, Usd

from houdini import materials, scene, stilt_asset

ROOT = Path(__file__).resolve().parent
STILT = ROOT / "assets" / "stilt.glb"


def parse_controls(pairs, defaults):
    values = dict(defaults)
    for pair in pairs:
        key, sep, raw = pair.partition("=")
        if not sep or key not in defaults:
            raise ValueError(f"Unknown control {pair!r}. Available: {', '.join(defaults)}")
        value = float(raw)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{key} must be between 0 and 1")
        values[key] = value
    return values


def write_usd(args, entry, controls, output, stage_dir):
    stage = Usd.Stage.CreateNew(str(stage_dir / output.name))
    scene.init(stage)
    count, fps = entry["clips"].get(args.clip, (1, 24))
    stage.SetFramesPerSecond(fps)
    stage.SetTimeCodesPerSecond(fps)
    stage.SetStartTimeCode(1)
    stage.SetEndTimeCode(count)
    if args.asset == "stilt":
        texture_folder = output.stem + "_textures"
        stilt_asset.prepare(STILT, stage_dir / texture_folder)
        stilt_asset.author(stage, STILT, texture_folder, args.clip, materials.material)
    elif args.asset in scene.EXTERNAL:
        from pxr import UsdUtils
        package = output.stem + "_source.usdz"
        if not UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str(args.source)), str(stage_dir / package)):
            raise ValueError("Could not package external USD dependencies")
        source = Usd.Stage.Open(str(stage_dir / package))
        if not source.GetDefaultPrim():
            raise ValueError("Supply an asset with a default prim")
        scene.external(stage, stage_dir / package)
        source_prim = stage.GetPrimAtPath("/Machine/Source")
        source_prim.GetReferences().SetReferences([Sdf.Reference(package)])
    else:
        frames = ((i, Usd.TimeCode(i)) for i in range(1, count + 1)) if args.clip else [(1, Usd.TimeCode.Default())]
        screen = None
        if args.asset == "laptop":
            import shutil
            screen = output.stem + "_screen.png"
            shutil.copyfile(ROOT / "houdini/rigs/screen_ui.png", stage_dir / screen)
        scene.geometry(stage, args.asset, controls, args.clip, frames, screen_texture=screen)
    stage.SetDefaultPrim(stage.GetPrimAtPath("/Machine"))
    box = scene.bounds(stage, Usd.TimeCode(1))
    if args.clip:
        for i in range(2, count + 1):
            box.UnionWith(scene.bounds(stage, Usd.TimeCode(i)))
    scene.studio(stage, box, args.view, args.size, "./" + output.stem + ".exr")
    stage.GetRootLayer().Save()
    return scene.compact_report(stage)


def main():
    parser = argparse.ArgumentParser(description="AnyMachine | Houdini 22, Solaris and Redshift")
    commands = parser.add_subparsers(dest="cmd", required=True)
    production = commands.add_parser("production", help="assemble AnyScene, AnyKit, AnyMachine and AnyShot in Solaris")
    production.add_argument("manifest", type=Path)
    production.add_argument("output", type=Path, help="new delivery folder")
    production.add_argument("--hip", action="store_true", help="also save the Houdini 22 scene")
    production.add_argument("--render", choices=("still", "sequence", "video"), help="render through the Redshift ROP")
    production.add_argument("--frame", type=int, default=1)
    production.add_argument("--display", default="sRGB - Display", help="OCIO review display")
    production.add_argument("--view", default="ACES 2.0 - SDR 100 nits (Rec.709)", help="OCIO review view")
    listing = commands.add_parser("list", help="print assets or the controls and clips of one asset")
    listing.add_argument("asset", nargs="?")
    checker = commands.add_parser("check", help="reopen USD and validate mesh topology and dimensions")
    checker.add_argument("path", type=Path)
    checker.add_argument("--frame", type=float, default=1)
    for command in ("usd", "hip", "glb"):
        sub = commands.add_parser(command)
        sub.add_argument("asset")
        sub.add_argument("output", type=Path)
        sub.add_argument("--clip")
        sub.add_argument("--set", dest="controls", metavar="CONTROL=VALUE", action="append", default=[])
        if command != "glb":
            sub.add_argument("--source", type=Path, help="supplied USD prop, including USDZ")
            sub.add_argument("--view", choices=scene.VIEWS, default="hero")
            sub.add_argument("--size", type=int, nargs=2, default=(960, 540), metavar=("WIDTH", "HEIGHT"))
    args = parser.parse_args()
    if args.cmd == "production":
        from houdini.production import run
        return run(args)
    if args.cmd == "check":
        stage = Usd.Stage.Open(str(args.path.resolve(strict=True)))
        print(json.dumps(scene.compact_report(stage, args.frame), indent=2))
        return
    entries = scene.catalog(STILT)
    if args.cmd == "list" and args.asset is None:
        for name, entry in entries.items():
            print(f"{name:24} {entry['family']}")
        return
    if args.asset not in entries:
        parser.error("unknown asset; run 'list' for the available IDs")
    entry = entries[args.asset]
    if args.cmd == "list":
        print(json.dumps(entry, indent=2))
        return
    if args.clip and args.clip not in entry["clips"]:
        parser.error(f"available clips: {', '.join(entry['clips']) or '(none)'}")
    if args.cmd != "glb":
        if min(args.size) < 1:
            parser.error("resolution must be positive")
        if args.asset in scene.EXTERNAL:
            if not args.source or not args.source.is_file():
                parser.error("this prop needs its licensed base mesh as --source file.usd")
            args.source = args.source.resolve()
        elif args.source:
            parser.error("--source applies to external props only")
    elif args.asset in scene.EXTERNAL:
        parser.error("external props use 'usd' or 'hip' with --source")
    controls = parse_controls(args.controls, entry["controls"])
    output = args.output.resolve()
    suffixes = {"usd": (".usd", ".usdc", ".usda"), "hip": (".hip", ".hiplc", ".hipnc"), "glb": (".glb",)}
    if output.suffix.lower() not in suffixes[args.cmd]:
        parser.error(f"expected extension: {', '.join(suffixes[args.cmd])}")
    if output.exists():
        parser.error(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".anymachine-", dir=output.parent) as tmp:
        staging = Path(tmp)
        if args.cmd == "usd":
            print(json.dumps(write_usd(args, entry, controls, output, staging), indent=2))
        elif args.cmd == "glb":
            from houdini.glb_export import export
            export(staging / output.name, args.asset, controls, args.clip, STILT)
        else:
            from houdini.session import build
            build(staging / output.name, args, entry, controls, STILT)
        main_file = staging / output.name
        if not main_file.is_file():
            raise RuntimeError("The requested file was not written. Check the licence and the file extension.")
        companions = [p for p in staging.iterdir() if p != main_file]
        if any((output.parent / p.name).exists() for p in companions):
            raise FileExistsError("A companion folder already exists. Use a new version name.")
        for item in companions:
            item.rename(output.parent / item.name)
        # Create the final name atomically without replacing a concurrent export.
        try:
            os.link(main_file, output)
        except OSError:
            with main_file.open("rb") as src, output.open("xb") as dst:
                import shutil
                shutil.copyfileobj(src, dst)
    print(output)


if __name__ == "__main__":
    main()
