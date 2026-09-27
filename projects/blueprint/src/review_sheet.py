#!/usr/bin/env python3
"""Compose the key frames of a captured scene into one review sheet."""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SCRATCH = Path("/Users/suhaas/.hermes/cache/scratch")


def main(scene: str, times: list[str], out: str) -> None:
    imgs = []
    for t in times:
        p = SCRATCH / f"check-{scene}-t{t}.png"
        if not p.exists():
            print(f"missing {p}")
            continue
        imgs.append((t, Image.open(p).convert("RGB")))
    if not imgs:
        raise SystemExit("no frames found")

    tw, th = 640, 360
    cols = 3
    rows = (len(imgs) + cols - 1) // cols
    pad = 8
    sheet = Image.new("RGB", (cols * tw + pad * (cols + 1), rows * th + pad * (rows + 1)), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(imgs):
        im = im.resize((tw, th), Image.LANCZOS)
        x = pad + (i % cols) * (tw + pad)
        y = pad + (i // cols) * (th + pad)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 74, y + 20], fill=(0, 0, 0))
        d.text((x + 6, y + 5), f"t={t}s", fill=(255, 140, 60))
    sheet.save(SCRATCH / out)
    print(f"{SCRATCH / out}  {sheet.size}")


if __name__ == "__main__":
    scene = sys.argv[1] if len(sys.argv) > 1 else "bonk-blueprint"
    times = sys.argv[2].split(",") if len(sys.argv) > 2 else ["0.6", "2.2", "3.6", "5.4", "7.0"]
    out = sys.argv[3] if len(sys.argv) > 3 else "review-sheet.png"
    main(scene, times, out)
