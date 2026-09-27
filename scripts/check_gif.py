#!/usr/bin/env python3
"""check_gif.py — measure a delivered GIF instead of trusting its label.

A GIF can open fine, have the frame count you expect, and still contain dead
beats or a loop seam that snaps. This reads every frame and reports:

  * frame count, size, declared frame rate, total duration
  * ink% and mean luminance per frame, and where the dead frames are
  * the loop seam: mean absolute pixel delta between the last frame and the
    first. A reel that loops should have a seam no worse than its typical
    consecutive-frame delta, or it pops every cycle.

Usage
-----
  python3 scripts/check_gif.py /path/to/render.gif [more.gif ...]
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageSequence


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def check(path):
    im = Image.open(path)
    n = getattr(im, "n_frames", 1)
    dur_ms = im.info.get("duration", 0)
    inks, lums, d = [], [], None
    prev = None
    deltas = []
    first = last = None
    for i, fr in enumerate(ImageSequence.Iterator(im)):
        a = np.asarray(fr.convert("RGB")).astype(np.float32)
        L = luma(a)
        inks.append(100.0 * float((L > 60).mean()))
        lums.append(float(L.mean()))
        if i == 0:
            first = a
        if prev is not None:
            deltas.append(float(np.abs(a - prev).mean()))
        prev = a
        last = a
    seam = float(np.abs(last - first).mean()) if first is not None else 0.0
    deltas = np.array(deltas) if deltas else np.array([0.0])

    print(f"\n{os.path.basename(path)}")
    print(f"  {n} frames  {im.size[0]}x{im.size[1]}  {dur_ms} ms/frame"
          f"  -> {n * dur_ms / 1000.0:.2f} s  at {1000.0 / max(dur_ms, 1):.1f} fps")
    print(f"  size on disk          : {os.path.getsize(path) / 1e6:.2f} MB")
    print(f"  ink%                  : min {min(inks):.3f}  max {max(inks):.3f}  "
          f"mean {float(np.mean(inks)):.3f}")
    print(f"  mean luminance        : min {min(lums):.2f}  max {max(lums):.2f}")
    dead = [i for i, v in enumerate(inks) if v < 0.01]
    if dead:
        print(f"  DEAD FRAMES           : {len(dead)}  at {dead[:12]}"
              f"{' ...' if len(dead) > 12 else ''}")
    else:
        print("  DEAD FRAMES           : none")
    print(f"  frame-to-frame delta  : mean {deltas.mean():.3f}  median "
          f"{float(np.median(deltas)):.3f}  max {deltas.max():.3f}")
    seam_ok = seam <= max(float(deltas.max()), 1e-6)
    verdict = "ok - within the loop own motion" if seam_ok else "SNAPS - worse than any in-loop step"
    print(f"  LOOP SEAM delta       : {seam:.3f}  ({verdict})")
    return {"file": os.path.basename(path), "frames": n, "size": im.size,
            "ms_per_frame": dur_ms, "ink_min": min(inks), "ink_max": max(inks),
            "luma_min": min(lums), "luma_max": max(lums),
            "dead_frames": dead, "seam": seam,
            "delta_mean": float(deltas.mean()), "delta_max": float(deltas.max())}


if __name__ == "__main__":
    targets = sys.argv[1:]
    if not targets:
        print(__doc__)
        sys.exit(2)
    for t in targets:
        if os.path.exists(t):
            check(t)
        else:
            print(f"missing: {t}")
