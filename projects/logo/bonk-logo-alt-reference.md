# BONK logo — alternate ("logo-1") reference

Source: Figma **"copy as CSS"** export, pasted by Suhaas 2026-09-26.
Status: **reference only.** The canonical mark is `projects/dotcut/public/bonk-wordmark.html` (+ `bonk-wordmark.svg` here).

## What this export actually carries

Every layer in the paste is a positioned box with `background:#FFFFFF` — no `path`, no `clip-path`,
no `mask`, no `d`. A Figma CSS export only emits outlines if you copy the *SVG* (or "copy as SVG"),
not "copy as CSS". So this file gives **positions and nothing about shape**:

| layer | CSS box (left / right / top / bottom, % of a 2000×2000 frame) | px box (x0→x1, y0→y1) |
|---|---|---|
| bleed plate | −10 / −10 / −10 / −10, `#FFFFFF` | −200→2200 both axes |
| black plate | 0 / 0 / 0 / 0, `#000000` | 0→2000 both axes |
| glyph 1 (`b`) | 33.30 / 58.38 / 44.75 / 44.70 | 666→832, 895→1106 |
| glyph 2 (`o`) | 41.60 / 50.32 / 47.38 / 44.70 | 832→994, 948→1106 |
| glyph 3 (`n`) | 50.07 / 42.29 / 47.38 / 44.90 | 1001→1154, 948→1102 |
| glyph 4 (`k`, bare vector) | 58.45 / 33.35 / 44.77 / 44.93 | 1169→1333, 895→1101 |
| glyph 5 (fragment) | 65.40 / 32.79 / 44.80 / 52.90 | 1308→1344, 896→1058 |
| glyph 6 (fragment) | 67.18 / 32.05 / 44.93 / 52.49 | 1344→1359, 899→1050 |

(The paste contains this block twice, identical.)

## How it relates to the shipped mark

Measured against the real path data in `projects/dotcut/public/bonk-wordmark.html` (tight ink bboxes via
`getBBox`, cross-checked with an independent bezier-bounds solver — they agree to 0.1px):

* The `b / o / n / k` boxes are the **same lockup, uniformly scaled**:
  `x_alt = 1.1766·x_main − 142.97`, `y_alt = 1.1279·y_main − 85.21`.
  **Max residual 2.1px on a 2000px frame** (mean 0.7px). The 4.3% x/y anisotropy is export frame
  padding, not a design difference.
* So the alt is not a different construction — it is the same six-glyph mark sitting **~17% wider /
  ~13% taller** inside the same 2000 square (i.e. main is that file at ~0.85× / ~0.89×).
* Layers 5 and 6 are **fragment frames**, not letter boxes (36×162px and 15×151px — a full-size `d`
  would measure 60×76, an `i` 27×96). Their left edges land where a scaled `d`/`i` would, but their
  heights sit on the ascender line, so do not use those two percentages as glyph positions.
* The alt splits the `k` into 3 separate vectors (one bare `Vector` + two groups) while the shipped
  SVG has `k` as one path. Since the export has no outlines, **shape/weight changes cannot be
  compared from it** — only position. Re-export as SVG if you want to diff the curves.

## The mark's six glyphs (this matters)

The shipped SVG contains **six** paths, right-to-left in file order: `k · n · o · b` at full size,
plus a **small `d` and `j`** (~34% scale, sitting on a baseline ~61px below the `b/o/n` baseline)
tucked at the bottom right — the `bonk.dj` domain lockup. Rasterised per-path to confirm.
**Corrected 2026-09-27**: this doc previously called the second small glyph an `i`. It is a `j`.
Verified from the geometry, not by eye — the `d` sits on the small baseline (bottom 1113.3) while
the second glyph drops **17.6px below it** (bottom 1130.9), and a descender is the one thing an `i`
cannot have. Measured via `getBBox()` on each path.

Including that small `dj`, the ink bbox is
x 687→1313.7, y 869→1130.9 — **centred in the 2000 frame to within 0.4px**, so the `dj` is load
-bearing, not stray geometry. Total ink footprint: 31.3% × 13.1% of the frame.

## Verbatim paste

```css
/* Bonk logo-1 1 */

position: relative;
width: 2000px;
height: 2000px;

/* Vector */
position: absolute;
left: -10%; right: -10%; top: -10%; bottom: -10%;
background: #FFFFFF;

/* Group */
position: absolute;
left: 0%; right: 0%; top: 0%; bottom: 0%;

/* Rectangle */
position: absolute;
left: 0%; right: 0%; top: 0%; bottom: 0%;
background: #000000;

/* Group */
position: absolute;
left: 33.3%; right: 58.38%; top: 44.75%; bottom: 44.7%;

/* Vector */
position: absolute;
left: 33.3%; right: 58.38%; top: 44.75%; bottom: 44.7%;
background: #FFFFFF;

/* Group */
position: absolute;
left: 41.6%; right: 50.32%; top: 47.38%; bottom: 44.7%;

/* Vector */
position: absolute;
left: 41.6%; right: 50.32%; top: 47.38%; bottom: 44.7%;
background: #FFFFFF;

/* Group */
position: absolute;
left: 50.07%; right: 42.29%; top: 47.38%; bottom: 44.9%;

/* Vector */
position: absolute;
left: 50.07%; right: 42.29%; top: 47.38%; bottom: 44.9%;
background: #FFFFFF;

/* Vector */
position: absolute;
left: 58.45%; right: 33.35%; top: 44.77%; bottom: 44.93%;
background: #FFFFFF;

/* Group */
position: absolute;
left: 65.4%; right: 32.79%; top: 44.8%; bottom: 52.9%;

/* Vector */
position: absolute;
left: 65.4%; right: 32.79%; top: 44.8%; bottom: 52.9%;
background: #FFFFFF;

/* Group */
position: absolute;
left: 67.18%; right: 32.05%; top: 44.93%; bottom: 52.49%;

/* Vector */
position: absolute;
left: 67.18%; right: 32.05%; top: 44.93%; bottom: 52.49%;
background: #FFFFFF;
```

Each glyph in the paste appears as 3–4 nested duplicate rules (Group → Group → Group → Vector) with
identical edges; collapsed above for readability. Numeric edges are unchanged.

## Files here

* `bonk-wordmark.svg` — standalone asset, white fill, transparent bg, extracted from the shipped HTML.
  Verified to render: at 800px the ink bbox lands x 275→524, y 348→451, matching the path-data
  prediction within 1px. Note it is white-on-transparent — composite it over dark, don't open it on a
  white page (it looks blank).
* `bonk-wordmark-gradient.svg` — same, with the pink→amber→yellow gradient.
* `logo-lockup-compare.html` — live comparison: main / alt boxes over main / alt boxes over fitted main.
* `lockup-compare.png` — screenshot of that page.
* `glyph-id-strip.png` — each of the six glyph paths rasterised individually (identifies the small `id`).
