"""Build and package a Solaris kit from a local reference manifest."""
from argparse import ArgumentParser
import json
from pathlib import Path
import tempfile
from pxr import Sdf, Usd, UsdUtils
from . import author


def write_stage(spec, base_dir, destination, standalone_item=False):
    if destination.suffix.lower()==".usdz":
        with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
            intermediate=Path(tmp)/"library.usdc"
            report=write_stage(spec,base_dir,intermediate,standalone_item)
            if not UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str(intermediate)),str(destination)):
                raise RuntimeError("Could not package the kit and its dependencies")
            return report
    stage=Usd.Stage.CreateNew(str(destination))
    report=author(stage,spec,base_dir)
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World/Kit"))
    if standalone_item:
        # A reference to the library's default prim includes the shared Looks scope.
        stage.GetPrimAtPath("/World/Kit").SetDisplayName(report["items"][0]["id"])
    stage.GetRootLayer().Save()
    return report


def run(spec_file,destination,separate=False):
    spec_file=Path(spec_file).resolve();target=Path(destination).resolve()
    if target.suffix.lower() not in (".usd",".usdc",".usda",".usdz"):
        raise ValueError("Use a USD, USDA, USDC or USDZ extension")
    spec=json.loads(spec_file.read_text(encoding="utf-8-sig"))
    report_file=target.with_name(target.stem+".manifest.json")
    items_folder=target.with_name(target.stem+"_items")
    outputs=([items_folder] if separate else [])+[report_file,target]
    for path in outputs:
        if path.exists():raise FileExistsError(f"Output exists: {path}")
    target.parent.mkdir(exist_ok=True,parents=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        folder=Path(tmp)
        report=write_stage(spec,spec_file.parent,folder/target.name)
        if separate:
            items=(folder/items_folder.name);items.mkdir()
            for row,item in zip(report["items"],spec["items"]):
                single=dict(spec,items=[dict(item,position=[0,0,0],yaw=0)])
                item_path=items/(item["id"]+".usdz")
                write_stage(single,spec_file.parent,item_path,True)
                row["asset"]=(Path(items_folder.name)/item_path.name).as_posix()
        (folder/report_file.name).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        published=[]
        try:
            for path in outputs:
                (folder/path.name).rename(path)
                published.append(path)
        except OSError:
            for path in reversed(published):
                path.rename(folder/path.name)
            raise
    return report


def main():
    cli=ArgumentParser(description="Build a Houdini Solaris prop kit")
    cli.add_argument("manifest",type=Path)
    cli.add_argument("output",type=Path)
    cli.add_argument("--per-item",action="store_true",help="also write one portable USDZ per prop")
    args=cli.parse_args()
    report=run(args.manifest,args.output,args.per_item)
    print(f"{len(report['items'])} items written to {args.output}")


if __name__=="__main__":
    main()

