# Draws the family's small decal images (invented maker's plates, the invented escape pictogram, lens interiors).
#   uv run --python 3.13 --with pillow python make_decals.py      (writes decal_*.png beside this file; run once)
import os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
H = os.path.dirname(os.path.abspath(__file__)); rnd = random.Random(3)
def font(s): return ImageFont.load_default(size=s)

def plate(name, maker, lines):
    W, Ht = 512, 300; im = Image.new("RGBA", (W, Ht), (176, 178, 176, 255)); d = ImageDraw.Draw(im)
    for y in range(Ht):                      # brushed
        v = 170 + rnd.randint(-7, 7); d.line([(0, y), (W, y)], fill=(v, v + 1, v - 1, 255))
    d.rectangle([6, 6, W - 7, Ht - 7], outline=(40, 40, 40, 255), width=4)
    d.rectangle([20, 20, W - 21, 86], fill=(34, 36, 38, 255))
    d.text((W // 2, 53), maker, font=font(40), fill=(200, 202, 200, 255), anchor="mm")
    y = 104
    for t in lines:
        d.text((30, y), t, font=font(30), fill=(30, 30, 30, 255)); d.line([(26, y + 40), (W - 26, y + 40)], fill=(70, 70, 70, 255), width=2); y += 46
    im.filter(ImageFilter.GaussianBlur(0.6)).save(os.path.join(H, name))

plate("decal_plate_a.png", "NORHAVN ELEKTRO", ["TYPE  WG 60     Ex d IIB T4", "IP66    230 V    60 W", "SER  04471      1998", "STAVNES  WORKS"])
plate("decal_plate_b.png", "KELDA MARINE LTG", ["TYPE  FL 400    Ex de IIC T3", "IP67    230 V    400 W", "SER  118203     2004", "TA  -30 / +45 C"])
plate("decal_plate_c.png", "ORMEN SIGNAL A/S", ["TYPE  RB 2      Ex d IIB T5", "IP66    24 V DC   25 W", "SER  7 0932     2001", "60 / 120 FLASH MIN"])

# escape sign: an invented pictogram (a figure striding to a doorway, three chevrons), white on transparent
W, Ht = 1024, 512; im = Image.new("RGBA", (W, Ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im); Wt = (236, 240, 232, 255)
d.rectangle([40, 40, W - 41, Ht - 41], outline=Wt, width=10)
d.rectangle([110, 96, 330, 416], fill=Wt)                      # doorway panel
G = (0, 0, 0, 0)
def limb(p, q, w=34): d.line([p, q], fill=G, width=w); d.ellipse([p[0] - w // 2, p[1] - w // 2, p[0] + w // 2, p[1] + w // 2], fill=G); d.ellipse([q[0] - w // 2, q[1] - w // 2, q[0] + w // 2, q[1] + w // 2], fill=G)
d.ellipse([222, 112, 274, 164], fill=G)                         # head (cut out of the panel)
limb((238, 182), (206, 276), 44); limb((206, 276), (262, 330)); limb((262, 330), (236, 400)); limb((206, 276), (150, 318)); limb((150, 318), (128, 380))
limb((238, 190), (292, 226), 26); limb((292, 226), (318, 196), 26); limb((232, 192), (176, 214), 26); limb((176, 214), (160, 258), 26)
for k in range(3):                                              # chevrons
    x = 430 + k * 170
    d.polygon([(x, 136), (x + 60, 136), (x + 150, 256), (x + 60, 376), (x, 376), (x + 90, 256)], fill=Wt)
im.save(os.path.join(H, "decal_exit.png"))

# flood lens interior: stippled glass over a faceted reflector with a lamp capsule
S = 512; im = Image.new("RGBA", (S, S), (150, 152, 150, 255)); d = ImageDraw.Draw(im); c = S // 2; a, bq = 236, 70
d.polygon([(c - a, c - a), (c + a, c - a), (c + bq * 2, c - bq), (c - bq * 2, c - bq)], fill=(196, 198, 196, 255))
d.polygon([(c - a, c + a), (c + a, c + a), (c + bq * 2, c + bq), (c - bq * 2, c + bq)], fill=(120, 123, 122, 255))
d.polygon([(c - a, c - a), (c - bq * 2, c - bq), (c - bq * 2, c + bq), (c - a, c + a)], fill=(160, 162, 160, 255))
d.polygon([(c + a, c - a), (c + bq * 2, c - bq), (c + bq * 2, c + bq), (c + a, c + a)], fill=(142, 145, 144, 255))
d.rectangle([c - bq * 2, c - bq, c + bq * 2, c + bq], fill=(104, 106, 104, 255))
d.rounded_rectangle([c - 100, c - 20, c + 100, c + 20], radius=20, fill=(226, 224, 210, 255), outline=(90, 90, 86, 255), width=3)
d.rectangle([c - 128, c - 12, c - 100, c + 12], fill=(70, 70, 68, 255)); d.rectangle([c + 100, c - 12, c + 128, c + 12], fill=(70, 70, 68, 255))
px = im.load()
for _ in range(26000):
    x, y = rnd.randrange(S), rnd.randrange(S); r, g, b_, _a = px[x, y]; k = rnd.randint(-22, 26); px[x, y] = (max(0, min(255, r + k)), max(0, min(255, g + k)), max(0, min(255, b_ + k)), 255)
im.filter(ImageFilter.GaussianBlur(1.2)).save(os.path.join(H, "decal_flood.png"))

# tube fitting interior: white gear tray, two tubes with end caps and lamp holders (seen through the diffuser)
W, Ht = 1536, 192; im = Image.new("RGBA", (W, Ht), (188, 190, 186, 255)); d = ImageDraw.Draw(im)
for cy in (62, 130):
    d.rectangle([40, cy - 26, 86, cy + 26], fill=(214, 214, 208, 255)); d.rectangle([W - 86, cy - 26, W - 40, cy + 26], fill=(214, 214, 208, 255))
    d.rounded_rectangle([86, cy - 19, W - 86, cy + 19], radius=8, fill=(244, 244, 238, 255))
    d.rectangle([86, cy - 19, 112, cy + 19], fill=(150, 150, 146, 255)); d.rectangle([W - 112, cy - 19, W - 86, cy + 19], fill=(150, 150, 146, 255))
    d.line([(112, cy - 13), (W - 112, cy - 13)], fill=(255, 255, 252, 255), width=4); d.line([(112, cy + 16), (W - 112, cy + 16)], fill=(206, 206, 200, 255), width=4)
    d.rectangle([112, cy - 19, 150, cy + 19], fill=(206, 200, 188, 255)); d.rectangle([W - 150, cy - 19, W - 112, cy + 19], fill=(206, 200, 188, 255))
for x in range(0, W, 12): d.line([(x, 0), (x, Ht)], fill=(170, 172, 168, 70), width=1)      # diffuser ribs
im.filter(ImageFilter.GaussianBlur(0.8)).save(os.path.join(H, "decal_tubes.png"))
print("decals written")
