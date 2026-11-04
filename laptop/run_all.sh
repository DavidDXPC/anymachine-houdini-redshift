#!/usr/bin/env bash
# AnyMachine experiment 1, end to end (after refs + gen/ exist): build -> check -> export -> stills -> anim -> mp4/gif
set -e
source /c/Users/apek-anna/Developer/anyscene/pipeline/env.sh
D=C:/Users/apek-anna/Developer/anymachine/laptop; G=C:/Users/apek-anna/Developer/anyscene/builder/blender_gpu.py
B() { "$BLENDER" -b --factory-startup "$@" 2>&1 | grep -E "BUILT|CHECK|EXPORTED|RENDERED|Error|Traceback" || true; }
B --python $D/scripts/build.py -- --glb $D/gen/tripo/model.glb --gen tripo --ui $D/refs/screen_ui_0.png --out $D/out/laptop.blend
B --python $D/scripts/check.py -- --blend $D/out/laptop.blend --out $D/out/check.json --step 1
B --python $D/scripts/export.py -- --blend $D/out/laptop.blend --out $D/out/laptop.glb
rm -rf $D/out/stills $D/out/anim
B --python $G --python $D/scripts/render.py -- --blend $D/out/laptop.blend --out $D/out/stills --stills 0,90,135 --samples 128 --resx 1600 --resy 900 --cam persp
B --python $G --python $D/scripts/render.py -- --blend $D/out/laptop.blend --out $D/out/stills --stills 0,90,135 --samples 96 --resx 1600 --resy 900 --cam side
B --python $G --python $D/scripts/render.py -- --blend $D/out/laptop.blend --out $D/out/stills --stills 0,45,90,135 --samples 64 --resx 1200 --resy 900 --cam hinge
B --python $G --python $D/scripts/render.py -- --blend $D/out/laptop.blend --out $D/out/anim --anim --samples 48 --resx 1280 --resy 720 --cam persp
cd /c/Users/apek-anna/Developer/anymachine/laptop/out
"$FFMPEG" -y -loglevel error -framerate 24 -i anim/f_%04d.png -c:v mpeg4 -q:v 2 -pix_fmt yuv420p laptop_hinge.mp4
"$FFMPEG" -y -loglevel error -framerate 24 -i anim/f_%04d.png -vf "fps=16,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer" laptop_hinge.gif
echo DONE
