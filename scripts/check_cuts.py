#!/usr/bin/env python3
"""check_cuts.py — how much does the frame dim at each scene crossover?

The claim to test: a crossfade drawn as two alpha-blended passes attenuates both
the content and the ground, because the second pass multiplies the first by
(1 - alpha). So the frame dips mid-crossover.

The baseline is the whole argument. Two earlier attempts got it wrong:
  * versus the MEAN of both neighbours  -> 65% worst  (averaged a dim block with
    one 3x brighter one)
  * versus the OUTGOING hold            -> 38% worst  (adjacent blocks differ from
    2.1 to 8.4 in mean luminance, so "the outgoing hold" is not the level the
    frame *should* be at mid-cut)
The right question is "did the frame go darker than EITHER side?" -> the dimmer of
the two adjacent holds. That is what this measures.

Usage
-----
  python3 scripts/check_cuts.py                       # v4-scenes.html, all cuts
  python3 scripts/check_cuts.py --scene 2 --fps 60
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765"
PAGE = "projects/blurreveal/public/v4-scenes.html"


def luma_of(shot_bytes):
    im = Image.open(__import__("io").BytesIO(shot_bytes)).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    return float((0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).mean())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", type=int, default=0, help="isolate a scene (?scene=N)")
    ap.add_argument("--fps", type=int, default=30, help="crossover sample rate")
    ap.add_argument("--pad", type=float, default=0.45, help="seconds of hold to sample each side")
    args = ap.parse_args(argv)

    url = f"{BASE}/{PAGE}" + (f"?scene={args.scene}" if args.scene else "")
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_context(viewport={"width": 1280, "height": 720}).new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
        pg.goto(url, wait_until="load", timeout=20000)
        pg.evaluate("() => window.__ready")
        blocks = pg.evaluate("() => window.__scenes()")

        step = 1.0 / args.fps
        rows = []
        for i in range(len(blocks) - 1):
            a, c = blocks[i], blocks[i + 1]
            # hold levels either side of the crossover
            pg.evaluate("(t) => window.__seek(t)", (a["holdTo"] - 80) / 1000.0)
            pg.wait_for_timeout(20)
            la = luma_of(pg.screenshot())
            pg.evaluate("(t) => window.__seek(t)", (c["holdFrom"] + 80) / 1000.0)
            pg.wait_for_timeout(20)
            lb = luma_of(pg.screenshot())

            t0 = a["holdTo"] / 1000.0
            t1 = c["holdFrom"] / 1000.0
            trace, ts = [], []
            t = t0
            while t <= t1 + 1e-9:
                pg.evaluate("(t) => window.__seek(t)", t)
                pg.wait_for_timeout(12)
                trace.append(luma_of(pg.screenshot()))
                ts.append((t - t0) * 1000.0)
                t += step
            trace = np.array(trace)
            base = min(la, lb)
            dip = 100.0 * (1.0 - trace.min() / base) if base > 0 else 0.0
            rows.append({
                "cut": f"{a['scene']}->{c['scene']}", "style": c["cut"],
                "holdA": round(la, 2), "holdB": round(lb, 2), "baseline": round(base, 2),
                "min": round(float(trace.min()), 2),
                "at_ms": round(float(ts[int(trace.argmin())]), 0),
                "window_ms": round((t1 - t0) * 1000.0, 0),
                "samples": len(trace), "dip_pct": round(dip, 1),
            })
            print(f"  cut {rows[-1]['cut']:>6}  {rows[-1]['style']:<15} "
                  f"holdA {la:6.2f}  holdB {lb:6.2f}  min {trace.min():6.2f} "
                  f"@ {rows[-1]['at_ms']:>4.0f}ms  dip {dip:5.1f}%")
        b.close()

    dips = np.array([r["dip_pct"] for r in rows]) if rows else np.array([0.0])
    print()
    print(f"  cuts measured        : {len(rows)}")
    print(f"  dip vs dimmer hold   : median {np.median(dips):.1f}%   worst {dips.max():.1f}%   "
          f"best {dips.min():.1f}%")
    print("  (baseline = the DIMMER of the two adjacent holds — the frame going darker")
    print("   than either side is the real defect; a bigger number means a bigger flash)")
    if errs:
        print(f"  page errors: {errs[:2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
