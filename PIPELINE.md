# The reference-first pipeline

How a machine goes from one painting to a rigged, animated, exported model that is built entirely by a script.
[`stilt/`](stilt/NOTES.md) is the worked example; every file named below exists there.

This is written for two readers: a person who wants to know how the Stilt was made, and an agent that is asked to
build the next machine. The Stilt was built by an agent (Claude Fable 5.2 in Claude Code) working through these
steps, with a person choosing the design, approving each set of references and judging the result.

## The idea

A generator can give you a mesh of a machine, but not one whose joints work. A modeller can build working joints,
but needs to know what each one looks like up close. So the pipeline spends its effort on **references**: it turns
one concept image into the set of drawings a modeller would ask for, and only then writes geometry. Nothing is
modelled from a whole-body picture alone.

The model itself is code. One Python script builds every part, the materials, the UVs, the rig and the animations
when it is run in Blender. A change to the design is a change to the script, and the whole machine rebuilds.

## Steps

| # | Step | What is made | In `stilt/` |
|---|---|---|---|
| 1 | Concept | One painting of the machine in its world, with a person for scale | `refs/concept_sheet.png` |
| 2 | Turnaround | The same machine, clean, on grey: front, side, rear, top, three-quarter | `refs/stilt_turnaround.png`, `jobs_turnaround.json` |
| 3 | Single views | Each view on its own, large enough to measure | `refs/stilt_front / left / rear / top / 3q.png`, `jobs_views.json` |
| 4 | Close-up plates | One plate per mechanism, then three more angles of each | `refs/closeup_*.png`, `jobs_closeups.json`, `jobs_closeup_angles.json` |
| 5 | Parts breakdown | Scale, axes, dimensions, every part and bone, written before modelling | `PARTS.md` |
| 6 | Build script | Geometry, materials, UVs, bake, rig, actions, export | `build_stilt.py` |
| 7 | Check renders | The model framed like each reference, placed beside it | `render_stilt.py`, `renders/stilt_compare_*.jpg` |
| 8 | Motion reference | Short video-model clips made from renders of the model, read for timing | `refs/motion/`, `jobs_motion.json` |
| 9 | Animation | Actions written in the build script, checked for parts passing through each other | `render_stilt.py -- check` |
| 10 | Export and verify | GLB and FBX, re-imported into an empty scene and compared | `verify_glb.py` |

### 1 to 4: references

Each step feeds the one before it back in as an image reference, so the design does not drift:

- The **turnaround** is generated from the concept plus crops of it.
- The **single views** are generated from the turnaround plus the concept.
- Each **close-up plate** is generated from the side view, the front view, the turnaround and the concept. The
  prompt asks for a studio product render of one area "for a 3D modeller", with every part "readable and physically
  plausible as real heavy engineering", on flat grey, no labels.

Rules that made the references usable:

- **One plate per mechanism, not per body area.** Hip, knee, foot, hand, head, shoulder, elbow. Then front, rear and
  inner or top angles of each, because a joint cannot be modelled from one side.
- **Approve before going on.** A person looks at each set. A wrong turnaround makes every later image wrong.
- **Say the scale in the prompt** ("a joint housing is 1.5 to 2.5 m across"), or the plates come back with details
  sized for a toy.
- **Keep the prompts.** The `jobs_*.json` files are the record of how each image was asked for; `edit.ps1` runs them.

The images here were made with GPT Image 2.6 on fal. Any image model that accepts reference images will do.

### 5: parts breakdown

Written before any geometry, from measurements taken off the single views (pixels per metre, where the ground and
the top are, where each joint sits). It fixes:

- the axes and the origin;
- overall dimensions and the size of every joint housing;
- **how the machine carries its own weight.** For the Stilt this was the decision to build each leg as a guyed mast
  (a compression beam, tension cables on spreaders, an actuator across each joint). This is what makes thin legs
  believable, and it came from asking the question, not from the references;
- the part list with the bone each part rides on;
- where the views disagree and which one wins.

### 6: build script

One file, run headless. In order: a solver for the limb poses, part builders, instancing of the repeated limbs,
materials, UV layouts, a texture bake, the armature, skinning (every rigid part to exactly one bone), the actions,
export. Habits worth copying:

- **Every joint is a real mechanism**: fork and tongue on a pin, a drum with a bolted flange, a two-part hydraulic
  cylinder whose halves are on their own bones and aim at each other.
- **Let the script pick what a person would fudge.** The actuator anchor points are chosen by sampling every action
  and keeping the points where the rod stays inside its cylinder over the whole stroke with the largest lever arm.
  The build fails if a rod could leave its cylinder.
- **Assert the rules.** No mesh shares a name with a bone; the bake is refused if the topology changed.
- **Write the numbers out.** `stilt_info.json` holds every part, bone, rest axis and stroke for whoever imports it.

### 7: check renders

`render_stilt.py` renders the model from the camera of each reference, and the comparison images put reference and
model side by side. This is the step that keeps the build honest: differences are listed in the notes
("What differs from the references") instead of being left for someone to find.

### 8 and 9: motion

A 30 m machine has no motion capture. Renders of the finished model are given to an image-to-video model with a
prompt for the movement ("like a giraffe or a heron filmed in slow motion"). The clips are **read, not tracked**:
frame strips show the order of the feet, how long each is in the air, when the body dips. Those timings go into the
actions in the build script. The first walk moved one foot at a time; the clips showed overlapping steps, and the
walk was rewritten.

After every animation change, the clash check compares every part against every part on another bone through all
actions and reports any intersection that is not there in the rest pose.

### 10: export and verify

The GLB and FBX are re-imported into empty scenes and counted: bones, meshes, actions and their lengths. The GLB is
rendered on its own, so what a plain viewer shows is known.

## Building the next machine

1. Make a folder beside `stilt/` and copy `edit.ps1`, `video.ps1` and the `jobs_*.json` files as templates. Rewrite
   the prefix of each jobs file to describe the new machine.
2. Do steps 1 to 4, stopping for approval after the turnaround and after the first plates.
3. Write `PARTS.md`. Do not start the script until the load path and the joint types are decided.
4. Write the build script. Reuse the solver, the actuator anchor search, the bake and the export from
   `build_stilt.py`; the part builders are specific to each machine.
5. Render the comparisons, list the differences, fix or accept each one.
6. Motion reference, actions, clash check, export, verify.

## What it costs

This is not one prompt. The Stilt has 40 reference images, each generated from the ones before it and looked at by
a person, a build script of about 2,200 lines, and some 40 check and comparison renders. It was the fourth machine
built this way, and the steps above are what survived from the first three. What generalises is the order of work
and the checks, and the parts of the script named in step 4 above.

## Needs

- Blender 5.2 (5.0 runs the older experiments in this repo).
- `FAL_KEY` in the environment, only for regenerating references and motion clips. Building, rendering and
  verifying need no network.
- ffmpeg, for the videos.
