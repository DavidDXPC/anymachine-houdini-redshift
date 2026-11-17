# lighting family: every fixture, ONE shared 2048 texture set (lighting_color|normal|orm.png in this folder).
#   blender -b --factory-startup -t 4 --python build.py -- [--nobake] [--size 2048] [--spp 24]
# Writes lighting.blend (all objects in a row) and, per fixture id, <id>/<id>.blend, <id>/<id>.glb, <id>/stats.json.
# Geometry of one fixture alone: blender ... --python <id>/build.py   (no bake, flat preview colours).
# The review (sheet beside lit and unlit renders) is _shared/review.py, run afterwards; it is not part of the bake.
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "_shared"))
import lkit
lkit.run(lkit.load_defs())
