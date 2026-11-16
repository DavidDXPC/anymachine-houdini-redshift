# Stilt-walker: parts breakdown (written before modeling)

> Written before the build. Where the build ended up different, `README.md` and `stilt_info.json` are the record.
> Changes made during the build: leg segments 8.55 / 7.55 / 5.05 m; hips moved out to Y +/-1.9 (front) and +/-2.2
> (rear), shoulders to +/-3.3; feet at X +5.0 / -5.4, 5.0 m and 9.2 m apart; neck pivots re-spaced along a tighter
> curve and the head pivot at (5.8, 0, 28.85); limb shells sit on the front of legs AND arms with a slot for each
> actuator lug; the foot got a separate `Foot_Collar`; ceramic joint caps are their own parts (`Hip_Cap`, `Knee_Cap`,
> `Ankle_Cap`, `Shoulder_Cap`, `Elbow_Cap`, `Wrist_Cap`); toe and finger meshes are `Toe_Blade_*` and `Finger_Seg_*`
> so no mesh shares a bone's name; three antenna blades per side; after the bake the five frame materials are one
> slot, `M_Stilt_Frame`; the reach action is 312 frames; motion reference clips from a video model were added.

Design C, "Stilt-walker": a 30 m, four-legged, two-armed strider. Design of record is the clean turnaround
`refs/stilt_turnaround.png` and its single views `refs/stilt_front / left / rear / top / 3q.png`, drawn from the
concept `refs/concept_sheet.png`. The seven close-up plates `refs/closeup_*.png` are the hard-surface reference for
each mechanism: `hip`, `knee`, `foot`, `hand`, `head`, `shoulder`, `elbow`.

**Scale.** `refs/stilt_front.png` (608 x 1088): ground at v = 1035, antenna tips at v = 25, so 1010 px = 30.0 m,
**29.7 mm per pixel**, centre line u = 304. `refs/stilt_left.png` (768 x 1024, head pointing left): ground at
v = 992, top at v = 42, 950 px = 30.0 m, **31.6 mm per pixel**, body centre at u = 430.

**Axes (Blender).** +X forward (head), +Y left, +Z up, metres. Origin on the ground under the body centre.

Where the views disagree the front view wins for heights and widths, the left view for the body, neck and head
profile. Known disagreements: the left view fuses the arm and the front leg into one limb, and the top view shows
four limbs instead of six. Both are ignored; the front, rear and three-quarter views agree on four legs plus two arms.

## Overall dimensions

| | Value | Source |
|---|---|---|
| Height | 30.0 m to the antenna tips, 29.5 m to the top of the head shell | front view |
| Footprint | 9.0 m long (front to rear feet) x 8.4 m wide (rear feet); front feet 4.8 m apart | front, 3q |
| Body | 8.6 m long (X -4.4..+4.2), core 2.6 m wide, 10.6 m over the wing shells, Z 19.9..25.3 | left, front |
| Hip height | front 21.3 m, rear 20.9 m | left view |
| Leg segments | thigh 8.6 m, shin 7.6 m, tarsus 5.1 m, foot pivot 0.60 m above ground | front view: knee at 12.9 m, ankle at 5.6 m |
| Leg thickness | beam 1.1 > 0.75 m deep (thigh), 0.75 > 0.55 (shin), 0.55 > 0.42 (tarsus); about 0.6 m wide | front view, 0.65 m at the shin |
| Joint housings | hip drum dia 1.9 m, knee 1.5 m, ankle 1.0 m, shoulder 1.4 m, elbow 1.0 m, wrist 0.72 m | close-ups |
| Foot | three toes 1.5 m long, 2.9 m across | close-up foot |
| Arm | upper arm 7.0 m, forearm 6.8 m, palm 1.2 m, fingers 3.6 m (1.5 + 1.2 + 0.9) | concept front view (see deviations) |
| Neck | 5.2 m along the curve, five links, 1.5 m deep at the base and 0.6 m under the head | left view |
| Head | 4.6 m long, 1.2 m wide, 0.9 m high; antenna blades trail 3.2 m behind it | left, close-up head |
| A person (1.75 m) | reaches a third of the way up the tarsus; the ankle housing is at head height | close-up foot |
| Triangle budget | 200k to 300k, no LODs yet | |

## How the thin legs carry 30 m

The concept draws the legs as bare tapering shells. To make them believable at this size each segment is built as a
**guyed mast**, like a crane boom or a sailboat spar:

- a tapered black-carbon box beam with lightening slots (the compression member);
- two braided **tendon cables** down the back of every segment, held 0.35 to 0.5 m off the beam on spreader
  brackets (the tension members). They run tangent to a grooved cable drum on each joint axis, so they stay
  tangent when the joint turns, as on a cable-driven arm;
- a hydraulic **actuator** across the back of each hip, knee and ankle, a real two-part cylinder and rod on its own
  bones;
- the pale ceramic shell only on the front and sides, held off the beam on stand-offs and split into panels.

