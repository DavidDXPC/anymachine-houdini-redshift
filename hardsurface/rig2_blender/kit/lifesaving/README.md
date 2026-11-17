# lifesaving: the lifeboat station, hand-modelled

Replaces the generated `lifeboat` prop (`kit/generated/props/lifeboat.blend`, Meshy) with two hand-built components.
Both are made in the old prop's own frame (the "station frame"), so each takes the old prop's transform unchanged.

| component | what | objects in its .blend | texture sets |
| --- | --- | --- | --- |
| `survival_craft/` | totally enclosed motor-propelled survival craft: moulded hull with chine, keel and skeg, rubber rubbing strake, canopy, boarding hatches with hinges and dogs, portlights, conning position, on-load release hooks in their boxes, deluge pipe, grab rails, becketed grab line, propeller in its nozzle, rudder; tape and lettering baked | `survival_craft` | one 2048 |
| `lifeboat_davit/` | fixed twin-arm davit, winch with cross shaft and a drum per fall, wire falls, suspension links, head sheaves, embarkation platform (grating, rails, chains), fender pads, gripe lashings with turnbuckles, control box, base girders bolted to the deck edge, knee braces to pads on the cellar wall | `lifeboat_davit`, `lifeboat_davit_grate` (tiling grating, alpha) | one 2048 + a 128 px tile |

- `_shared/station.py`: the station frame, the hull sections and the hook positions both builds use.
- `_shared/ls.py`: helpers on top of `landmarks/_shared/lm.py` and rig 1's `hs.py` (both imported, not edited).
- `_shared/shots.py`: close-up stills (clay or textured) of any set of .blend files in the station frame.
- `gen_refs.mjs`: the reference sheets (`kit/sheets/survival_craft_*.png`, `lifeboat_davit_*.png`); `spend.jsonl` is what they cost.
- `BAKE.md`, `farm/`: the farm bake and the farm stills.
- `HANDOVER.md`: placement for the scene.

Station frame: boat along Y (bow +Y); the main deck edge is the plane x = -2.25 with the deck on -X; deck top z = 2.6;
the cellar wall face the braces land on is x = -4.25 (map x = 2.0).  Look: maintained but in service.
