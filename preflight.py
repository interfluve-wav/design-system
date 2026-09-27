#!/usr/bin/env python3
"""Pre-flight scan of the deliverables folder — run BEFORE rendering anything.

Why this exists: the reel was rendered three times (750 frames each, ~5 min apiece)
and two of those renders turned out to be pixel-identical. Nothing checked what was
already on disk first, and nothing compared the new output against the old, so the
duplicate was only discovered hours later by hand.

This fingerprints every image/video deliverable by content — 8 frames sampled
across the piece, each downscaled to 24x24 greyscale — and reports pairs that are
identical or near-identical. Content, not filename: a re-render that changed
nothing produces the same fingerprint under a new version tag.

Usage:
    python3 preflight.py              # report only
    python3 preflight.py --gate       # exit 1 if near-duplicates exist (pre-render check)

Thresholds are empirical for this folder: a true duplicate measured 0.0000, and a
subtle-but-real motion change (the reel's beat pulse) measured 0.0430.
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path("/Users/suhaas/Pictures/design - tiles - motion")
SAMPLES = (0.06, 0.18, 0.30, 0.42, 0.55, 0.68, 0.80, 0.93)
GRID = 24
IDENTICAL = 0.010     # hashes to the same picture
NEAR = 0.500          # a change too small to notice


def fingerprint(path: Path):
    """Content signature: 8 timestamps, downscaled to a GRIDxGRID greyscale stack."""
    try:
        im = Image.open(path)
    except Exception:
        return None
    if getattr(im, "is_animated", False) or getattr(im, "n_frames", 1) > 1:
        n = im.n_frames
        vecs = []
        for f in SAMPLES:
            im.seek(min(int(f * n), n - 1))
            g = im.convert("L").resize((GRID, GRID), Image.LANCZOS)
            vecs.append(np.asarray(g, dtype=float).ravel())
        return np.concatenate(vecs)
    # a still: use it as every sample so it can still be compared
    g = im.convert("L").resize((GRID, GRID), Image.LANCZOS)
    v = np.asarray(g, dtype=float).ravel()
    return np.tile(v, len(SAMPLES))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 if near-duplicates exist")
    args = ap.parse_args()

    files = sorted([p for p in OUT.iterdir()
                    if p.suffix.lower() in (".gif", ".png")
                    and not p.name.startswith(".")])
    fps, skipped = {}, 0
    for p in files:
        v = fingerprint(p)
        if v is None:
            skipped += 1
            continue
        fps[p] = v

    print(f"  scanned {len(fps)} files in {OUT.name}  ({skipped} unreadable)\n")

    # group by family: the stem with any trailing -vN / -light etc stripped
    def family(name):
        stem = name.rsplit(".", 1)[0]
        for suf in ("-contact-sheet",):
            stem = stem.replace(suf, "")
        parts = stem.split("-")
        return "-".join(parts[:3])

    dupes = []
    keys = sorted(fps, key=lambda p: p.name)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if family(a.name) != family(b.name):
                continue
            d = np.abs(fps[a] - fps[b]).mean()
            if d <= NEAR:
                dupes.append((d, a, b))

    if not dupes:
        print("  no near-duplicates found")
        return 0

    dupes.sort()
    print("  duplicate / near-duplicate pairs (content-compared, not by filename):")
    print(f"  {'distance':>9}  {'verdict':<16} files")
    for d, a, b in dupes:
        verdict = "IDENTICAL" if d <= IDENTICAL else "near-identical"
        print(f"  {d:9.4f}  {verdict:<16} {a.name}  ==  {b.name}")
    print()
    print(f"  {len(dupes)} pair(s). A render that reproduces an existing file is")
    print("  wasted work -- check before rendering, not afterwards.")

    if args.gate:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