The legs also stand in a slight zigzag (knee forward, ankle back) instead of dead straight, so the load path reads
and the crouch has somewhere to go.

## Parts (bone in brackets). Leg parts exist four times (`_FL _FR _RL _RR`), arm parts twice (`_L _R`).

**Body [`pelvis`]**
- `Body_Core`: black carbon hull, a long teardrop keel X -4.2..+4.0, 2.6 m wide, with vent grilles.
- `Body_Frame`: graphite truss ribs, four hip brackets, two shoulder brackets, the wing struts.
- `Body_Spine_Shell`: dorsal ceramic carapace in three plates with seams, ending in the tail point.
- `Chest_Shield`: the pointed ceramic shield at the front, two halves with a centre seam, vent slots, bolts.
- `Wing_Shell_L/R`: the broad drooping shoulder shells, three overlapping ceramic plates each, tip at Z 19.3.
- `Neck_Turret`: bolted bearing ring where the neck leaves the body.
- `Belly_Cables`: four cable loops hanging under the belly between the hips (catenaries, rigid).

**Leg, per leg [`hip`, `thigh`, `shin`, `tarsus`, `foot`, `toe_a/b/c`, six `act_*`]**
- `Hip_Yoke` [`hip`]: abduction block on a fore-aft pin in the body bracket, carrying the hip motor stator, its
  bolted flange and vent ring.
- `Thigh_Beam` [`thigh`]: twin fork arms around the hip drum, tapered box beam, slots, spreader brackets, actuator
  lugs, the knee fork, the ceramic `hip cap` disc.
- `Thigh_Shell` [`thigh`]: the big ceramic haunch plate, three panels, hatch.
- `Thigh_Tendons` [`thigh`]: two cables, clamps.
- `Shin_Beam` [`shin`]: knee tongue with the grooved cable drum, knuckle with triangular lightening holes, beam,
  brackets, lugs, ankle fork. `Knee_Cap`: convex ceramic shield over the outside of the knee (three panels).
- `Shin_Shell`, `Shin_Tendons` [`shin`].
- `Tarsus_Beam`, `Tarsus_Shell`, `Tarsus_Tendons`, `Ankle_Cap` [`tarsus`]. The tendons end in turnbuckle clamps
  above the foot.
- `Foot_Block` [`foot`]: ankle ball in a carbon housing with a ceramic collar, toe hinge lugs.
- `Toe_A/B/C` [`toe_*`]: tapering carbon blade with a ceramic cap, hinge barrel, rubber sole pad. A and B point
  forward-out and forward-in, C points back.
- `Act_Hip_Cyl/Rod`, `Act_Knee_Cyl/Rod`, `Act_Ankle_Cyl/Rod`: cylinder on the upper bone, polished rod on the lower.

**Arm, per arm [`shoulder`, `upperarm`, `forearm`, `hand`, `finger_a1..c3`, two `act_*`]**
- `Shoulder_Yoke`, `Upperarm_Beam`, `Upperarm_Shell`, `Forearm_Beam` (with `elbow cap`), `Forearm_Shell`,
  `Arm_Loom` (cable loom in clips), `Act_Elbow_Cyl/Rod`.
- `Hand_Palm` (wrist drum, carbon palm block, ceramic back plate).
- `Finger_A1..A3`, `Finger_B1..B3`, `Finger_C1..C3`: three fingers, three segments each, pin hinges with round
  bolted caps, ceramic back shells, dark rubber tips. A and B sit side by side, C opposes them like a thumb.

**Neck and head [`neck_01..05`, `head_yaw`, `head`, `sensor`]**
- `Neck_Link_1..5`: carbon lattice vertebrae with a ceramic dorsal plate each, pin joints between them.
- `Neck_Bundle`: the cable bundle along the underside, smooth-skinned over the five neck bones (the one exception
  to rigid single-bone skinning).
- `Head_Yoke` [`head_yaw`]: yaw bearing ring with bolts, yoke arms, pitch pin.
- `Head_Core` (dark underside, sensor bays), `Head_Shell` (ceramic blade, centre seam, panel lines),
  `Head_Antennae` (three trailing ceramic blades and a thin whisker), `Head_Cables` (two hanging loops) [`head`].
- `Sensor_Lenses` (dark bezels and clear domes) [`head`]; `Light_Sensors`: the blue emissive discs, their own
  object and material so the lights can be driven [`sensor`].

## Skeleton

Left side shown; the right side mirrors Y. Leg, arm and finger bones are **segment-aligned**: local Z runs up the
segment toward its upper joint, local Y is the hinge pin, local X is the segment's front. Body, neck and head bones
are world-aligned (X forward, Y left, Z up).

