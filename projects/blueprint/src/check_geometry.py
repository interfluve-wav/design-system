#!/usr/bin/env python3
"""
Objective geometry check on captured frames.

The mark's fill is isolated from accent-coloured UI text (spec panel header,
dimension labels, anchors) by eroding the accent mask: hairlines and 12px text
disappear, the thick letterforms survive. That yields a trustworthy mark bbox
to compare against the layout's expected box, and lets us ask the two questions
a review complaint raised: is the mark the right size, and is anything drawing
on top of it.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

SCRATCH = Path("/Users/suhaas/.hermes/cache/scratch")

# layout: 1920x1080 CSS at device scale 2
MARK_W_CSS, MARK_H_CSS = 302.1, 257.0
TARGET_W = 1920 * 0.40
S = TARGET_W / MARK_W_CSS
EXPECT = {                      # device px
    "x0": (1920 * 0.455 - TARGET_W / 2) * 2,
    "x1": (1920 * 0.455 + TARGET_W / 2) * 2,
    "y0": (1080 * 0.50 - MARK_H_CSS * S / 2) * 2,
    "y1": (1080 * 0.50 + MARK_H_CSS * S / 2) * 2,
}


def erode(mask: np.ndarray, n: int = 3) -> np.ndarray:
    out = mask.copy()
    for k in range(1, n + 1):
        out = (
            out
            & np.roll(out, k, axis=0) & np.roll(out, -k, axis=0)
            & np.roll(out, k, axis=1) & np.roll(out, -k, axis=1)
        )
    return out


def analyse(path: Path) -> None:
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]

    strict = (np.abs(r - 255) < 60) & (np.abs(g - 107) < 60) & (np.abs(b - 26) < 60)
    loose = (r > 90) & (r > g * 1.35) & (g > b)
    core = erode(strict, 3)
    grey = (r > 40) & (np.abs(r - g) < 26) & (np.abs(g - b) < 26) & ~loose

    print(f"\n{path.name}")
    if core.sum() < 500:
        print(f"  no solid mark fill yet (core {int(core.sum())} px)")
        print(f"  strict accent {int(strict.sum())} px · grey {int(grey.sum())} px")
        return

    rows = np.nonzero(core.sum(axis=1))[0]
    cols = np.nonzero(core.sum(axis=0))[0]
    bx = (int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1]))
    print(f"  mark fill core  : {int(core.sum()):>8} px   bbox {bx}")
    print(f"  expected box    : ({EXPECT['x0']:.0f}, {EXPECT['y0']:.0f}, {EXPECT['x1']:.0f}, {EXPECT['y1']:.0f})")

    outside = (bx[0] < EXPECT["x0"] - 4 or bx[1] < EXPECT["y0"] - 4
               or bx[2] > EXPECT["x1"] + 4 or bx[3] > EXPECT["y1"] + 4)
    print(f"  containment     : {'OUTSIDE expected box' if outside else 'inside expected box (erode margin ~3px)'}")

    inner = grey[bx[1] + 8:bx[3] - 8, bx[0] + 8:bx[2] - 8]
    print(f"  grey inside box : {int(inner.sum()):>8} px   ({inner.mean()*100:.3f}% of box)")
    print(f"  grey overall    : {int(grey.sum()):>8} px")
    borders = (int(grey[:8, :].sum()), int(grey[-8:, :].sum()), int(grey[:, :8].sum()), int(grey[:, -8:].sum()))
    print(f"  grey in borders : top {borders[0]}  bottom {borders[1]}  left {borders[2]}  right {borders[3]}")


if __name__ == "__main__":
    names = sys.argv[1:] or [
        "check-bonk-blueprint-t2.2.png",
        "check-bonk-blueprint-t3.6.png",
        "check-bonk-blueprint-t5.4.png",
        "check-bonk-blueprint-t7.0.png",
    ]
    for n in names:
        p = Path(n) if Path(n).is_absolute() else SCRATCH / n
        if p.exists():
            analyse(p)
        else:
            print(f"missing {p}")
