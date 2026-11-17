# render.py: the final stills, run after build.py in the same farm job (Cycles, the worker's GPU; nothing here is run
# on the local PC).  Clay from the bake source (every part and bake-only detail), textured from the baked game meshes.
# Writes renders/clay_<view>.jpg and renders/tex_<view>.jpg beside this file.
#   blender -b --factory-startup --python render.py
import bpy, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import shots
OUT = os.path.join(HERE, "renders")
MAIN = ["side_left", "side_right", "front", "rear", "q_front_left", "q_rear_right", "eye_front_left", "eye_side", "eye_rear_right", "eye_cabin"]
CLOSE = ["c_rotor", "c_tail", "c_gear", "c_nose", "c_cowl", "c_cockpit", "c_door", "c_exhaust", "c_secured"]
A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "tex" not in A:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "helicopter_hi.blend"))
    shots.run(OUT, "clay", "clay", "cycles", True, MAIN + CLOSE, res=(1920, 1080), spp=64)
if "clay" not in A:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "helicopter.blend"))
    shots.run(OUT, "tex", "tex", "cycles", False, MAIN + CLOSE, res=(1920, 1080), spp=128)
