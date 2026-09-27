#!/usr/bin/env python3
"""brand_audit.py — is every chromatic pixel inside the brand hue family?

The trap this exists to avoid (GOTCHAS §4.2): a nearest-RGB match flags
anti-aliased greys between ink and ground as violations and invents thousands
of false positives on a perfectly correct render. Colour at low alpha over
black is *dark*, not *off-brand* — hue is unchanged.

So this audits by HUE FAMILY:
  * near-achromatic pixels (saturation below --sat) are skipped, not failed;
  * everything else must sit within --hue-tol degrees of an allowed hue;
  * the hue histogram is printed so the verdict is legible rather than a number
    you have to take on faith.

Usage
-----
  python3 scripts/brand_audit.py './frames/*.png' --allowed ff6b1a,ffffff,000000
  python3 scripts/brand_audit.py frames/ --hue-tol 25 --sat 0.15 --json out.json

Exit code is 1 if any off-hue pixel is found, 0 otherwise (CI-usable).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np
from PIL import Image


# ── colour maths ─────────────────────────────────────────────────────────────

def hex_to_rgb(h: str) -> tuple:
    h = h.strip().lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hsv(arr: np.ndarray):
    """Vectorised RGB->HSV. arr: float (N,3) in 0..1. Returns hue (deg), sat, val."""
    r, g, b = arr[:, 0], arr[:, 1], arr[:, 2]
    mx = arr.max(axis=1)
    mn = arr.min(axis=1)
    d = mx - mn
    denom = np.maximum(d, 1e-9)
    s = np.where(mx > 0, d / np.maximum(mx, 1e-9), 0.0)

    h = np.zeros_like(mx)
    idx = np.argmax(arr, axis=1)
    nz = d > 0
    m_r = nz & (idx == 0)
    m_g = nz & (idx == 1)
    m_b = nz & (idx == 2)
    h[m_r] = ((g - b) / denom)[m_r] % 6.0
    h[m_g] = ((b - r) / denom)[m_g] + 2.0
    h[m_b] = ((r - g) / denom)[m_b] + 4.0
    return (h * 60.0) % 360.0, s, mx


def hue_delta(a, b):
    """Shortest angular distance between two hues, in degrees."""
    d = np.abs(a - b) % 360.0
    return np.minimum(d, 360.0 - d)


# ── audit ────────────────────────────────────────────────────────────────────

def audit_image(path, allowed_hex, hue_tol, sat_min, val_min):
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im).reshape(-1, 3).astype(np.float32) / 255.0
    hue, sat, val = rgb_to_hsv(arr)

    allowed = []
    for a in allowed_hex:
        hh, ss, vv = rgb_to_hsv(np.array([hex_to_rgb(a)], dtype=np.float32) / 255.0)
        allowed.append((a, float(hh[0]), float(ss[0])))
    allowed_hues = np.array([a[1] for a in allowed if a[2] > sat_min], dtype=np.float32)

    chromatic = (sat >= sat_min) & (val >= val_min)
    n_chrom = int(chromatic.sum())
    if n_chrom == 0:
        return {
            "path": os.path.basename(path), "px": int(arr.shape[0]), "chromatic": 0,
            "off_hue": 0, "off_hue_pct_chromatic": 0.0, "off_hue_pct_total": 0.0,
            "top_off": [], "hist": [0] * 36,
        }

    if len(allowed_hues) == 0:
        # every permitted colour is achromatic -> any chromatic pixel is off-brand
        off = chromatic.copy()
        nearest = np.zeros(n_chrom, dtype=np.float32)
    else:
        hh = hue[chromatic]
        dists = np.stack([hue_delta(hh, ah) for ah in allowed_hues], axis=1)
        nearest = dists.min(axis=1)
        off = np.zeros_like(chromatic)
        off[np.where(chromatic)[0]] = nearest > hue_tol

    n_off = int(off.sum())
    hist = [0] * 36
    for h in hue[chromatic] if n_chrom < 400000 else hue[chromatic][::4]:
        hist[min(35, int(h // 10))] += 1

    top_off = []
    if n_off:
        off_idx = np.where(off)[0]
        bucket = (hue[off_idx] // 10).astype(int)
        vals, counts = np.unique(bucket, return_counts=True)
        order = np.argsort(-counts)[:5]
        rgb255 = (arr[off_idx] * 255).astype(int)
        for o in order:
            b = int(vals[o])
            sel = off_idx[bucket == b]
            sample = rgb255[np.where(off_idx == sel[0])[0][0]] if len(sel) else np.zeros(3, int)
            top_off.append({
                "hue_bucket": f"{b * 10}-{b * 10 + 10}",
                "count": int(counts[o]),
                "example_hex": "#%02x%02x%02x" % tuple(sample),
                "nearest_allowed_hue_deg": round(
                    float(nearest[np.where(off_idx == sel[0])[0][0]]) if len(sel) else 0.0, 1),
            })

    return {
        "path": os.path.basename(path), "px": int(arr.shape[0]),
        "chromatic": n_chrom, "off_hue": n_off,
        "off_hue_pct_chromatic": round(100.0 * n_off / n_chrom, 4),
        "off_hue_pct_total": round(100.0 * n_off / arr.shape[0], 4),
        "top_off": top_off, "hist": hist,
    }


def expand(targets):
    out = []
    for t in targets:
        if os.path.isdir(t):
            for ext in ("png", "jpg", "jpeg", "bmp"):
                out += sorted(glob.glob(os.path.join(t, f"*.{ext}")))
        else:
            out += sorted(glob.glob(t))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hue-family brand audit for rendered frames.")
    ap.add_argument("targets", nargs="+", help="image files, globs, or a directory")
    ap.add_argument("--allowed", default="ff6b1a,ffffff,000000",
                    help="comma-separated hex colour families allowed on a brand surface")
    ap.add_argument("--hue-tol", type=float, default=25.0, help="hue tolerance in degrees")
    ap.add_argument("--sat", type=float, default=0.15,
                    help="saturation below this is treated as achromatic (skipped, not failed)")
    ap.add_argument("--val", type=float, default=0.10,
                    help="value (brightness) below this is skipped: #010100 has S=1.0 by "
                         "the ratio definition while being visually black, and that alone "
                         "manufactures thousands of phantom off-hue pixels")
    ap.add_argument("--json", default=None, help="write the full result set here")
    ap.add_argument("--quiet", action="store_true", help="summary only, no histogram")
    args = ap.parse_args(argv)

    allowed = [a for a in args.allowed.split(",") if a.strip()]
    files = expand(args.targets)
    if not files:
        print("no images matched", file=sys.stderr)
        return 2

    allowed_buckets = set()
    for a in allowed:
        hh, ss, vv = rgb_to_hsv(np.array([hex_to_rgb(a)], dtype=np.float32) / 255.0)
        if ss[0] > args.sat:
            allowed_buckets.add(int(hh[0] // 10) * 10)

    results = [audit_image(f, allowed, args.hue_tol, args.sat, args.val) for f in files]

    tot_px = sum(r["px"] for r in results)
    tot_chrom = sum(r["chromatic"] for r in results)
    tot_off = sum(r["off_hue"] for r in results)
    hist = np.zeros(36, dtype=np.int64)
    for r in results:
        hist += np.array(r["hist"], dtype=np.int64)

    print(f"brand_audit  {len(results)} frame(s)")
    print(f"  allowed hue families : {', '.join(allowed)}   (tol +/-{args.hue_tol:g} deg)")
    print(f"  saturation cut       : < {args.sat:g} treated as achromatic (skipped)")
    print(f"  value cut            : < {args.val:g} treated as black (skipped)")
    print(f"  total pixels         : {tot_px:,}")
    print(f"  chromatic pixels     : {tot_chrom:,}  ({100.0 * tot_chrom / max(tot_px, 1):.2f}% of image)")
    print(f"  OFF-HUE pixels       : {tot_off:,}  "
          f"({100.0 * tot_off / max(tot_chrom, 1):.4f}% of chromatic, "
          f"{100.0 * tot_off / max(tot_px, 1):.4f}% of total)")

    if not args.quiet and tot_chrom:
        print("  hue histogram (chromatic px, 10 deg buckets):  [* = inside an allowed family]")
        peak = max(1, int(hist.max()))
        for i, c in enumerate(hist):
            if c == 0:
                continue
            bar = "#" * max(1, int(round(36.0 * c / peak)))
            marker = " *" if i * 10 in allowed_buckets else ""
            print(f"    {i * 10:3d}-{i * 10 + 10:3d} deg {c:>10,}  {bar}{marker}")

    for r in results:
        if r["off_hue"]:
            print(f"  ! {r['path']}: {r['off_hue']:,} off-hue px "
                  f"({r['off_hue_pct_chromatic']:.2f}% of chromatic)")
            for t in r["top_off"]:
                print(f"      hue {t['hue_bucket']} deg  n={t['count']:,}  "
                      f"e.g. {t['example_hex']}  ({t['nearest_allowed_hue_deg']:.0f} deg from allowed)")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"allowed": allowed, "hue_tol": args.hue_tol, "sat": args.sat,
                       "val": args.val,
                       "total_px": tot_px, "chromatic_px": tot_chrom, "off_hue_px": tot_off,
                       "frames": results}, fh, indent=2)
        print(f"  wrote {args.json}")

    verdict = "PASS - 0 off-hue px" if tot_off == 0 else f"FAIL - {tot_off:,} off-hue px"
    print(f"  verdict: {verdict}")
    return 0 if tot_off == 0 else 1


def _h(hexs):
    return float(rgb_to_hsv(np.array([hex_to_rgb(hexs)], dtype=np.float32) / 255.0)[0][0])


if __name__ == "__main__":
    sys.exit(main())
