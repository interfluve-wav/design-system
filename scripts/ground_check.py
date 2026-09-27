#!/usr/bin/env python3
"""Is a page's high ink% real content, or just a light ground?

verify_renders.py measures ink as "% of pixels with luma > 60". That is correct for the
dark brand surfaces and meaningless for a light-theme variant -- a white page reads 100%
ink with or without content. This prints the ground's mean RGB and the luma spread so a
100% reading can be labelled instead of trusted (GOTCHAS 3.9).
"""
import glob
import os

import numpy as np
from PIL import Image

BASE = os.path.expanduser("~/.hermes/cache/scratch/verify/frames")
LABELS = ["dotcut-demo", "blurreveal-v4-lt", "bonk-logo", "libsdev", "bonk-sup",
          "blurreveal-v4", "design-tiles", "intro-preview", "motion-system-v3"]

for label in LABELS:
    fs = sorted(glob.glob(os.path.join(BASE, label, "*.png")))
    if not fs:
        print("%-18s no frames" % label)
        continue
    a = np.stack([np.asarray(Image.open(f).convert("RGB")).astype(np.float32) for f in fs])
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    mean_rgb = a.mean(axis=(0, 1)).mean(axis=0)
    per_frame = lum.mean(axis=(1, 2))
    print("%-18s n=%2d  meanRGB=(%5.1f,%5.1f,%5.1f)  luma>200=%5.1f%%  luma<60=%5.1f%%  "
          "frame-luma %.0f-%.0f"
          % (label, len(fs), mean_rgb[0], mean_rgb[1], mean_rgb[2],
             100 * (lum > 200).mean(), 100 * (lum < 60).mean(),
             per_frame.min(), per_frame.max()))
