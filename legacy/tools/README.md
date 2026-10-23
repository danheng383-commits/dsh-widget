# 大肥鱼 mascot assets — build & verify

Regenerates all mascot image assets from `../assets/source-original.png`
(never modified). Only needs the bundled Python runtime with Pillow + numpy:

    C:\Users\Emily\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe tools\build_assets.py
    C:\Users\Emily\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe tools\verify_assets.py

## Outputs (see paths relative to the package root)

| file                       | what                                                                 | budget / size        |
|----------------------------|----------------------------------------------------------------------|----------------------|
| `assets/fish.png`          | transparent bust cutout, 8 px padding, native resolution            | ≤360 px, ≤110 KiB   |
| `assets/fish-icon.png`     | 256×256 rounded-square icon (pastel gradient, mascot fills the width) | ≤100 KiB           |
| `assets/fish.b64.txt`      | single-line base64 of `fish.png` (no `data:` prefix, no newlines)    | —                    |
| `icon.png`                 | byte copy of `fish-icon.png` for the plugin manager                  | —                    |
| `tools/qa/*.png`           | QA composites: light / dark / checker boards, 4× edge zooms, icon sizes | —                   |

## How `fish.png` is produced

1. **Background** — near-white/near-neutral light pixels (min channel ≥ 225,
   max−min ≤ 30) that are 4-connected to any image border get flood-filled
   out. This removes the white page, the light grey top-right panel, and the
   soft glow around the hair in one pass.
2. **Character component** — 8-connected labelling keeps only the largest
   component (the chibi), which alone drops the hamburger button, the top-edge
   UI fragments, and every other stray speck.
3. **Explicit UI clears** — belt-and-braces: top strip `y ≤ 9`, hamburger box
   `(x 40..106, y 8..70)`, and the 1 px neutral-grey divider at `y 33..47`
   (chroma ≤ 10, min ≥ 190) right of the head. Nothing in these boxes belongs
   to the character (verified pixel by pixel before building).
4. **Soft alpha** — only the 2 px silhouette ring gets fractional alpha,
   estimated per pixel against the *nearest interior colour*:
   `a = Σ(255−P)/(255−F)` over channels where `255−F ≥ 18`. Ring colours are
   replaced by that interior colour (decontamination), so no white halo is
   possible. Interior pixels stay fully opaque (the white headdress / collar
   are preserved exactly — no global white removal anywhere).
5. **Trim + pad** — bbox of visible content + 8 px transparent padding;
   colours are bled 8 px outside the silhouette so downscaling never pulls in
   white or dark fringes. Long edge is capped at 360 (native 331×353 already
   fits, so no downscale is applied).
6. **Size budget** — truecolor PNG lands at ~127 KiB, over the 110 KiB budget,
   so RGB channels are rounded to 6 bits each (max 2/255 per channel,
   imperceptible); this yields 95.1 KiB with full 8-bit alpha. If ever needed
   it falls back to 5-bit and finally a 256-colour palette.

The source character is natively cropped at `y = 347` (15 px white strip
below) and its hair runs into the left/right edges; that crop is kept as-is
(bust portrait) — no pixels were invented.

## Icon layout

Mascot (padding stripped) is scaled to fill the 256 px icon width, top-aligned
with a 2 px top margin, so the source's bottom crop runs off the canvas instead
of floating as a line. Background is a vertical pastel-blue gradient with a
soft top highlight and a faint cool bottom shade, clipped to a rounded square
(radius 54).

## Caveats

* The headdress lace was originally drawn on white, so its outermost rim is
  inherently ambiguous against the page; the rim keeps a light, slightly
  feathered edge (this is the art, not an artefact). No UI chrome remains
  anywhere (hamburger, top fragments, divider line all verified gone at 4×).
* `fish.b64.txt` is ~126 KiB of base64 — fine to embed in `client.js` if the
  lead prefers embedding over a runtime file read.
