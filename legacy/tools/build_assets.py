#!/usr/bin/env python
"""Build the 大肥鱼 mascot assets for the dsh-fat-fish-widget plugin.

Inputs : assets/source-original.png (354x363 screenshot crop, white bg + UI chrome)
Outputs: assets/fish.png        transparent cutout, trimmed + 8px padding, long edge <= 360
         assets/fish-icon.png   256x256 square plugin icon
         assets/fish.b64.txt    single-line base64 of fish.png
         icon.png               copy of fish-icon.png at the package root
         tools/qa_*.png         QA composites (not shipped)

Run:  <bundled python> tools/build_assets.py
"""
import base64
import os
import shutil
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SRC = os.path.join(PKG, "assets", "source-original.png")
ASSETS = os.path.join(PKG, "assets")
QA = HERE

BG_MIN = 225      # min channel at/above this may be background
BG_CHROMA = 30    # max-min at/below this counts as neutral (background is white/grey)
PAD = 8           # transparent padding around the trimmed character
MAX_LONG = 360    # long edge cap for fish.png
S_ICON = 256      # icon canvas size


# ----------------------------------------------------------------- helpers
def flood_bg(cand):
    """4-connected flood fill of `cand` from every border pixel."""
    h, w = cand.shape
    out = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if cand[y, x] and not out[y, x]:
                out[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if cand[y, x] and not out[y, x]:
                out[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True
                dq.append((ny, nx))
    return out


def label(mask):
    """8-connected component labelling, returns (labels, sizes) with labels 0 = none."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    sizes = [0]
    cur = 0
    for y0 in range(h):
        for x0 in range(w):
            if mask[y0, x0] and lab[y0, x0] == 0:
                cur += 1
                lab[y0, x0] = cur
                dq = deque([(y0, x0)])
                n = 0
                while dq:
                    y, x = dq.popleft()
                    n += 1
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and lab[ny, nx] == 0:
                                lab[ny, nx] = cur
                                dq.append((ny, nx))
                sizes.append(n)
    return lab, sizes


def erode(mask, iters=1):
    """Binary erosion with 4-neighbourhood; image border counts as inside."""
    m = mask.copy()
    for _ in range(iters):
        p = np.pad(m, 1, constant_values=True)
        m = (p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    return m


def nearest_colour(pix, mask, target, rounds=3):
    """Propagate colours from `mask` into `target` (8-neighbour iterative fill)."""
    col = np.zeros(pix.shape, np.float32)
    known = mask.copy()
    col[known] = pix[known]
    todo = target & ~known
    for _ in range(rounds):
        if not todo.any():
            break
        acc = np.zeros(pix.shape, np.float32)
        cnt = np.zeros(pix.shape[:2], np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                sh = np.roll(np.roll(col, dy, axis=0), dx, axis=1)
                shm = np.roll(np.roll(known, dy, axis=0), dx, axis=1)
                if dy == 1:
                    sh[0] = 0; shm[0] = False
                elif dy == -1:
                    sh[-1] = 0; shm[-1] = False
                if dx == 1:
                    sh[:, 0] = 0; shm[:, 0] = False
                elif dx == -1:
                    sh[:, -1] = 0; shm[:, -1] = False
                acc += sh * shm[..., None]
                cnt += shm
        fill = todo & (cnt > 0)
        if not fill.any():
            break
        col[fill] = acc[fill] / cnt[fill][:, None]
        known |= fill
        todo &= ~fill
    return col, known


# ----------------------------------------------------------------- cutout
def build_cutout():
    im = Image.open(SRC).convert("RGB")
    arr = np.asarray(im).astype(np.float32)
    h, w, _ = arr.shape
    mn = arr.min(axis=2)
    mx = arr.max(axis=2)

    # 1. background = near-white / near-neutral light, border-connected
    bg = flood_bg((mn >= BG_MIN) & ((mx - mn) <= BG_CHROMA))
    fg = ~bg

    # 2. keep only the character component (largest)
    lab, sizes = label(fg)
    keep = int(np.argmax(sizes))          # sizes[0] == 0 (background label)
    char = lab == keep
    print("component kept: id=%d px=%d  (other comps=%d)" % (keep, sizes[keep], len(sizes) - 2))

    # 3. explicit UI chrome removal (all outside the character silhouette)
    ui = np.zeros_like(char)
    ui[:10, :] = True                       # grey/dark fragments on the top edge
    ui[8:70, 40:106] = True                 # dark-blue hamburger button (top-left)
    # horizontal 1px divider + its soft shadow (rows ~33..47, right of the head)
    zy, zx = slice(33, 47), slice(150, w)
    neutral_bright = ((mx - mn) <= 10) & (mn >= 190)
    ui[zy, zx] |= neutral_bright[zy, zx]
    char &= ~ui
    print("UI px cleared: %d" % ui.sum())

    # 4. soft alpha only on the 2px silhouette ring, using the *interior* colour
    interior = erode(char, 2)
    ring = char & ~interior
    print("ring px: %d" % ring.sum())
    col_in, _ = nearest_colour(arr, interior, ring, rounds=3)
    rgb = col_in.copy()
    rgb[char & ~ring] = arr[char & ~ring]

    denom = 255.0 - rgb
    num = 255.0 - arr
    good = (denom >= 18.0) & ring[..., None]
    wsum = (denom * good).sum(axis=2)
    nsum = (num * good).sum(axis=2)
    alpha = np.ones((h, w), np.float32)
    ok = ring & (wsum > 0)
    alpha[ok] = np.clip(nsum[ok] / wsum[ok], 0.0, 1.0)
    # pixels of the ring whose surrounding foreground is (nearly) white: keep opaque
    alpha[ring & ~ok] = 1.0
    alpha[~char] = 0.0

    # 5. colour bleed so filtering/zooming cannot pull in white/dark fringes
    near, known = nearest_colour(rgb, char, ~char, rounds=8)
    rgb_full = rgb.copy()
    bgpix = ~char
    rgb_full[bgpix] = near[bgpix]
    # far background pixels do not matter (alpha 0); give them white
    rgb_full[~char & ~known] = 255.0

    out = np.dstack([np.clip(rgb_full, 0, 255), np.clip(alpha * 255.0 + 0.5, 0, 255)]).astype(np.uint8)
    cut = Image.fromarray(out, "RGBA")

    # 6. trim to visible content, then pad
    a = out[..., 3]
    ys, xs = np.nonzero(a > 4)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    print("content bbox:", box, "size:", (box[2] - box[0], box[3] - box[1]))
    cut = cut.crop(box)
    pm = Image.new("RGBA", (cut.width + 2 * PAD, cut.height + 2 * PAD), (255, 255, 255, 0))
    # copy also the bleed colour of the padding area? flat white is fine at alpha 0
    pm.paste(cut, (PAD, PAD), cut)
    # re-bleed padding edges so downscales stay clean
    pa = np.asarray(pm).astype(np.float32)
    pmask = pa[..., 3] > 0
    pb, pknown = nearest_colour(pa[..., :3], pmask, ~pmask, rounds=16)
    pa[..., :3][~pmask] = pb[~pmask]
    pa[..., :3][~pmask & ~pknown] = 255.0
    pa[..., 3] = np.where(pmask, pa[..., 3], 0)
    pm = Image.fromarray(np.clip(pa, 0, 255).astype(np.uint8), "RGBA")

    # 7. cap the long edge
    if max(pm.size) > MAX_LONG:
        s = MAX_LONG / max(pm.size)
        pm = pm.resize((max(1, round(pm.width * s)), max(1, round(pm.height * s))), Image.LANCZOS)
        print("resized to", pm.size)
    return pm


# ----------------------------------------------------------------- icon
def build_icon(cut):
    """256x256 rounded-square icon: pastel gradient, mascot fills the width so the
    source's native bottom crop runs off the canvas (no floating cut line)."""
    S = S_ICON
    top, bot = np.array([238, 243, 255], np.float32), np.array([197, 214, 248], np.float32)
    grad = np.linspace(top, bot, S).astype(np.uint8)
    gimg = Image.fromarray(np.repeat(grad[:, None, :], S, axis=1), "RGB").convert("RGBA")
    hi = Image.new("L", (S, S), 0)
    ImageDraw.Draw(hi).ellipse((-80, -130, 230, 130), fill=80)
    hi = hi.filter(ImageFilter.GaussianBlur(55))
    gimg = Image.composite(Image.new("RGBA", (S, S), (255, 255, 255, 255)), gimg, hi)
    # soft cool shade at the very bottom for depth
    shade = Image.new("L", (S, S), 0)
    ImageDraw.Draw(shade).ellipse((-40, 200, S + 40, 340), fill=40)
    shade = shade.filter(ImageFilter.GaussianBlur(30))
    gimg = Image.composite(Image.new("RGBA", (S, S), (120, 145, 205, 255)), gimg, shade)

    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=54, fill=255)
    icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    icon.paste(gimg, (0, 0), mask)

    # character: crop the padding, fill the icon width, top margin 2px
    a = np.asarray(cut)
    ys, xs = np.nonzero(a[..., 3] > 0)
    body = cut.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    sc = S / body.width
    body = body.resize((S, max(1, round(body.height * sc))), Image.LANCZOS)
    icon.alpha_composite(body, (0, 2))
    # keep the mascot inside the rounded silhouette
    ia = np.asarray(icon).copy()
    ia[..., 3] = np.minimum(ia[..., 3], np.asarray(mask))
    return Image.fromarray(ia, "RGBA")


# ----------------------------------------------------------------- QA
def qa(cut, icon):
    qdir = os.path.join(QA, "qa")
    os.makedirs(qdir, exist_ok=True)
    chk = Image.new("RGB", cut.size, (255, 255, 255))
    d = ImageDraw.Draw(chk)
    for yy in range(0, cut.height, 12):
        for xx in range(0, cut.width, 12):
            if (xx // 12 + yy // 12) % 2:
                d.rectangle((xx, yy, xx + 11, yy + 11), fill=(226, 226, 230))
    for name, bgc in (("light", (242, 245, 251)), ("dark", (15, 26, 46)), ("checker", None)):
        base = chk.copy() if bgc is None else Image.new("RGB", cut.size, bgc)
        base.paste(cut, (0, 0), cut)
        base.save(os.path.join(qdir, "qa_%s.png" % name))
    # 4x zoom of the risky edges over dark and light
    for rname, box in (("top", (0, 0, cut.width, 70)), ("bottom", (0, cut.height - 70, cut.width, cut.height)),
                       ("left", (0, 40, 110, cut.height)), ("right", (cut.width - 110, 40, cut.width, cut.height))):
        for bgname, bgc in (("dark", (15, 26, 46)), ("light", (246, 248, 255))):
            base = Image.new("RGB", cut.size, bgc)
            base.paste(cut, (0, 0), cut)
            c = base.crop(box)
            c = c.resize((min(c.width * 4, 1400), min(c.height * 4, 1400)), Image.NEAREST)
            c.save(os.path.join(qdir, "qa_zoom_%s_%s.png" % (rname, bgname)))
    # icon contact sheet: 256 px + list sizes
    sheet = Image.new("RGBA", (S_ICON + 130, S_ICON + 24), (255, 255, 255, 255))
    sheet.alpha_composite(icon, (8, 8))
    sheet.alpha_composite(icon.resize((48, 48), Image.LANCZOS), (S_ICON + 18, 40))
    sheet.alpha_composite(icon.resize((32, 32), Image.LANCZOS), (S_ICON + 18, 100))
    sheet.alpha_composite(icon.resize((22, 22), Image.LANCZOS), (S_ICON + 18, 145))
    sheet.save(os.path.join(qdir, "qa_icon_sizes.png"))


# ----------------------------------------------------------------- saving
def reduce_then_save(im, path, budget, name):
    """Save RGBA PNG under a byte budget. Lossless first, then a mild 6-6-6 RGB
    depth reduction (max 2/255 per channel: invisible), then 5-6-5, then a
    palette fallback. Alpha stays full 8-bit at every step."""
    im.save(path, "PNG", optimize=True, compress_level=9)
    size = os.path.getsize(path)
    if size <= budget:
        return
    a = np.asarray(im).copy()
    for tag, bits in (("6-6-6", 6), ("5-5-5", 5)):
        b = a.copy()
        for ch in range(3):
            nb = bits
            q = np.rint(b[..., ch].astype(np.float32) / 255.0 * ((1 << nb) - 1))
            b[..., ch] = np.rint(q / ((1 << nb) - 1) * 255.0).astype(np.uint8)
        Image.fromarray(b, "RGBA").save(path, "PNG", optimize=True, compress_level=9)
        size = os.path.getsize(path)
        print("%s: truecolor too big, RGB%s -> %d bytes" % (name, tag, size))
        if size <= budget:
            return
    im.quantize(colors=256, method=Image.FASTOCTREE).save(path, "PNG", optimize=True, compress_level=9)
    print("WARNING %s: quantised to 256 colours -> %d bytes" % (name, os.path.getsize(path)))


# ----------------------------------------------------------------- main
def main():
    cut = build_cutout()

    fish = os.path.join(ASSETS, "fish.png")
    reduce_then_save(cut, fish, 110 * 1024, "fish.png")

    with open(fish, "rb") as f:
        raw = f.read()
    with open(os.path.join(ASSETS, "fish.b64.txt"), "w", encoding="ascii", newline="") as f:
        f.write(base64.b64encode(raw).decode("ascii"))

    icon = build_icon(Image.open(fish).convert("RGBA"))
    icon_path = os.path.join(ASSETS, "fish-icon.png")
    reduce_then_save(icon, icon_path, 100 * 1024, "fish-icon.png")
    shutil.copyfile(icon_path, os.path.join(PKG, "icon.png"))

    qa(Image.open(fish).convert("RGBA"), Image.open(icon_path).convert("RGBA"))

    # report
    a = np.asarray(Image.open(fish).convert("RGBA"))
    print("\n== fish.png %dx%d  %d bytes (%0.1f KiB)" % (a.shape[1], a.shape[0], os.path.getsize(fish), os.path.getsize(fish) / 1024))
    print("   corner alpha:", a[0, 0, 3], a[0, -1, 3], a[-1, 0, 3], a[-1, -1, 3])
    print("   opaque px:", int((a[..., 3] == 255).sum()), " semi px:", int(((a[..., 3] > 0) & (a[..., 3] < 255)).sum()))
    cy, cx = a.shape[0] // 2, a.shape[1] // 2
    print("   centre px:", a[cy, cx])
    ia = np.asarray(Image.open(icon_path).convert("RGBA"))
    print("== fish-icon.png %dx%d  %d bytes (%0.1f KiB)  corner:", ia.shape[1], ia.shape[0],
          os.path.getsize(icon_path), os.path.getsize(icon_path) / 1024, ia[0, 0, 3])
    print("== icon.png %d bytes identical=%s" % (os.path.getsize(os.path.join(PKG, "icon.png")),
          open(os.path.join(PKG, "icon.png"), "rb").read() == open(icon_path, "rb").read()))
    b64 = open(os.path.join(ASSETS, "fish.b64.txt")).read()
    print("== fish.b64.txt len=%d newlines=%d decodes=%s" % (len(b64), b64.count("\n"),
          base64.b64decode(b64) == raw))


if __name__ == "__main__":
    main()
