# Seamless 1024 tiles for the Oil Rig V2 kit, from the generated sheets in gen/ (and two shared with rig 1).
#   blender -b --factory-startup --python rig2_blender/kit/_tex/tex.py
import bpy, os, numpy as np
D = os.path.dirname(os.path.abspath(__file__)); G = os.path.join(D, "gen"); O = os.path.join(D, "out"); os.makedirs(O, exist_ok=True)
R1 = os.path.join(D, "..", "..", "..", "dugout_blender", "props_hand", "_tex", "gen")
def load(p):
    im = bpy.data.images.load(p); w, h = im.size
    a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1].copy()
def save(a, n):
    h, w = a.shape[:2]; a = np.dstack([a, np.ones((h, w), np.float32)])
    im = bpy.data.images.new(n, w, h, alpha=True); im.pixels.foreach_set(np.ascontiguousarray(a[::-1], dtype=np.float32).ravel())
    im.filepath_raw = os.path.join(O, n); im.file_format = "PNG"; im.save(); bpy.data.images.remove(im)
def tile(p, n):
    a = load(p)[:, :, :3]; a = a[40:-40, 40:-40]          # the generator darkens its borders
    h, w = a.shape[:2]; s = np.roll(a, (h // 2, w // 2), (0, 1))
    y = np.abs(np.linspace(-1, 1, h))[:, None]; x = np.abs(np.linspace(-1, 1, w))[None, :]
    m = np.clip((1 - np.maximum(x, y)) / 0.25, 0, 1)[..., None]; m = m * m * (3 - 2 * m)
    r = (a * m + s * (1 - m))[:1920, :1920]
    save((r[0::2, 0::2] + r[1::2, 0::2] + r[0::2, 1::2] + r[1::2, 1::2]) / 4, n)
for n in sorted(os.listdir(G)):
    if n.endswith(".png"): tile(os.path.join(G, n), n)
for n in ("steel_galv.png", "rust_steel.png"):
    if os.path.exists(os.path.join(R1, n)): tile(os.path.join(R1, n), n)
print("tex done", sorted(os.listdir(O)))
