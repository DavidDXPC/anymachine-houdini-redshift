# AnyMachine experiment 3: a quadruped that walks

Date: 2026-11-03. Everything runs headless with Blender 5.0. To rebuild from the cached generation, run `bash run_all.sh`; `bash run_all.sh render` re-renders only.

## What came out

| | |
|---|---|
| Trot loop | `out/quadruped_trot.mp4` (1280x720, 72 frames, 30 fps, 4 gait cycles), `out/quadruped_trot.gif`. Cycles. The camera tracks the robot at gait speed, so the loop is seamless and the 12 cm checker floor shows the motion. |
| Sit / stand | `out/quadruped_sit_stand.mp4`, `.gif` (Eevee) |
| Stills | `out/stills/`: `persp_trot_forward_{001,013}`, `persp_sit_049` (three-quarter); `side_trot_{001,005,010}`, `side_sit_049` (ortho side); `knee_trot_{001,010}`, `knee_sit_049` (FL knee close-up; the cap's notch shows shin rotation) |
| Rig | `out/quadruped.blend`. Armature `quadruped_rig`: `root` → `body` → 4 × (`XX_haa` → `XX_hfe` → `XX_kfe`), legs FL FR HL HR. There are 13 rigid groups and no skinning. |
| GLB | `out/quadruped.glb` (11.6 MB). Actions: `trot` (1 cycle, in place, loops), `trot_forward` (4 cycles with root motion), `idle` (4 s loop), `sit`, `stand`. Every action is linear per-frame FK keys, so no drivers or IK are needed. Rig extras: `anymachine` (joint spec JSON) and the gait params. |
| Check | `out/check.json` (+ `check.log`) |
| GLB re-import | `out/verify_glb.json`: all 5 actions present, and every action reproduces the planner's foot centres to ≤ 0.001 mm |
| Build report | `out/build.json`: every measured and derived number |

### Scripts

All scripts are in `scripts/`:
- `probe.py`: measurement probe.
- `build.py`: GLB → rigged .blend.
- `gait.py`: kinematics, IK and gaits. It is also embedded in the .blend as a Text block: edit the rig's custom props, then Run Script to re-bake.
- `check.py`
- `export.py`
- `verify_glb.py`
- `render.py`

## Size

I picked an **overall length of 0.70 m** (head to rear foot) and let the generator's proportions set the rest:

| Dimension | Value |
|---|---|
| Hip axis height (bind pose) | 0.331 m |
| Hip axis height (standing gait) | 0.32 m |
| Body top | 0.42 m |
| Body width | 0.21 m |
| Width across the legs | 0.41 m |
| Thigh | 0.188 m |
| Shin | 0.190 m |
| Foot ball radius | 25.5 mm |

## Pipeline as built

1. **Reference.** I generated 2 GPT Image 2.5 (sunburst) candidates of an invented quadruped in three-quarter view, standing with its knees visibly bent, and used `refs/quad_0.png`. Both candidates gave knees pointing backward, which the mesh then carried.
2. **Image-to-3D.** I ran Tripo P2 (face_limit 50k) and Meshy v7.1 and picked **Meshy**:
   - The legs are symmetric and the knee barrels crisp.
   - The light-grey shell matches the reference.
   - Tripo's version was dark and chrome, the same metallic-map problem as experiment 1, and its legs were asymmetric.

   Contact sheets are in `gen/tripo_grid.png` and `gen/meshy_grid.png`.
3. **Normalise.** Meshy is already Z-up with the front at −Y. I scaled it uniformly to a 0.70 m Y extent, centred X and Y, and put the feet on z = 0.
4. **Measure (automatic, per leg).**

   | Measurement | Method |
   |---|---|
   | Body underside, top, half-width | Percentiles of a central column |
   | Foot ball | Lowest-cluster centroid; radius from its x extent |
   | Hip housing | Widest 5 mm bin in the top 9 cm of the outboard side profile: radius = half its width, centre = top − r |
   | Knee | Profile bin that deviates most from the hip→foot line. The side of the deviation gives the knee direction; the bin width gives the barrel radius. |

   - All 4 legs measured "knee points back".
   - **Left and right agree within 1–7 mm** on hip position and ±6 mm on segment length, so the measurement is real, not noise.
   - I then symmetrised: one leg design (the mean thigh and shin vectors), hips per end (the mean of L and R), and feet directly under the hips.
5. **What was measured vs designed.**
   - **Measured:** hip axis height and front/hind positions, thigh and shin vectors (so lengths and bind angles), knee direction, foot radius, body wall x.
   - **Designed:** the lateral layout. A side profile can't give it, and the generated legs are fused blobs in x. Everything is offset from the measured wall at `hw` = 105 mm:
     - HAA pivot inside the body at hw − 30 mm;
     - fixed bearing disc on the wall;
     - HAA flange, then the HFE motor (r 48 mm);
     - thigh slab outboard (24 mm thick);
     - shin slab inboard of the thigh (20 mm);
     - knee cap outboard of the thigh.

     Each moving link sits in its own x-slab, coaxial with its joint, with 1–2 mm running gaps. Adjacent links therefore **cannot clip at any angle, by construction**: the lesson from the experiment 1 barrel, applied per joint.
6. **Body.**
   - **Kept** the generated shell, including its head, sensor visor, panels and the dark hip-recess detail. I bisected away everything outboard of hw + 3 mm (actuators and legs), then dropped 632 tiny leftover islands.
   - The cut holes sit exactly under the rebuilt bearing discs, so they never show.
7. **Legs (all rebuilt):**
   - HAA flange and HFE motor, with a machined ring;
   - thigh: a tapered stadium slab with bevels;
   - shin: a tapered slab with a dark inset stripe;
   - knee cap, with a notch;
   - rubber ball foot.

   The leg grey is sampled from the shell's base-colour texture (sRGB → linear).
8. **Rig.**
   - Bones lie along the segments: `hfe` runs hip→knee and `kfe` runs knee→foot, with roll set so that bone X = world X (asserted at build). `haa` points ∓Y, so a positive local Y rotation = abduction on both sides.
   - Limit Rotation per joint, in local space. Limits are HAA ±18°, HFE ±60°, knee −77.9..+62.1° (knee interior angle 30..170°).
   - IK: `ik_XX` empties on the root bone, plus an IK constraint (chain 3) on each `kfe`, with IK locks and IK limits per bone. Influence is driven by the rig prop `ik`, which defaults to 0, so the baked FK actions play. Set it to 1 to pose by dragging the feet.
9. **Gaits** (`gait.py`). Exact analytic IK in the rig's own conventions: HAA from the lateral plane offset, then a planar 2-link. What we key is what Blender evaluates; the tracking error measures as 0.00001°.
   - **Trot.**
     - Diagonal pairs FL+HR and FR+HL, duty 0.55.
     - Swing is a cycloid in time with a cosine height profile.
     - Body bob 6 mm at twice the gait frequency, pitch ±1.2° at twice the gait frequency, roll ±1.5° at gait frequency.
     - Params, all rig custom props: `step_length` 0.24 m (world stride per cycle), `step_height` 0.07, `body_height` 0.32, `speed` 0.40 m/s, `duty`, `pitch_deg`, `roll_deg`, `bob`. Period = step_length / speed = 0.6 s = 18 frames.
     - **Rolling contact:** stance feet are not pinned. The ball centre is shifted by r × (the foot's incremental rotation), iterated 3×, so the *contact material point* is stationary. That is true rolling, about 9 mm of travel per stance, and no skating.
   - **Idle:** 4 s loop of lateral sway (14 mm), roll 1.6°, pitch 0.8° and a 4 mm dip, with all feet planted and rolling.
   - **Sit:** 1.6 s. The body pitches 25° nose-up, drops to a 0.235 m body-centre height and shifts 4 cm back. All four feet stay planted.
   - **Stand:** sit played backwards. Rolling is reversible, so it stays slip-free and starts exactly where sit ends.

## Check results (`out/check.json`)

| Check | Result |
|---|---|
| Single-joint sweeps: 12 joints, 2° steps, commanded 6° past each limit | **0 overlaps.** The constraint clamps exactly (error 0.000°). Min clearance 2.0 mm (the designed running gaps); min non-adjacent clearance 8 mm (hind HFE at −60° vs the front leg). |
| HFE limit | Was −70° at first. The sweep found the hind leg hitting the same-side front shin past −64°, so I set it to −60°. The check did its job. |
| Actions (trot, trot_forward, idle, sit, stand: 311 frames) | **0 overlaps in every frame. All joints stay within limits.** Max FK tracking error 0.00002°. The evaluated foot centre matches the planner to 0.000 mm. Lowest non-foot point 12.5 mm above the ground (the shin tip next to the ball). Foot penetration 0. |
| Foot slip, trot_forward (16 stances) | **0.014 mm per stance** (material point in contact, frame to frame). Rolling travel is 9 mm per stance; this is rolling, not slip. |
| Foot slip, idle / sit / stand | 0.46 / 0.22 / 0.22 mm per action. That is residue from the iterated rolling solve on large body motions; the sit roll is 15.6 mm. |
| Random poses (300, all 12 joints uniform within limits) | **17/300 (5.7%) have a leg-leg overlap:** shin\|shin 11, shin\|thigh 6, haa\|shin 5, all between the same-side front and hind legs. Per-joint limits can't prevent this, because it depends on two legs together. |
| GLB re-import | 5 actions, frame ranges intact, feet match the planner to ≤ 0.001 mm |

**Contact tolerance note.** With a 0.2 mm "in contact" threshold, trot slip read 1.7 mm per stance. That was the first swing frame, which sits only 0.105 mm above the ground while the shin is already swinging forward: a lift-off *scuff*, not stance slip (`check_tol0.2mm.log`). The final check uses 0.05 mm. A swing profile that lifts faster in its first frame would remove it.

## Honest quality notes

- **The gait reads as a believable trot.**
  - The diagonal pairs are clear, the knees fold in swing, and the body has a slight bob and roll.
  - At 0.6 s per cycle and 0.4 m/s it looks brisk and robotic, which is right for this class.
  - It is a kinematic gait: no dynamics, no centre-of-mass planning. Duty 0.55 gives brief 4-foot support, so it never looks like it's falling.
- **The feet don't slide.** The rolling-contact solve is the reason. Pinning the ball centre would have spun the ball in place and skated by about r·Δθ (≈ 9 mm per stance).
- **Nothing clips in any shipped action**, and adjacent links can't clip by construction. Leg-to-leg contact is possible in about 6% of random in-limit poses, so anyone posing by hand with IK on can make the front and hind legs touch.
- **What looks procedural:**
  - The rebuilt legs are clean, bevelled slabs: correct but plain next to the generated body, with no fasteners, cables or panel lines.
  - The thigh is a flat slab. The reference thigh is a sculpted cover.
  - The ball feet are plain UV spheres.
- **Shell problems:**
  - The generated body has a mottled patch on its flank (Meshy texture).
  - The cut leaves the generator's dark hip-recess detail visible around the motors. It mostly reads as a housing interior.
- **Shadows** under the feet are soft in the tracking shot, so contact reads mainly from the motion.
- There is one foot track for all four legs (x = 154 mm). The generated front feet were at 180 mm and the hind feet at 139 mm, so the front stance is 2.6 cm narrower than the reference and the hind 1.5 cm wider.
- The sit is a "rump-down" robot sit with all feet planted. It doesn't fold the front legs, and there is no lie-down.

## What had to be remade (and why)

| Part | Generated mesh | Fix |
|---|---|---|
| All 4 legs | Fused to the body at the hips. Each leg is one blob, with no separation between thigh, knee and shin in x. Front and hind tracks differ by 4 cm. | Rebuilt as 6 parts per leg in disjoint x-slabs, from measured lengths and angles |
| Hip actuators | Fused to the body side and to the thigh | Fixed bearing disc (body) + HAA flange + HFE motor (moves with HAA) |
| Feet | Fine shape, but fused to the shin | Rebuilt as spheres at the measured radius |
| Body | Usable | **Kept** (54k tris after the cut) |
| Materials | Meshy metallic/roughness maps are fine on the body (unlike Tripo's) | Left as is. New leg materials use the sampled body grey. |

## How `ref-to-machine` should grow for legged machines

Experiment 1's schema is joint-centric: one joint, one 0..1 param. A legged machine needs **chains, contacts and gaits** as first-class objects.

```jsonc
{
  "category": "quadruped",                     // prior: body + 4 x 3-DoF legs, knees back, ball feet
  "real_size_m": {"length": 0.70},
  "chains": [
    {"name": "FL", "root": "body", "mirror_of": null,
     "joints": [
       {"name": "FL_haa", "type": "hinge", "axis": "body_y", "limits": [-18, 18]},
       {"name": "FL_hfe", "type": "hinge", "axis": "body_x", "limits": [-60, 60]},
       {"name": "FL_kfe", "type": "hinge", "axis": "body_x", "limits": "auto", "interior_deg": [30, 170],
        "bend": "auto"}                        // "back" | "front" | "auto" (measured from the profile)
     ],
     "segments": {"thigh": "auto", "shin": "auto"},          // lengths measured, or metres
     "end_effector": {"name": "FL_foot", "contact": "ball", "radius_m": "auto"},
     "layout": {"slabs": "auto", "running_gap_m": 0.002}},  // lateral slab layout for coaxial non-clipping links
    {"name": "FR", "mirror_of": "FL"}, {"name": "HL", "mirror_of": "FL", "offset": "measured"}, {"name": "HR", "mirror_of": "HL"}
  ],
  "symmetry": "left_right",                    // average measured L/R, report the disagreement as a quality signal
  "gaits": [
    {"name": "trot", "pattern": {"FL": 0, "HR": 0, "FR": 0.5, "HL": 0.5}, "duty": 0.55,
     "params": {"step_length": 0.24, "step_height": 0.07, "body_height": 0.32, "speed": 0.4},
     "body": {"bob_m": 0.006, "pitch_deg": 1.2, "roll_deg": 1.5}, "root_motion": "both"},  // in_place + forward clips
    {"name": "idle"}, {"name": "sit", "pose": {"pitch_deg": -25, "hip_z": 0.235}}, {"name": "stand", "from": "reverse:sit"}
  ],
  "ik": {"targets": "end_effectors", "solver": "analytic", "in_blend": true},
  "contact": {"model": "rolling", "ground": "plane_z0"}
}
```

Response additions:
- `chains[]`, with measured vs designed values flagged per field. For example, `hip: measured`, `layout_x: designed`, plus `lr_disagreement_mm`.
- `gaits[]`, each with its glTF action name, frame count, loop flag and root-motion speed.
- `validation`:
  - `sweep_overlaps`;
  - `action_overlaps`;
  - `random_pose_overlap_rate` (a quality signal, not a gate);
  - `stance_slip_mm` and `rolling_travel_mm`;
  - `min_ground_clearance_mm`;
  - `ik_reach` and `clamped_keys`.

Notes on what generalises:
- **Use analytic IK, not a solver, for anything you bake.** Write the IK in the rig's own bone conventions and keep the iterative IK constraint only as a .blend posing aid. Then "angles follow commands" and "foot = target" are exact (0.00001°), and the check can compare against the planner.
- **Model contact explicitly.** "Foot pinned" is wrong for anything with a round foot. The endpoint should choose the contact model per end-effector (ball = rolling, flat pad = pinned, wheel = rolling about one axis) and measure slip at the material contact point.
- **Coaxial slabs generalise the experiment 1 barrel:** each link of a chain occupies a disjoint slab along its joint axis. That kills same-chain clipping. **Cross-chain clipping** (front vs hind leg) can't be ruled out with per-joint limits, so the validator must sample combos, and the gait planner must keep stride below the front–hind reach overlap.
- **Expect to rebuild every leg.** The generator gives a believable silhouette and pose (great for measuring), but a single fused blob per leg. The body shell is the part worth keeping.

## Spend

About $1.90, logged to `anyscene/generate/spend.jsonl`: 1 image call (n = 2), Tripo P2 ×1, Meshy v7.1 ×1.
