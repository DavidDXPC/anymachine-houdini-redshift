# AnyMachine: working mechanical rigs from a generated mesh

Part of a family: [AnyScene](https://github.com/apekshik/anyscene) builds whole sets,
[AnyKit](https://github.com/apekshik/anykit) builds the props that go in them, AnyMachine makes those props move, and
[AnyShot](https://github.com/apekshik/anyshot) shoots the result.

Give AnyMachine an object (a reference image, or a static mesh from a kit) and it hands back a rig that works: a laptop
lid on a real hinge, legs that walk without sliding, a bag that fills and opens. Every control is a 0-1 parameter, and
every result is checked by machine before anyone looks at it.

**Status: experiments.** This repo holds the four runs so far; there is no endpoint yet.

## How it works

1. **Generate** the object in an articulated pose (Meshy and Tripo, both tried).
2. **Treat the mesh as a skin.** Measure the joint axes off it, then rebuild the moving parts as clean geometry on those
   axes: coaxial hinge barrels, side-by-side joint slabs, so nothing can pass through anything.
3. **Expose parameters.** Each joint gets a 0-1 custom property with drivers and limits, and bakes to linear glTF
   actions, so `seek(t = value)` poses the GLB in any engine.
4. **Check.** Sweep every parameter for triangle overlaps, clamp out-of-range values, measure foot slip, then re-import
   the GLB to confirm it matches.

## Experiments

| | Joints | Result |
|---|---|---|
| [laptop](laptop/NOTES.md) | one lid hinge, 0-135 deg | Works. 0 overlaps over the full sweep, min clearance 0.32 mm |
| [quadruped](quadruped/NOTES.md) | 4 legs x 3 joints; trot, idle, sit, stand | Works. 0 overlaps, 0.014 mm foot slip; legs are plain slabs |
| [spider](spider/NOTES.md) | 8 legs x 3 joints; walk, idle, crouch | Works. 0 overlaps; generators gave 6 legs, the 8 come from the brief; body skin is rough |
| [backpacks](backpacks/NOTES.md) | roll, clip, fill, flap, zip, straps | Partly. The roll-top passes every check; the rucksack and daypack fail where controls interact |

What the backpacks showed: hinges, sliders and wheels cover hard-surface objects, but soft goods need their own joint
types (`flap`, `zip_path`, `fill`, `strap`, `roll`, `clip`, `jiggle`) and a way to say which controls depend on each
other. The notes in `backpacks/` draft them.

## Running

Each folder has a `run_all.sh` (`run_bag.sh` for the backpacks) that rebuilds everything from the cached generations
in its `gen/` folder, headless, with Blender 5.0. Generations, `.blend` files, GLBs and render frames are not in the repo;
the demo GIFs, stills and `check.json` reports are.
