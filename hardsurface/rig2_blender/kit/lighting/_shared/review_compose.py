# review_compose.py: puts the cells from review_render.py beside each reference sheet -> <id>/review.jpg, and all
# objects (off above on) into the family contact sheet review_family.jpg.
#   uv run --python 3.13 --with pillow python review_compose.py [id ...]
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); FAM = os.path.abspath(os.path.join(HERE, "..")); SHEETS = os.path.join(FAM, "..", "sheets")
IDS = ["wellglass", "tube_light", "flood", "obstruction_light", "helideck_lights", "escape_route", "beacon", "work_light"]
F = lambda s: ImageFont.load_default(size=s)
CW, CH = 720, 600


def cell(path, label, w=CW, h=CH):
    im = Image.open(path).convert("RGB").resize((w, h), Image.LANCZOS) if os.path.exists(path) else Image.new("RGB", (w, h), (90, 20, 20))
    d = ImageDraw.Draw(im); d.rectangle([0, 0, w, 26], fill=(20, 20, 22)); d.text((8, 3), label, font=F(18), fill=(235, 235, 235))
    return im


def review(fid):
    st = json.load(open(os.path.join(FAM, fid, "stats.json"))); rv = os.path.join(FAM, "_rv", fid); names = list(st["items"])
    rows = [[cell(os.path.join(rv, f"_{t}.png"), f"{t} (lamp off)") for t in ("front", "side", "back", "top")]]
    cur = []
    for n in names:
        it = st["items"][n]
        cur.append(cell(os.path.join(rv, f"{n}_off.png"), f"{n}  off  {it['tris']} tris"))
        cur.append(cell(os.path.join(rv, f"{n}_on.png"), f"{n}  on  {it.get('mount', '')}"))
        if len(cur) == 4: rows.append(cur); cur = []
    if cur: rows.append(cur + [Image.new("RGB", (CW, CH), (60, 60, 62))] * (4 - len(cur)))
    H = CH * len(rows); W = CW * 4
    grid = Image.new("RGB", (W, H)); [grid.paste(c, (i * CW, j * CH)) for j, r in enumerate(rows) for i, c in enumerate(r)]
    sh = Image.open(os.path.join(SHEETS, f"{fid}_turn.png")).convert("RGB"); sw = W; shh = int(sh.height * sw / sh.width); sh = sh.resize((sw, shh), Image.LANCZOS)
    out = Image.new("RGB", (W, shh + 40 + H), (200, 50, 30)); out.paste(sh, (0, 0)); out.paste(grid, (0, shh + 40))
    d = ImageDraw.Draw(out); d.text((10, shh + 6), f"{fid}: reference sheet above, baked model below ({'baked ' + str(st.get('texture')) if st.get('baked') else 'NOT baked: flat preview colours'})", font=F(24), fill=(255, 255, 255))
    out.save(os.path.join(FAM, fid, "review.jpg"), quality=88); print("review", fid, out.size)


def family():
    cw, ch = 360, 300; cells = []
    for fid in IDS:
        p = os.path.join(FAM, fid, "stats.json")
        if not os.path.exists(p): continue
        st = json.load(open(p))
        for n, it in st["items"].items():
            c = Image.new("RGB", (cw, ch * 2 + 44), (24, 24, 26)); rv = os.path.join(FAM, "_rv", fid)
            for k, s in enumerate(("off", "on")):
                q = os.path.join(rv, f"{n}_{s}.png")
                if os.path.exists(q): c.paste(Image.open(q).convert("RGB").resize((cw, ch), Image.LANCZOS), (0, k * ch))
            d = ImageDraw.Draw(c); d.text((6, ch * 2 + 2), n, font=F(18), fill=(240, 240, 240))
            d.text((6, ch * 2 + 23), f"{it['tris']} tris, {it.get('mount', '')[:22]}", font=F(14), fill=(170, 170, 170)); cells.append(c)
    cols = 7; rows = -(-len(cells) // cols); out = Image.new("RGB", (cols * cw, rows * (ch * 2 + 44)), (24, 24, 26))
    for i, c in enumerate(cells): out.paste(c, ((i % cols) * cw, (i // cols) * (ch * 2 + 44)))
    out.save(os.path.join(FAM, "review_family.jpg"), quality=88); print("family", out.size, len(cells), "objects")


ids = sys.argv[1:] or IDS
for fid in ids: review(fid)
family()
