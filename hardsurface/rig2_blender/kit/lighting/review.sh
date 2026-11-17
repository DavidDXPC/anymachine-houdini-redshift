#!/bin/sh
# Review after a bake: renders the cells and composes <id>/review.jpg and review_family.jpg.   sh review.sh [id ...]
D="$(cd "$(dirname "$0")" && pwd)"
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -t 4 --python "$D/_shared/review_render.py" -- "$@" 2>&1 | grep -E "Error|Traceback|line [0-9]+"
uv run --python 3.13 --with pillow python "$D/_shared/review_compose.py" "$@" 2>&1 | tail -1
