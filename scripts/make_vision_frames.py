#!/usr/bin/env python3
"""Downscale verification frames for vision inspection.

vision_analyze times out on large payloads (GOTCHAS 3.6) -- 1280x720 PNGs of a dark
render are well over the working ceiling. 320 px wide passes reliably.
"""
import glob
import os
import sys

from PIL import Image

BASE = os.path.expanduser("~/.hermes/cache/scratch/verify/frames")
OUT = os.path.expanduser("~/.hermes/cache/scratch/vision")
os.makedirs(OUT, exist_ok=True)

for label in sys.argv[1:]:
    for f in sorted(glob.glob(os.path.join(BASE, label, "*.png")))[:4]:
        im = Image.open(f).convert("RGB")
        h = round(320 * im.height / im.width)
        im = im.resize((320, h), Image.LANCZOS)
        p = os.path.join(OUT, "%s__%s" % (label, os.path.basename(f)))
        im.save(p, optimize=True)
        print("%s  %d bytes" % (p, os.path.getsize(p)))
