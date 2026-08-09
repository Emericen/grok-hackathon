#!/usr/bin/env python3
# REFERENCE IMPLEMENTATION — reuse the degradation profiles (flatbed/photocopy/phone),
# not the hardcoded paths/PROFILE table, which belong to the project this came from.
# Degrades the clean PDFs into shoebox realism. Three conditions:
#   flatbed   — slight rotation, paper tone, sensor noise, mid JPEG quality
#   photocopy — grayscale gen-2 copy: blur, harsh contrast, edge band, heavy noise
#   phone     — photographed on a desk: perspective, rotation, warm cast, vignette
# Output filenames mimic how a real client names files (IMG_xxxx, "bank stmt jan").
import os, random, subprocess, glob
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageOps

OUT = os.path.expanduser("~/Desktop/workfile/openmnk/gtm/data/demo-case")
CLEAN, WORK, BOX = f"{OUT}/clean", f"{OUT}/work", f"{OUT}/shoebox"
random.seed(20260720)

PROFILE = {
    "01-cp2000":      ("flatbed",   "IRS letter 1.pdf"),
    "02-1099k":       ("flatbed",   "1099K clover.pdf"),
    "03-return-2024": ("photocopy", "scan0007.pdf"),
    "03-bank-jan":    ("flatbed",   "bank stmt jan.pdf"),
    "04-bank-feb":    ("flatbed",   "bank stmt feb.pdf"),
    "05-bank-mar":    ("phone",     "IMG_5203.pdf"),
    "06-bank-apr":    ("flatbed",   "bank stmt april.pdf"),
    "07-bank-may":    ("phone",     "IMG_5209.pdf"),
    "08-bank-jun":    ("flatbed",   "bank june.pdf"),
    "10-pnl-2024":    ("clean",     "P&L 2024 QuickBooks.pdf"),
    "11-receipts":    ("phone",     "IMG_5217.pdf"),
    "12-note-danny":  ("phone",     "IMG_5222.jpg"),
    "13-cp504":       ("photocopy", "scan0002.pdf"),
}

def noise_layer(size, opacity):
    n = Image.effect_noise(size, 64).convert("L")
    return n.point(lambda p: int(p * opacity))

def flatbed(img):
    img = img.rotate(random.uniform(-1.1, 1.1), expand=True, fillcolor=(246, 244, 238))
    tone = Image.new("RGB", img.size, (250, 248, 240))
    img = Image.blend(img, tone, 0.06)
    img = Image.composite(Image.new("RGB", img.size, (110, 110, 110)), img, noise_layer(img.size, 0.10))
    img = ImageEnhance.Contrast(img).enhance(random.uniform(0.95, 1.05))
    img = ImageEnhance.Brightness(img).enhance(random.uniform(0.96, 1.02))
    return img

def photocopy(img):
    img = ImageOps.grayscale(img)
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    img = ImageEnhance.Contrast(img).enhance(1.35)
    img = img.rotate(random.uniform(-1.8, 1.8), expand=True, fillcolor=235)
    img = Image.composite(Image.new("L", img.size, 70), img, noise_layer(img.size, 0.16))
    d = ImageDraw.Draw(img, "L")
    edge = random.randint(10, 26)
    d.rectangle([img.width - edge, 0, img.width, img.height], fill=60)   # copier edge band
    band_y = random.randint(int(img.height * .35), int(img.height * .65))
    shadow = Image.new("L", img.size, 0)
    ImageDraw.Draw(shadow).polygon([(0, band_y), (img.width, band_y - 60), (img.width, band_y - 20), (0, band_y + 40)], fill=28)
    img = Image.composite(img.point(lambda p: max(0, p - 30)), img, shadow.filter(ImageFilter.GaussianBlur(14)))
    return img.convert("RGB")

def phone(img):
    w, h = img.size
    desk = Image.new("RGB", (int(w * 1.18), int(h * 1.14)), (94, 72, 52))
    grain = noise_layer(desk.size, 0.25)
    desk = Image.composite(Image.new("RGB", desk.size, (70, 52, 36)), desk, grain)
    j = lambda s: random.randint(-s, s)
    # PIL QUAD order: upper-left, lower-left, lower-right, upper-right (of the source)
    q = [(j(28) + 30, j(22) + 26), (26 + j(26), h - 20 + j(26)), (w - 22 + j(30), h - 26 + j(24)), (w - 30 + j(28), 20 + j(22))]
    img = img.transform((w, h), Image.QUAD, sum(q, ()), resample=Image.BICUBIC, fillcolor=(94, 72, 52))
    img = img.rotate(random.uniform(-3.5, 3.5), expand=True, fillcolor=(94, 72, 52))
    desk.paste(img, ((desk.width - img.width) // 2, (desk.height - img.height) // 2))
    warm = Image.new("RGB", desk.size, (255, 236, 200))
    desk = Image.blend(desk, warm, 0.07)
    vig = Image.new("L", desk.size, 0)
    ImageDraw.Draw(vig).ellipse([-desk.width // 3, -desk.height // 3, desk.width * 4 // 3, desk.height * 4 // 3], fill=255)
    vig = ImageOps.invert(vig.filter(ImageFilter.GaussianBlur(120))).point(lambda p: int(p * 0.5))
    desk = Image.composite(Image.new("RGB", desk.size, (20, 14, 8)), desk, vig)
    return desk

def process(stem, mode, outname):
    src = f"{CLEAN}/{stem}.pdf"
    if mode == "clean":
        subprocess.run(["cp", src, f"{BOX}/{outname}"])
        print(f"  {outname} (untouched digital)")
        return
    os.makedirs(WORK, exist_ok=True)
    for f in glob.glob(f"{WORK}/{stem}*"): os.remove(f)
    subprocess.run(["pdftoppm", "-r", "150", "-png", src, f"{WORK}/{stem}"], check=True)
    pages = sorted(glob.glob(f"{WORK}/{stem}*.png"))
    jpgs = []
    for p in pages:
        img = Image.open(p).convert("RGB")
        img = {"flatbed": flatbed, "photocopy": photocopy, "phone": phone}[mode](img)
        jp = p.replace(".png", ".jpg")
        img.save(jp, quality=random.randint(58, 74))
        jpgs.append(jp)
    if outname.endswith(".jpg"):
        subprocess.run(["cp", jpgs[0], f"{BOX}/{outname}"])
        print(f"  {outname} ({mode}, bare photo)")
        return
    subprocess.run(["img2pdf", "-o", f"{BOX}/{outname}", *jpgs], check=True)
    print(f"  {outname} ({mode}, {len(jpgs)}pp)")

os.makedirs(BOX, exist_ok=True)
for stem, (mode, outname) in PROFILE.items():
    process(stem, mode, outname)
print("shoebox ->", BOX)