| Bone | Parent | Pivot (X, Y, Z) | Joint | Axis |
|---|---|---|---|---|
| `root` | - | (0, 0, 0) | ground | |
| `pelvis` | root | (0, 0, 21.1) | body | free |
| `hip_FL` | pelvis | (1.6, 1.5, 21.3) | abduction pin in the body bracket | X |
| `hip_RL` | pelvis | (-2.0, 1.9, 20.9) | same | X |
| `thigh_*` | hip | at the hip | hip drum | Y |
| `shin_*` | thigh | 8.6 m down | knee: thigh fork, shin tongue, pin | Y |
| `tarsus_*` | shin | 7.6 m down | ankle: shin fork, tarsus tongue, pin | Y |
| `foot_*` | tarsus | 5.1 m down, 0.60 m above ground | ball joint | free, stays level |
| `toe_a/b/c_*` | foot | on the foot block | pin hinge each | Y |
| `act_hip/knee/ankle_top_*`, `_bot_*` | upper / lower segment | on the lugs | actuator halves, aimed at each other | local Z along the actuator |
| `shoulder_L` | pelvis | (2.6, 2.9, 23.3) | abduction pin | X |
| `upperarm_L` | shoulder | at the shoulder | shoulder drum | Y |
| `forearm_L` | upperarm | 7.0 m down | elbow | Y |
| `hand_L` | forearm | 6.8 m down | wrist: pitch hinge in a roll ring | Y pitch, Z roll |
| `finger_a1..c3_L` | hand / previous | on the palm, then 1.5 and 1.2 m down | pin hinges | Y (positive curls) |
| `act_elbow_top/bot_L` | upperarm / forearm | on the lugs | | |
| `neck_01..05` | pelvis, then chain | (3.6, 0, 24.2) rising to (5.7, 0, 28.3) | pin joints | Y pitch, Z yaw at 01 |
| `head_yaw` | neck_05 | (6.0, 0, 28.6) | bearing ring | Z |
| `head` | head_yaw | (6.0, 0, 28.9) | yoke pin | Y |
| `sensor` | head | (8.3, 0, 28.9) | socket for the light component | none |
| `ik_foot_root`, `ik_foot_*`, `ik_hand_root`, `ik_hand_L/R` | root | at the feet and wrists | UE IK targets, no meshes | |

Front legs fold knee-forward, rear legs knee-backward (mirror images), so a crouch spreads the knees fore and aft
and keeps the space under the belly clear.

## Animations

| Action | What |
|---|---|
| `A_Stilt_Walk` | slow careful walk in place, loop, 8 s: one foot at a time (rear-left, front-left, rear-right, front-right), each lifted high and placed like a heron's, body swaying over the three planted feet |
| `A_Stilt_Reach` | crouches about 6 m, tips forward, the left arm reaches to the ground, the hand opens and closes, stands again |
| `A_Stilt_HeadTurn` | lights off; the head lifts, the lights come on, it looks left and right and settles |
| build-up | render only (`render_stilt.py -- assembly`): the parts arrive feet first and the lights come on |

## Materials

`M_Stilt_Ceramic` (pale grey / off-white shell), `M_Stilt_Carbon` (black carbon beams and hull), `M_Stilt_Metal`
(dark graphite housings, brackets), `M_Stilt_Steel` (polished rods, pins, bolts), `M_Stilt_Cable` (braided tendons
and looms), `M_Stilt_Rubber` (toe pads, fingertips), `M_Stilt_Lens`, `M_Stilt_Emit_Sensor` (blue emissive, linear
about 0.03, 0.2, 1.0). Two baked texture sets on `UV_Atlas`: `stilt_ceramic_*` and `stilt_frame_*` (base colour
with ambient occlusion, ORM, normal). The four legs share one set of UV islands, as do the two arms and the left /
right shells, so the texel density is four times what a unique unwrap would give.

## Deviations from the concept and the turnaround, and why

1. **Clean, intact machine.** No moss, vines or dirt in the geometry: the dead one among the pylons is a set
   dressing and material job on top of this model.
2. **Tendons, spreaders and actuators on the legs** are added (see "How the thin legs carry 30 m"). The concept
   shows only a few thin cables; the close-up plates were drawn to design this.
3. **Three-segment leg with a slight zigzag.** The concept legs read as hip, knee, a low ankle and a small foot,
   nearly straight. Kept, but the knee and ankle are given real fold directions so it can crouch.
4. **Arms follow the concept, not the turnaround.** The turnaround shortened the arms (fingertips at 8.5 m). The
   concept has them reaching to about 4 m above the ground, and the reach-to-ground animation needs that length,
   so: 7.0 + 6.8 + 4.8 m, fingertips hanging at about 4.5 m.
5. **Three fingers.** The hand close-up drew four; the design says three.
6. **Three toes.** The foot close-up drew four radial toes; the design says three (two forward, one back).
7. **Six limbs, not the fused limbs of the left view.** Arms hang from their own shoulder drums above and outside
   the front hips.
8. **Front track narrower than the rear** (4.8 m against 8.4 m), read from the front view's inner and outer feet,
   so the arms can swing down past the front legs.
9. **Sensor lights in a bay on each side of the head plus three on the nose**, so the cluster shows from the
   front, the side and above. The concept only shows one side.
