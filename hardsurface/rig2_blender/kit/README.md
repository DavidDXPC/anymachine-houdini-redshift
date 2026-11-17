# Oil Rig V2 kit: every modelled piece of the map

Nothing here is wired into the game. The map is `?map=rig2` (grey box); its boxes are `rig2_blender/plan/rig2_boxes.json`
(x east, y up, z south, metres). The approved look is `rig2_blender/concepts/out/v5_ref/bypass/` (overcast film grade,
light wear: used, not new, not rusty).

## What is where

- `manifest.json`: the 59 components, by family, each with a track:
  - `model`: hand-modelled in Blender Python from its reference sheets, on the rig 1 kit (`dugout_blender/props_hand/_common/hs.py`).
  - `generate`: image-to-3D from its turnaround sheet (Meshy 7.1 and Tripo H3.1, best of the two), then prepped.
  - `script`: parametric, built from the blockout's own boxes (stairs, deck plate, lattice landmarks).
  - `reuse`: a rig 1 hand-modelled prop (`dugout_blender/props_hand/<kind>`), repainted to this look.
- `sheets/<id>_turn.png`: six views of the one object (top row: front, left, back; bottom row: right, top, three-quarter).
  `sheets/<id>_detail.png`: six close-ups (corner, joint, foot, functional detail, plain surface, most worn spot).
  Made by `gen_sheets.mjs` (GPT Image 2.6, seeded from the reference photo the object appears in). The sheets are the
  brief: proportions, part breakdown, fastener spacing and wear come from them; sizes come from the manifest.
  The large structures (crane, derrick, flare boom, separator tower, helideck) also have `sheets/<id>_close1.png` (and
  `_close2`): six named close-ups each of joints, lattice bays, pivots and feet, made by `gen_closeups.mjs` from the
  turnaround. They are built exterior-only but accurately: member sections, lacing and joints come from these.
- `_tex/out/`: shared seamless tiles (1024 px): `paint_offwhite`, `paint_ochre`, `paint_darkblue`, `deck_antislip`,
  `wood_crate`, `steel_galv`, `rust_steel`. Other paint colours are `paint_offwhite` with `tint=` in `b.wear(...)`.
  Rig 1's decals and stains are in `dugout_blender/props_hand/_tex/out/` (stencil text there says "RIG 7": do not use
  the text decals; blank plates and stains are fine).
- `<family>/<id>/build.py` -> `<id>.blend`, `<id>.glb`, `<id>_color|normal|orm.png`, `stats.json`, `review.jpg`.

## Rules for a component

1. Read `dugout_blender/props_hand/README.md` and one existing build (`box_yellow/build.py`) first. Same method here:
   separate real parts, one-segment chamfers where they matter, no hidden faces, no n-gons, bake-only detail for
   anything under about 8 mm, wear shader, Cycles bake.
2. Size is the manifest's `dims` (long side along X, front faces -Y, origin bottom centre, Z up in Blender).
   `b.stats(min, max)` must report the bounding box error; keep it under 5 mm. A cover prop that is bigger or smaller
   than its box breaks the collision.
3. Modular pieces must tile: decks are 0.3 m thick, module walls 0.3 m thick and 3.7 m tall on the main deck and upper
   deck (4.7 m in the cellar), rails 1.1 m tall in 1.5 m bays with a 0.1 m toe board, grating panels 1 x 3 m, bridges
   and catwalks 3 m wide, doors 2.4 m wide and 2.2 m high. Build one bay with clean ends so copies butt together.
4. Budgets: a cover prop 1,500 to 4,000 triangles; a tiling bay 200 to 1,200; a big piece (container, tank) up to
   6,000. One 2048 texture set for anything over 2 m, 1024 under.
5. Gate, every component: render the model from the same six directions as its turnaround sheet, same framing, flat
   light, and put sheet and render side by side as `review.jpg`. Look at it. Fix what differs in silhouette, part
   breakdown or colour before calling it done. A build that ran without errors proves nothing about how it looks.
6. Stay in your own family folder. Do not edit `hs.py`, the manifest, the sheets, the tiles, anything under `web/`,
   `dugout_blender/` or `blockouts/`. If the kit lacks something, copy what you need into your folder and say so.
7. Blender is `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, always `-b --factory-startup -t 4`
   (four threads: this PC has 32 cores shared with other sessions' renders and the game; an unthrottled bake takes
   all of them). **No full bakes or
   final renders on this PC.** Heavy compute goes to the Blender render farm (cloud workers), which is not deployed
   yet. Locally, do only quick checks: geometry (`-- --nobake`), a preview bake at `-- --size 1024 --spp 8`, and the
   review stills. Leave the full 2048 bake undone, make sure `build.py` can do it unattended with one command, and
   list that command in `BAKE.md` in your family folder (one line per component) so it can be sent to the farm.
   The farm job has no network and sees only: your family's `.py`, `.json`, `.md` and `.txt` files (and small
   images named `decal_*.png`, `mask_*.png` or `ref_*.png`), `hs.py`, the two tile folders and
   `rig2_blender/plan/rig2_boxes.json`, at the same relative paths as here. So `build.py` must bake from those alone,
   find everything by paths relative to itself, take `--size` and `--spp`, and must not need the reference sheets:
   keep the review render in a separate script or behind a flag. `farm/make_spec.mjs` makes one job per `build.py`.
8. Commit nothing. Do not print or ask for API keys. No spend: if a sheet is unusable, say which and why.

## Report

End with: per component, triangles, bounding-box error, texture size, the path of `review.jpg`, and one line on what
still differs from the sheet. Say plainly what was not built.
