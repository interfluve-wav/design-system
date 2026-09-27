"""Verify a motion asset against the reference clip it was distilled from.

Comparing my render's grammar signature to the reference's measured numbers is a far
stronger check than "it looks right": the whole point of the asset is to reproduce a
*motion behaviour*, and that behaviour is measurable. If the radial correlation, component
growth, ink floor and edge-orientation spread do not land near the reference's, the asset
does not actually do what it claims.

Ground handling matters here: this asset is dark-ground (orange on black) while the
reference reel is light-ground (#f0f0f0). Measuring one with the other's assumption is a
trap that has fired repeatedly, so ink is always taken relative to the frame's own median.

Usage:  python3 verify.py <scene.html> <reference-clip-name>
"""
import io
import json
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path("/Users/suhaas/Pictures/motion - design - assets")
CLIPS = Path("/Users/suhaas/Pictures/Motion Design Reference Vids/clips")
PORT = 8765
N = 24


# ── the same measurements the reference was scored with ─────────────────────
def ground(fr):
    return float(np.median(fr))


def ink(fr, g):
    return np.abs(fr - g) > max(18.0, 0.07 * 255)


def bbox(m):
    ys, xs = np.nonzero(m)
    return None if not len(xs) else (xs.min(), ys.min(), xs.max(), ys.max())


def components(m, minpx=12):
    h, w = m.shape
    seen = np.zeros_like(m, bool)
    n = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if not m[y, x] or seen[y, x]:
                continue
            q, size = deque([(y, x)]), 0
            seen[y, x] = True
            while q:
                cy, cx = q.popleft()
                size += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if size >= minpx:
                n += 1
    return n


def orientations(fr, g):
    """Gradient orientation, weighted histogram.

    These bins are EDGE NORMALS, not edge directions, and mislabelling them cost
    two wrong builds of one asset. Bin 0 means a horizontal gradient, which is a
    VERTICAL edge. So: bin0 = vertical edges (letterform stems), bin1 = 90-degree
    normals = horizontal edges (rules, rails), bin2/bin3 = the two diagonals.
    """
    m = ink(fr, g).astype(np.float32)
    gy = np.zeros_like(fr); gx = np.zeros_like(fr)
    gy[1:-1] = m[2:] - m[:-2]
    gx[:, 1:-1] = m[:, 2:] - m[:, :-2]
    mag = np.hypot(gx, gy)
    if mag.sum() < 1e-6:
        return [0.0] * 4
    ang = (np.degrees(np.arctan2(gy, gx)) + 180) % 180
    h = [mag[(ang >= a) & (ang < a + 45)].sum() for a in (0, 45, 90, 135)]
    s = sum(h) or 1.0
    return [round(100 * v / s, 1) for v in h]


def radial_linear(frames, g):
    ms = [ink(f, g) for f in frames]
    h, w = ms[0].shape
    yy, xx = np.mgrid[0:h, 0:w]
    rad = np.hypot(yy - h / 2, xx - w / 2).ravel()
    d = np.abs(np.diff(np.stack(ms), axis=0)).reshape(len(ms) - 1, -1).mean(0)
    if d.sum() < 1e-6 or d.std() == 0:
        return 0.0, 0.0
    return (round(float(np.corrcoef(rad, d)[0, 1]), 3),
            round(float(np.corrcoef((yy / h).ravel(), d)[0, 1]), 3))


def score(frames):
    """The signature, computed identically for the reference GIF and for a render."""
    g = ground(frames[0])
    ms = [ink(f, g) for f in frames]
    inks = [round(100 * m.mean(), 3) for m in ms]
    h, w = ms[0].shape
    boxes = [bbox(m) for m in ms]
    areas = [0 if b is None else (b[2] - b[0] + 1) * (b[3] - b[1] + 1) for b in boxes]
    comps = [components(m) for m in ms]
    deltas = [round(float(np.abs(ms[i+1].astype(int) - ms[i].astype(int)).mean()), 4)
              for i in range(len(ms) - 1)]
    r, l = radial_linear(frames, g)
    return {
        "ink_start": inks[0], "ink_min": min(inks), "ink_max": max(inks),
        "peak_phase": round(int(np.argmax(inks)) / (len(inks) - 1), 2),
        "components": (comps[0], max(comps), comps[-1]),
        "bbox_span": round(max(areas) / (h * w), 3),
        "orient": orientations(frames[len(frames) // 2], g),
        "radial_corr": r, "linear_corr": l,
        "delta_mean": round(float(np.mean(deltas)), 4),
        "delta_max": max(deltas),
        "still": sum(1 for d in deltas if d < 0.02),
        "n": len(deltas),
    }


def ref_frames(name, n=N, w=320):
    im = Image.open(CLIPS / f"{name}.gif")
    total = 0
    try:
        while True:
            im.seek(total); total += 1
    except EOFError:
        pass
    idx = sorted({round(i * (total - 1) / (n - 1)) for i in range(n)})
    out = []
    for i in idx:
        im.seek(i)
        out.append(np.asarray(im.convert("RGB")
                   .resize((w, round(w * im.height / im.width)), Image.LANCZOS)
                   .convert("L"), dtype=np.float32))
    return out


def render_frames(url, n=N, w=320):
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url, wait_until="load")
        # __ready is a Promise when the page waits for its font; evaluate awaits it.
        try:
            pg.wait_for_function("() => window.__ready === true", timeout=4000)
        except Exception:
            pg.evaluate("() => window.__ready")
        pg.wait_for_timeout(120)
        dur = pg.evaluate("() => window.__duration")
        out = []
        for i in range(n):
            t = dur * i / (n - 1)
            pg.evaluate(f"() => window.__seek({t})")
            img = Image.open(io.BytesIO(pg.screenshot()))
            out.append(np.asarray(img.resize((w, round(w * img.height / img.width)),
                                             Image.LANCZOS).convert("L"), dtype=np.float32))
        br.close()
    return out, dur, errs


def fmt(tag, s):
    return (f"  {tag:10s} ink {s['ink_start']:6.3f} -> min {s['ink_min']:6.3f}"
            f" / max {s['ink_max']:6.3f}%  peak@{s['peak_phase']:<5} "
            f"comps {s['components'][0]}->{s['components'][1]}->{s['components'][2]}  "
            f"bbox {s['bbox_span']:.3f}\n"
            f"  {'':10s} radial {s['radial_corr']:+.3f} linear {s['linear_corr']:+.3f}"
            f"   delta mean {s['delta_mean']:.4f} max {s['delta_max']:.4f}"
            f"   still {s['still']}/{s['n']}\n"
            f"  {'':10s} edges vert/horiz/d1/d2 {s['orient']}")


if __name__ == "__main__":
    scene = sys.argv[1]
    ref = sys.argv[2]
    url = f"http://127.0.0.1:{PORT}/{scene}"
    mine, dur, errs = render_frames(url)
    theirs = ref_frames(ref)
    print(f"═══ {scene}  (__duration {dur}s)")
    print(fmt("MINE", score(mine)))
    print(fmt("REF " + ref.split('_')[0], score(theirs)))
    if errs:
        print(f"\n  PAGE ERRORS: {errs[:3]}")
    else:
        print("\n  no pageerror")
