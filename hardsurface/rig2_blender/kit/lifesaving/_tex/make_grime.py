# Stain textures for the lifesaving family, made from rig 1's rust streaks (sn_0k.png):
#   gr_00..05.png   dark grime versions, for orange paint (rust multiplied onto orange does not show)
#   gr_row.png      a strip of dark streaks hanging from its top edge (one projector instead of ten: a material holds
#   rr_row.png      about thirty projectors before Cycles runs out of shader stack); rr_ is the same strip in rust
#   blender -b --factory-startup --python make_grime.py
import bpy, os, random
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "..", "..", "dugout_blender", "props_hand", "_tex", "out")


def save(px, name):
    h, w = px.shape[:2]; o = bpy.data.images.new("g", w, h, alpha=True); o.pixels.foreach_set(px.astype(np.float32).ravel())
    o.filepath_raw = os.path.join(HERE, name); o.file_format = "PNG"; o.save(); print("wrote", name, w, h)


def dark(px):
    lum = px[..., :3].mean(axis=2); dens = np.clip(px[..., 3] * (1.15 - lum) * 2.2, 0, 1)      # dark where the rust was dense
    core = np.clip((dens - 0.55) * 2.5, 0, 1)[..., None]                                       # a little rust brown in the heart
    out = np.empty_like(px); out[..., :3] = (1 - core) * np.array([0.30, 0.27, 0.24]) + core * np.array([0.34, 0.17, 0.08])
    out[..., 3] = np.clip(dens * 1.25, 0, 1); return out


src = []
for k in range(6):
    im = bpy.data.images.load(os.path.join(SRC, "sn_0%d.png" % k)); w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(px); src.append(px.reshape(h, w, 4))
for k, px in enumerate(src): save(dark(px), "gr_0%d.png" % k)


def row(srcs, W, H, n, seed):
    """n streaks hanging from the top edge of a W x H strip (rows are bottom-up, as Blender stores them)."""
    rnd = random.Random(seed); out = np.zeros((H, W, 4), dtype=np.float32); out[..., :3] = 1.0
    for i in range(n):
        s = srcs[rnd.randrange(5)]; sh, sw = s.shape[:2]
        w = int(W * rnd.uniform(0.035, 0.07)); h = int(H * rnd.uniform(0.45, 1.0)); x0 = int((i + rnd.uniform(0.15, 0.85)) * W / n - w / 2)
        x0 = max(0, min(W - w, x0)); ys = (np.arange(h) * sh / h).astype(int); xs = (np.arange(w) * sw / w).astype(int)
        if rnd.random() < 0.5: xs = xs[::-1]
        t = s[ys][:, xs]; a = t[..., 3:4] * rnd.uniform(0.55, 1.0); dst = out[H - h:H, x0:x0 + w]
        dst[..., :3] = dst[..., :3] * (1 - a) + t[..., :3] * a; dst[..., 3:4] = np.maximum(dst[..., 3:4], a)
    return out


save(row(src, 4096, 400, 16, 7), "rr_row.png")
save(row([dark(s) for s in src], 4096, 400, 16, 7), "gr_row.png")
