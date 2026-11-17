# helicopter: the aircraft on the Oil Rig V2 helideck

An invented medium twin offshore crew-transport helicopter (two pilots, ten passengers), parked with the rotor
stopped, chocked and strapped to the deck. Not a real type, operator, livery or registration: the shape is generic,
the livery (off-white, navy belly and fin, one orange band, fleet number 07) is made up.

Nothing here is wired into the game or the scene. `rig2_blender/scene/rig2.blend` was only read.

## Size (picked from the deck, not the other way round)

The helideck is 14 x 16 m between its rails (touchdown circle 9.2 m, centre Blender (7, -27, 13)), with the walkway
tab to the east. The largest aircraft whose whole length fits inside 14 m: main rotor 11.4 m, overall length 13.9 m
(rotor tip to tail rotor), fuselage 11.9 m, height 4.4 m, wheel track 3.0 m. Parked on the H's axis, nose east
towards the walkway (people approach from the front, in the pilots' view), tail to the open sea side. Rotor tips
stay 2.3 m inside the north and south rails and 0.8 m inside the east edge of the main deck; the fin and tail rotor
stand 0.1 to 0.7 m out over the west rail and safety net, 2.2 m and more above the deck.

## Files

| file | what |
| --- | --- |
| `sheets/heli_turn.png`, `heli_ortho.png`, `heli_close1..8_*.png` | the reference sheets, made first (`gen_refs.mjs`, prompts beside each) |
| `heli.py`, `build.py` | the model: lofted skin with real window openings and door gaps, every mechanism as separate parts |
| `helicopter_hi.blend` | bake source: game meshes plus the bake-only detail (`hi_*` objects), wear shaders, projected livery |
| `helicopter.blend`, `helicopter.glb` | game-ready, baked |
| `heli_body_*`, `heli_mech_*`, `heli_interior_*` `color / normal / orm .png` | the three texture sets |
| `tex/decal_*.png` | generated livery, numerals, soot, anti-glare and walkway masks (shapes drawn in code, no font, no logo) |
| `renders/` | final stills from the farm (Cycles): `clay_*` from the bake source, `tex_*` from the baked game meshes |
| `collision_boxes.json` | proposed collision in the map's box format, and what on the deck is in the way |
| `stats.json` | triangles, UV fill, bounds, texture sizes, placement |
| `farm/` | `make_spec.mjs` (stage + one-job spec), `collect.mjs`, the run log and results |
| `spend.jsonl` | generation spend (estimate) |

Objects in `helicopter.blend` / `.glb`, all with origin at the deck under the rotor mast, nose +X, Z up:

- `heli_body` (set heli_body): fuselage, cowling, intakes, exhausts, sponsons with flotation covers, fin, stabiliser,
  door hinges / handles / rail, wipers, pitot tubes, antennas, lights.
- `heli_rotor` (set heli_mech): mast, swashplate with servos and scissors, hub, five grips with bearings, dampers,
  pitch horns and links, five blades. Its own object so it can be hidden or turned.
- `heli_mech` (set heli_mech): tail rotor and gearbox, landing gear, boarding steps.
- `heli_tiedown` (set heli_mech): four ratchet straps, wheel chocks with ropes, blade tip socks and ropes, pitot
  covers. Only valid at the placement in `stats.json`: the straps end on the helideck's own tie-down points.
- `heli_interior` (set heli_interior): cabin liner, floor, bulkheads, two pilot seats, ten passenger seats with
  harnesses, instrument panel with four displays, pedestal, overhead panel, cyclics, collectives, pedals.
- `heli_glass`: the windows, one see-through material (alpha 0.32), not baked.

## Rebuild

    blender -b --factory-startup -t 4 --python build.py -- --nobake              # geometry and helicopter_hi.blend, seconds
    blender -b --factory-startup -t 4 --python build.py -- --size 1024 --spp 8   # local preview bake (about 4 minutes)
    blender -b helicopter_hi.blend -t 4 --python shots.py -- <abs out dir> a clay hi   # quick clay stills (Workbench)
    blender -b --factory-startup --python compose.py                            # stills beside their sheets -> rig2_blender/out/helicopter/

The full bake (4096 / 4096 / 2048, 24 samples) and the final stills run on the farm, never locally: see `BAKE.md`.
