# compose.py: each final still beside the reference sheet it was built from -> rig2_blender/out/helicopter/.
#   blender -b --factory-startup --python compose.py          (image work only, seconds; no rendering)
import bpy, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REN = os.path.join(HERE, "renders"); SH = os.path.join(HERE, "sheets")
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "out", "helicopter")); os.makedirs(OUT, exist_ok=True)
SHEET = {"side_left": "heli_turn", "side_right": "heli_turn", "front": "heli_turn", "rear": "heli_turn", "q_front_left": "heli_turn",
         "q_rear_right": "heli_ortho", "eye_front_left": "heli_ortho", "eye_side": "heli_ortho", "eye_rear_right": "heli_ortho", "eye_cabin": "heli_close7_interior",
         "c_rotor": "heli_close1_rotor", "c_tail": "heli_close2_tail", "c_cowl": "heli_close3_engines", "c_exhaust": "heli_close3_engines",
         "c_door": "heli_close4_doors", "c_nose": "heli_close6_fittings", "c_gear": "heli_close5_gear", "c_cockpit": "heli_close7_interior", "c_secured": "heli_close8_secured"}
sc = bpy.context.scene; sc.view_settings.view_transform = "Standard"; sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 88
def load(p):
    im = bpy.data.images.load(p); w, h = im.size; a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)
    if im.channels == 3: a = np.concatenate([a, np.ones((h, w, 1), np.float32)], 2)
    bpy.data.images.remove(im); return a
def fit(a, H):
    h, w = a.shape[:2]; W = int(round(w * H / h)); return a[(np.arange(H) * h / H).astype(int)][:, (np.arange(W) * w / W).astype(int)]
def save(a, p):
    a = a.copy(); a[..., 3] = 1; o = bpy.data.images.new("o", a.shape[1], a.shape[0], alpha=False); o.pixels.foreach_set(a.ravel()); o.save_render(p, scene=sc); bpy.data.images.remove(o)
cache = {}; n = 0
for look in ("clay", "tex"):
    for view, sheet in SHEET.items():
        p = os.path.join(REN, f"{look}_{view}.jpg")
        if not os.path.exists(p): print("missing", p); continue
        r = load(p); H = 900; r = fit(r, H)
        if sheet not in cache: cache[sheet] = fit(load(os.path.join(SH, sheet + ".png")), H)
        bar = np.ones((H, 10, 4), np.float32) * np.array([0.9, 0.2, 0.1, 1], np.float32)
        save(np.concatenate([r, bar, cache[sheet]], 1), os.path.join(OUT, f"{look}_{view}__beside_{sheet}.jpg")); n += 1
# one overview: the four sides and the eye-level views, clay over textured
rows = []
for look in ("clay", "tex"):
    cells = [fit(load(os.path.join(REN, f"{look}_{v}.jpg")), 450) for v in ("side_left", "front", "side_right", "rear", "eye_front_left", "eye_rear_right") if os.path.exists(os.path.join(REN, f"{look}_{v}.jpg"))]
    if len(cells) == 6: rows.append(np.concatenate(cells[3:], 1)); rows.append(np.concatenate(cells[:3], 1))
if len(rows) == 4: save(np.concatenate([rows[2], rows[3], rows[0], rows[1]], 0), os.path.join(OUT, "overview_clay_top_textured_bottom.jpg"))
print("composed", n, "pairs in", OUT)
