#!/usr/bin/env python3
"""panel_coverage.py — is anything actually drawn, in every panel, at every frame?

A render can exit 0, write a perfectly valid file, and be blank (GOTCHAS §2.1).
Worse, DOM chrome (badges, labels, counters) keeps painting when the canvas
fails, so a small positive ink reading proves nothing on its own.

This answers two questions you cannot answer by looking:
  * per spatial panel  — which cell of a multi-panel layout is empty?
  * per temporal panel — which stretch of the loop goes dead? (a panel that
    reads 0% for the *whole* loop is broken; 0% for 0.2s is design)

Ink = pixels brighter than --threshold. For "is the frame dark?" use mean
luminance instead: thresholded ink cannot tell *blurred* from *dark*
(GOTCHAS §3.7), so this prints both.

Usage
-----
  # one frame sliced into a 4x2 panel layout
  python3 scripts/panel_coverage.py frames/ --cols 4 --rows 2

  # a laid-out capture sheet, ignoring the gaps between panels
  python3 scripts/panel_coverage.py sheet.png --cols 3 --rows 2 --gap 24

  # temporal: one panel per frame (checks for dead beats in the loop)
  python3 scripts/panel_coverage.py frames/*.png --cols 1 --rows 1 --min-ink 0.2

Exit code 1 if any panel never reaches --min-ink, else 0.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np
from PIL import Image


def expand(targets):
    out = []
    for t in targets:
        if os.path.isdir(t):
            for ext in ("png", "jpg", "jpeg", "bmp"):
                out += sorted(glob.glob(os.path.join(t, f"*.{ext}")))
        else:
            out += sorted(glob.glob(t))
    return out


def luma(arr):
    return (0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2])


def slice_panels(im, cols, rows, gap, box=None):
    """Yield (row, col, PIL.Image) for a cols x rows grid, minus `gap` px between cells."""
    W, H = im.size
    if box:
        pw, ph = box
        pw = min(pw, (W - gap * (cols - 1)) // cols)
        ph = min(ph, (H - gap * (rows - 1)) // rows)
    else:
        pw = (W - gap * (cols - 1)) // cols
        ph = (H - gap * (rows - 1)) // rows
    for r in range(rows):
        for c in range(cols):
            x0 = c * (pw + gap)
            y0 = r * (ph + gap)
            yield r, c, im.crop((x0, y0, x0 + pw, y0 + ph))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Per-panel ink coverage across frames.")
    ap.add_argument("targets", nargs="+", help="image files, globs, or a directory")
    ap.add_argument("--cols", type=int, default=1)
    ap.add_argument("--rows", type=int, default=1)
    ap.add_argument("--gap", type=int, default=0, help="pixels between panels in the sheet")
    ap.add_argument("--box", default=None, help="panel size WxH instead of dividing evenly")
    ap.add_argument("--threshold", type=int, default=60, help="luma above this counts as ink (0-255)")
    ap.add_argument("--min-ink", type=float, default=0.05,
                    help="a panel below this %% at EVERY frame is reported dead")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    box = None
    if args.box:
        w, h = args.box.lower().split("x")
        box = (int(w), int(h))

    files = expand(args.targets)
    if not files:
        print("no images matched", file=sys.stderr)
        return 2

    n = args.cols * args.rows
    ink = np.zeros((n, len(files)))
    lum = np.zeros((n, len(files)))

    for fi, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        for r, c, panel in slice_panels(im, args.cols, args.rows, args.gap, box):
            a = np.asarray(panel).astype(np.float32)
            L = luma(a)
            p = r * args.cols + c
            ink[p, fi] = 100.0 * float((L > args.threshold).mean())
            lum[p, fi] = float(L.mean())

    print(f"panel_coverage  {len(files)} frame(s)  grid {args.cols}x{args.rows} = {n} panel(s)"
          f"  gap={args.gap}px  ink>luma{args.threshold}")
    print()
    header = f"{'panel':>6}  {'min ink%':>9}  {'max ink%':>9}  {'frames@0%':>9}  {'mean luma':>9}  verdict"
    print(header)
    print("-" * len(header))
    dead = []
    for p in range(n):
        mn, mx = float(ink[p].min()), float(ink[p].max())
        zeros = int((ink[p] < 0.01).sum())
        ml = float(lum[p].mean())
        if mx < args.min_ink:
            v = "DEAD - never drew"
            dead.append(p)
        elif zeros == len(files):
            v = "DEAD - all frames"
            dead.append(p)
        elif zeros:
            v = f"{zeros} empty frame(s) - check duration"
        else:
            v = "ok"
        print(f"{p:>6}  {mn:>9.3f}  {mx:>9.3f}  {zeros:>9}  {ml:>9.2f}  {v}")

    print()
    print(f"  frames are low-luma relative to each other:")
    order = np.argsort(lum.mean(axis=0))
    for i in order[:3]:
        print(f"    {os.path.basename(files[i])}  mean luma {lum[:, i].mean():.2f}  "
              f"min panel ink {ink[:, i].min():.3f}%")
    print(f"  darkest frame mean luma {lum.mean(axis=0).min():.2f} / "
          f"brightest {lum.mean(axis=0).max():.2f}")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"files": [os.path.basename(f) for f in files],
                       "cols": args.cols, "rows": args.rows,
                       "ink_pct": ink.tolist(), "mean_luma": lum.tolist(),
                       "dead_panels": dead}, fh, indent=2)
        print(f"  wrote {args.json}")

    if dead:
        print(f"  verdict: FAIL - {len(dead)} dead panel(s): {dead}")
        return 1
    print("  verdict: PASS - every panel drew at some point")
    return 0


if __name__ == "__main__":
    sys.exit(main())
