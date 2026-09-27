#!/usr/bin/env python3
"""
Verify the traced wordmark against the source raster, pixel by pixel.

The trace pipeline is easy to get subtly wrong (polarity, relative-command
resolution, coordinate spaces) and the failure mode is a torn or inverted
letterform rather than an exception. So: rasterize the traced path, compare it
to the source ink mask, and report real disagreement numbers.

Run after trace.py. Exit code 1 if agreement is below threshold.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path("/Users/suhaas/Documents/GitHub/bonk-beta/src/assets/auth/bonk-wordmark.png")
PATHS = Path("/Users/suhaas/Pictures/motion - design - assets/blueprint/public/wordmark-paths.js")
OUT = Path("/Users/suhaas/.hermes/cache/scratch")
MIN_IOU = 0.90
SS = 4  # supersample factor for an anti-aliased comparison render


def main() -> int:
    mask = np.array(Image.open(SRC).convert("L")) > 110
    rows = np.nonzero(mask.sum(axis=1))[0]
    cols = np.nonzero(mask.sum(axis=0))[0]
    ref = mask[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    h, w = ref.shape

    js = PATHS.read_text()
    data = json.loads(js[js.index("{"):js.rindex(";")])

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {data["width"]} {data["height"]}" '
        f'width="{w * SS}" height="{h * SS}">'
        f'<rect width="100%" height="100%" fill="black"/>'
        f'<path d="{data["d"]}" fill="white" fill-rule="nonzero"/></svg>'
    )
    svg_path = OUT / "verify-trace.svg"
    png_path = OUT / "verify-trace.png"
    svg_path.write_text(svg)
    subprocess.run(["magick", "-background", "black", str(svg_path), str(png_path)], check=True)

    rendered = Image.open(png_path).convert("L").resize((w, h), Image.LANCZOS)
    got = np.array(rendered) > 110

    inter = np.logical_and(ref, got).sum()
    union = np.logical_or(ref, got).sum()
    iou = inter / union if union else 0.0
    extra = np.logical_and(got, ~ref).sum()
    missing = np.logical_and(ref, ~got).sum()
    speckle = extra / max(1, ref.sum())

    # The reference here is cropped to its ink bbox, so both bboxes must match
    # exactly — a torn or offset trace shows up as a shifted/oversized box.
    def bbox(a: np.ndarray) -> tuple[int, int, int, int]:
        r = np.nonzero(a.sum(axis=1))[0]
        c = np.nonzero(a.sum(axis=0))[0]
        return int(r[0]), int(r[-1]), int(c[0]), int(c[-1])

    ref_box, got_box = bbox(ref), bbox(got)
    box_ok = all(abs(a - b) <= 1 for a, b in zip(ref_box, got_box))

    print(f"reference ink    : {ref.sum()} px  ({w}x{h})")
    print(f"traced ink       : {got.sum()} px")
    print(f"IoU              : {iou:.4f}   (target >= {MIN_IOU})")
    print(f"missing ink      : {missing} px ({missing / max(1, ref.sum()) * 100:.2f}% of source)")
    print(f"extra ink        : {extra} px ({speckle * 100:.2f}% of source)")
    print(f"ink bbox         : ref {ref_box} vs traced {got_box}  -> {'match' if box_ok else 'MISMATCH'}")

    diff = np.zeros((h, w, 3), dtype=np.uint8)
    diff[..., 0] = np.where(ref, 255, 0)          # source = red
    diff[..., 1] = np.where(got, 255, 0)          # traced = green -> overlap = yellow
    Image.fromarray(diff).resize((w * 2, h * 2), Image.NEAREST).save(OUT / "verify-trace-diff.png")
    print(f"diff image       : {OUT / 'verify-trace-diff.png'} (red=source, green=trace, yellow=overlap)")

    ok = iou >= MIN_IOU and box_ok
    print("RESULT           :", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
