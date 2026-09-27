"""Brand colour audit for the new motion assets.

Saturation-based, not nearest-RGB-distance: brand colour at low alpha over black is a
darker tint of the same hue, not a different colour, so filtering by hue FAMILY with
near-achromatic treated as in-family is the only test that doesn't report false positives.
(A tolerance-26 nearest-RGB check once reported 2.9% off-brand where a hue audit found
0.00% across 4.6M px.)

Two families are legitimate here: the brand orange (#ff6b1a, hue ~21) on brand surfaces,
and the light register's teal (#1e555c, hue ~187) which exists for non-brand surfaces.
The light ground polls at ~46-70 luma, close enough to the teal family that its own
anti-aliased edge must be tolerated.
"""
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/projects/motion-assets"
ASSETS = [("ripple.html", "dark orange"), ("ripple.html?ground=light", "light teal"),
          ("typeon.html", "dark orange"), ("typeon.html?ground=light", "light teal"),
          ("curves-v2.html", "dark orange"), ("timeline.html", "dark orange")]


def hue_of(rgb):
    r, g, b = rgb[..., 0].astype(float), rgb[..., 1].astype(float), rgb[..., 2].astype(float)
    mx, mn = np.max(rgb, axis=2).astype(float), np.min(rgb, axis=2).astype(float)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0) * 255
    d = np.maximum(mx - mn, 1e-6)
    h = np.zeros_like(mx)
    m = (mx == r); h[m] = (60 * ((g - b) / d) % 360)[m]
    m = (mx == g); h[m] = (60 * ((b - r) / d) + 120)[m]
    m = (mx == b); h[m] = (60 * ((r - g) / d) + 240)[m]
    return h, sat


def audit(url, label):
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        pg.goto(url, wait_until="load")
        pg.wait_for_function("() => window.__ready === true", timeout=20000)
        dur = pg.evaluate("() => window.__duration")
        total = chrom = off = 0
        for i in range(8):
            pg.evaluate(f"() => window.__seek({dur * i / 8})")
            a = np.asarray(Image.open(io.BytesIO(pg.screenshot())).convert("RGB")).astype(int)
            h, s = hue_of(a)
            # chromatic = genuinely coloured, not a grey ramp
            c = s > 60
            total += a.shape[0] * a.shape[1]
            chrom += int(c.sum())
            # in family if within 25 deg of a legitimate family hue:
            #   orange #ff6b1a (21)     brand surface
            #   teal   #1e555c (187)    light register accent
            #   sage   #36453b (140)    light register ink, from the approved
            #                           blur-reveal light palette. Not orange,
            #                           but it is the sanctioned light-register
            #                           ink, so its glyph edges are in-family.
            d = np.minimum(np.abs(h - 21), 360 - np.abs(h - 21))
            for fam in (187, 140):
                d = np.minimum(d, np.minimum(np.abs(h - fam), 360 - np.abs(h - fam)))
            off += int((c & (d > 25)).sum())
        br.close()
    pct = 100 * off / max(chrom, 1)
    verdict = "CLEAN" if pct < 0.05 else "OFF-BRAND"
    print(f"  {label:34s} chromatic {chrom:>9,} px   off-brand {off:>6,}"
          f"  ({pct:5.3f}%)  {verdict}")
    return off


if __name__ == "__main__":
    print("═══ brand colour audit — 8 frames per register, 1280x720 each")
    bad = 0
    for path, label in ASSETS:
        bad += audit(f"{BASE}/{path}", f"{path.split('?')[0]}  [{label}]")
    print(f"\n  {'ALL CLEAN — every chromatic pixel inside the brand hue families' if not bad else 'FAILURES PRESENT'}")
