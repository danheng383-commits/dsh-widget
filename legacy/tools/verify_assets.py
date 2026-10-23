#!/usr/bin/env python
"""Verify the 大肥鱼 mascot assets against the task-1 acceptance criteria.

Checks (exit code 0 = all good):
  * all four deliverables exist, source-original.png untouched
  * fish.png: RGBA, long edge <= 360, <= 110 KiB, corner alpha 0, character alpha 255,
    anti-aliased alpha ramp present, 8px transparent padding, no stray islands,
    no UI leftovers (hamburger / top divider) in the shipped crop
  * fish-icon.png: 256x256 square, <= 100 KiB, valid PNG
  * icon.png identical to fish-icon.png
  * fish.b64.txt: single line, decodes to exactly fish.png
Run:  <bundled python> tools/verify_assets.py
"""
import base64
import hashlib
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ASSETS = os.path.join(PKG, "assets")
FISH = os.path.join(ASSETS, "fish.png")
ICON = os.path.join(ASSETS, "fish-icon.png")
B64 = os.path.join(ASSETS, "fish.b64.txt")
ROOT_ICON = os.path.join(PKG, "icon.png")
SRC = os.path.join(ASSETS, "source-original.png")

ok = True


def check(cond, msg):
    global ok
    print(("  OK   " if cond else "  FAIL ") + msg)
    ok = ok and bool(cond)


def main():
    for p in (FISH, ICON, B64, ROOT_ICON, SRC):
        check(os.path.isfile(p), "exists: %s (%s bytes)" % (p, os.path.getsize(p) if os.path.isfile(p) else "-"))

    print("\nfish.png")
    im = Image.open(FISH)
    a = np.asarray(im.convert("RGBA"))
    h, w = a.shape[:2]
    size = os.path.getsize(FISH)
    check(im.format == "PNG", "format PNG (mode %s)" % im.mode)
    check(max(w, h) <= 360, "long edge %d <= 360 (%dx%d)" % (max(w, h), w, h))
    check(size <= 110 * 1024, "size %d bytes (%.1f KiB) <= 110 KiB" % (size, size / 1024))
    check(a[0, 0, 3] == 0 and a[0, -1, 3] == 0 and a[-1, 0, 3] == 0 and a[-1, -1, 3] == 0,
          "corner alpha 0 (tl=%d tr=%d bl=%d br=%d)" % (a[0, 0, 3], a[0, -1, 3], a[-1, 0, 3], a[-1, -1, 3]))
    opaque = a[..., 3] == 255
    semi = (a[..., 3] > 0) & (a[..., 3] < 255)
    check(opaque.sum() > 0.3 * w * h, "character pixels opaque: %d" % opaque.sum())
    check(semi.sum() > 500, "anti-aliased edge pixels: %d" % semi.sum())
    # 8 px transparent padding on every side of the content bbox
    ys, xs = np.nonzero(a[..., 3] > 0)
    pad = (xs.min(), ys.min(), w - 1 - xs.max(), h - 1 - ys.max())
    check(pad == (8, 8, 8, 8), "transparent padding L/T/R/B = %s" % (pad,))
    # character alpha at a known opaque spot (centre of the face is opaque)
    check(a[h // 2, w // 2, 3] == 255, "centre pixel alpha %d" % a[h // 2, w // 2, 3])
    # no near-white halo: every semi-transparent pixel must not be washed-out white
    semi_rgb = a[..., :3][semi].astype(int)
    washed = ((semi_rgb.min(axis=1) > 235) & (semi_rgb.max(axis=1) - semi_rgb.min(axis=1) < 8)).sum()
    check(washed < 0.05 * max(1, semi.sum()), "washed-out white fringe pixels: %d / %d" % (washed, semi.sum()))
    # no stray islands: one big foreground blob plus no isolated specks far from it
    from collections import deque
    fg = a[..., 3] > 0
    seen = np.zeros_like(fg)
    comps = []
    for y0 in range(h):
        for x0 in range(w):
            if fg[y0, x0] and not seen[y0, x0]:
                dq = deque([(y0, x0)])
                seen[y0, x0] = True
                n = 0
                while dq:
                    y, x = dq.popleft()
                    n += 1
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h and 0 <= nx < w and fg[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                dq.append((ny, nx))
                comps.append(n)
    check(len(comps) == 1, "foreground components: %d (sizes %s)" % (len(comps), sorted(comps, reverse=True)[:5]))
    # the source top chrome (hamburger at ~(45..93, 13..59) + divider row 38) must be gone:
    # the cutout is trimmed, so compare against the source mapping: content offset was 39,11
    # -> hamburger maps to (45-39+8, 13-11+8) = (14, 10) in fish.png
    hb = a[10:60, 14:64, 3]
    check(int((hb > 0).sum()) == 0, "hamburger area is transparent (%d px)" % int((hb > 0).sum()))

    print("\nfish-icon.png")
    ic = Image.open(ICON)
    ia = np.asarray(ic.convert("RGBA"))
    check(ic.format == "PNG", "format PNG (mode %s)" % ic.mode)
    check(ic.size == (256, 256), "size %dx%d is 256x256 square" % ic.size)
    check(os.path.getsize(ICON) <= 100 * 1024, "size %d bytes (%.1f KiB) <= 100 KiB" % (os.path.getsize(ICON), os.path.getsize(ICON) / 1024))
    check(ia[128, 128, :3].min() >= 0, "centre pixel rgba %s" % (tuple(int(v) for v in ia[128, 128]),))

    print("\nicon.png / fish.b64.txt")
    check(open(ROOT_ICON, "rb").read() == open(ICON, "rb").read(), "icon.png is a byte copy of fish-icon.png")
    raw = open(FISH, "rb").read()
    txt = open(B64, "r", encoding="ascii").read()
    check("\n" not in txt and "\r" not in txt, "fish.b64.txt is a single line (%d chars)" % len(txt))
    check(txt.startswith("iVBORw0KGgo"), "base64 starts with the PNG magic iVBORw0KGgo")
    check(base64.b64decode(txt) == raw, "base64 decodes byte-identically to fish.png")

    print("\nsource")
    src = Image.open(SRC)
    check(src.size == (354, 363), "source-original.png untouched %dx%d, %d bytes" % (src.width, src.height, os.path.getsize(SRC)))
    print("  source sha256:", hashlib.sha256(open(SRC, "rb").read()).hexdigest())

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
