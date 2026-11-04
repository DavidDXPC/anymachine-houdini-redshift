#!/usr/bin/env bash
# Cycles GPU renders through the shared FIFO GPU queue: stills + walk loop -> mp4 + gif.
set -e
source /c/Users/apek-anna/Developer/anyscene/pipeline/env.sh
S=C:/Users/apek-anna/Developer/anymachine/spider; G=C:/Users/apek-anna/Developer/anyscene/builder/blender_gpu.py
Q=/c/Users/apek-anna/Developer/anyscene/pipeline/gpu_run.sh
R() { bash $Q "$BLENDER" -b --factory-startup --python $G --python $S/scripts/render.py -- --blend $S/out/spider.blend "$@" 2>&1 | grep -E "RENDERED|Error|Traceback" || true; }
rm -rf $S/out/stills $S/out/anim
R --out $S/out/stills --cam persp --frames 7 --samples 128 --resx 1600 --resy 900 --tag threequarter
R --out $S/out/stills --cam side --frames 7 --samples 96 --resx 1600 --resy 900
R --out $S/out/stills --cam joint --frames 7,13 --samples 96 --resx 1200 --resy 900
R --out $S/out/stills --cam persp --action crouch --frames 25 --samples 96 --resx 1600 --resy 900 --tag crouch
R --out $S/out/anim --cam walk --anim --samples 48 --resx 1280 --resy 720
cd $S/out
"$FFMPEG" -y -loglevel error -framerate 24 -i anim/f_%04d.png -c:v mpeg4 -q:v 2 -pix_fmt yuv420p spider_walk.mp4
"$FFMPEG" -y -loglevel error -framerate 24 -i anim/f_%04d.png -vf "fps=24,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer" spider_walk.gif
echo DONE
