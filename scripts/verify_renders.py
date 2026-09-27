#!/usr/bin/env python3
"""verify_renders.py — what in this folder actually renders, measured not assumed.

Every claim in the docs is supposed to be backed by a run. This is that run.
It does two passes:

  STATIC   extract every literal #hex from an HTML file and classify it against
           the brand family (design.md: #ff6b1a + black + white only). This is
           how a file gets caught for having ten off-brand colours before you
           build on it (GOTCHAS §4.1).

  RUNTIME  load the page in headless Chromium over http://127.0.0.1:8765,
           collect page/console errors, wait for window.__ready, then either
           seek through the whole timeline (pages that expose __seek+__duration)
           or sample live. Measures per-frame ink% and mean luminance, runs the
           hue-family brand audit, and for pages that expose __scenes() checks
           every timed block individually.

Nothing here trusts a comment in the source, including its own. Run it, read it.

Usage
-----
  python3 scripts/verify_renders.py                 # everything
  python3 scripts/verify_renders.py --only v4       # substring filter
  python3 scripts/verify_renders.py --static-only
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from brand_audit import rgb_to_hsv, hex_to_rgb, hue_delta  # noqa: E402

BASE = "http://127.0.0.1:8765"
OUT = os.path.join(os.path.expanduser("~"), ".hermes", "cache", "scratch", "verify")
BRAND = ["#ff6b1a", "#ffffff", "#000000"]
HUE_TOL = 25.0
SAT = 0.15
VAL_MIN = 0.10
VIEWPORT = {"width": 1280, "height": 720}
SEEK_FRAMES = 16
LIVE_SHOTS = 5
LIVE_GAP_MS = 420

# (label, path, hooks)  hooks: seek | scenes | theme(rebuilt how) | extras
# Paths are relative to ROOT and carry the 2026-09-27 `projects/` prefix -- the
# refactor moved every entry point and this list silently reported 15x MISSING
# until it was fixed. If a label shows MISSING, check the path before the page.
PAGES = [
    ("blurreveal-v4",     "projects/blurreveal/public/v4-scenes.html",       {"seek": True, "scenes": True, "theme": "rebuild", "isolate": True}),
    ("blurreveal-v4-lt",  "projects/blurreveal/public/v4-light-scenes.html", {"seek": True, "scenes": True, "theme": "rebuild"}),
    ("blueprint",         "projects/blueprint/public/bonk-blueprint.html",   {"seek": True, "theme": "applyTheme"}),
    ("blueprint-v2",      "projects/blueprint/public/bonk-blueprint-v2.html", {"seek": True, "theme": "applyTheme"}),
    ("blueprint-v3-sup",  "projects/blueprint/public/bonk-blueprint-v3-sup.html", {"seek": True, "theme": "applyTheme"}),
    ("motion-system-v1",  "projects/motion-system/bonk-motion-system.html",  {}),
    ("motion-system-v2",  "projects/motion-system/bonk-motion-system-v2.html", {"seek": True, "theme": "applyTheme"}),
    ("motion-system-v3",  "projects/motion-system/bonk-motion-system-v3.html", {"seek": True, "theme": "applyTheme"}),
    ("dotcut-demo",       "projects/dotcut/public/dotcut-demo.html",         {"presets": True}),
    ("bonk-logo",         "projects/dotcut/public/bonk-logo.html",           {}),
    ("bonk-wordmark",     "projects/dotcut/public/bonk-wordmark.html",       {}),
    ("design-tiles",      "projects/design-tiles/public/design-tiles-demo.html", {}),
    ("libsdev",           "projects/libs-dev/bonk-libsdev.html",             {}),
    ("logo-lockup",       "projects/logo/logo-lockup-compare.html",          {}),
    ("bonk-sup",          "projects/logo/bonk-sup.html",                     {}),
    ("font-specimen",     "fonts/specimen.html",                             {}),
    ("intro-preview",     "projects/motion-system/bonk-intro-preview.html",  {}),
]

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


# ── STATIC ───────────────────────────────────────────────────────────────────

def norm_hex(h):
    h = h.lower()
    if len(h) == 4:
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def brand_hexes():
    out = {}
    for h in BRAND:
        rgb = np.array([hex_to_rgb(h)], dtype=np.float32)
        hh, ss, vv = rgb_to_hsv(rgb / 255.0)
        out[h] = (float(hh[0]), float(ss[0]), float(vv[0]))
    return out


def strip_comments(txt):
    """Comments are not colours. v1's off-brand hex survived in v4's header
    comment describing what v1 got wrong, and the naive scan duly reported v4
    as having four off-brand hex — a false positive of exactly the kind this
    folder keeps producing."""
    txt = re.sub(r"<!--.*?-->", " ", txt, flags=re.S)
    txt = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
    txt = re.sub(r"^[ \t]*//.*$", " ", txt, flags=re.M)
    return txt


def static_colours(path):
    with open(path, "r", errors="replace") as fh:
        txt = strip_comments(fh.read())
    counts = Counter(norm_hex(h) for h in HEX_RE.findall(txt))
    b = brand_hexes()
    off, on = {}, {}
    for h, n in counts.items():
        rgb = np.array([hex_to_rgb(h)], dtype=np.float32)
        hh, ss, vv = rgb_to_hsv(rgb / 255.0)
        if ss[0] <= SAT:
            on[h] = n
            continue
        d = min(hue_delta(np.array([hh[0]]), np.array([b[k][0]]))[0]
                for k in b if b[k][1] > SAT)
        (on if d <= HUE_TOL else off)[h] = n
    return counts, on, off


# ── RUNTIME helpers ──────────────────────────────────────────────────────────

def measure(shot_bytes):
    im = Image.open(__import__("io").BytesIO(shot_bytes)).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return im, 100.0 * float((L > 60).mean()), float(L.mean())


def hue_counts(im):
    a = np.asarray(im).reshape(-1, 3).astype(np.float32) / 255.0
    hue, sat, val = rgb_to_hsv(a)
    # value floor matters: #010100 reads S=1.0 by the ratio definition while being
    # visually black. Without the floor it invents thousands of phantom off-hue px.
    chrom = (sat >= SAT) & (val >= VAL_MIN)
    res = {"chromatic": int(chrom.sum()), "off_hue": 0, "orange": 0, "green": 0}
    if res["chromatic"] == 0:
        return res
    hh = hue[chrom]
    d_o = hue_delta(hh, np.array([20.0]))
    d_g = hue_delta(hh, np.array([155.0]))
    res["orange"] = int((d_o <= HUE_TOL).sum())
    res["green"] = int((d_g <= HUE_TOL).sum())
    res["off_hue"] = int((np.minimum(d_o, d_g) > HUE_TOL).sum())
    return res


def sweep(page, hooks, frame_dir, label):
    """Return (frames, stats). Frames are (t, ink%, luma, hue_counts)."""
    os.makedirs(frame_dir, exist_ok=True)
    durs = page.evaluate("() => (typeof window.__duration === 'number' ? window.__duration : null)")
    out = []
    if hooks.get("seek") and durs:
        # 16 samples across the loop, including both edges
        ts = [round(durs * i / (SEEK_FRAMES - 1), 3) for i in range(SEEK_FRAMES)]
        for i, t in enumerate(ts):
            page.evaluate("(t) => window.__seek(t)", t)
            page.wait_for_timeout(30)
            b = page.screenshot()
            im, ink, lum = measure(b)
            im.save(os.path.join(frame_dir, f"{i:03d}.png"))
            out.append((t, ink, lum, hue_counts(im)))
    else:
        for i in range(LIVE_SHOTS):
            b = page.screenshot()
            im, ink, lum = measure(b)
            im.save(os.path.join(frame_dir, f"{i:03d}.png"))
            out.append((i * LIVE_GAP_MS / 1000.0, ink, lum, hue_counts(im)))
            page.wait_for_timeout(LIVE_GAP_MS)
    return out, durs


def check_blocks(page):
    """v4-style: verify every timed block draws during its hold window."""
    blocks = page.evaluate("() => window.__scenes()")
    res = []
    for b in blocks:
        inks = []
        for frac in (0.25, 0.5, 0.75):
            t = b["holdFrom"] / 1000.0 + (b["holdTo"] - b["holdFrom"]) / 1000.0 * frac
            page.evaluate("(t) => window.__seek(t)", t)
            page.wait_for_timeout(25)
            _, ink, lum = measure(page.screenshot())
            inks.append(ink)
        res.append({"i": b["i"], "text": (b["text"] or "")[:44], "hold_ms": b["hold"],
                    "min_ink": round(min(inks), 3), "luma": round(lum, 1)})
    return res


def theme_flip(page, mode):
    """Count orange vs green px before/after a flip. Texture-baked colour cannot
    see CSS, so this is the only honest test of the theming contract.

    Both accent tokens get flipped. Flipping `--accent` alone leaves `--accent-soft`
    (#ffb37a — hue 26 deg, inside the orange family) still orange, which reads as a
    failed flip when it is really an incomplete test."""
    before = hue_counts(Image.open(__import__("io").BytesIO(page.screenshot())).convert("RGB"))
    page.evaluate("""() => {
        const s = document.documentElement.style;
        s.setProperty('--accent', '#00ff85');
        s.setProperty('--accent-soft', '#00ff85');
    }""")
    page.evaluate("() => window.__rebuild ? window.__rebuild() : window.__applyTheme()")
    page.wait_for_timeout(80)
    after = hue_counts(Image.open(__import__("io").BytesIO(page.screenshot())).convert("RGB"))
    page.evaluate("""() => {
        const s = document.documentElement.style;
        s.setProperty('--accent', '#ff6b1a');
        s.setProperty('--accent-soft', '#ffb37a');
    }""")
    page.evaluate("() => window.__rebuild ? window.__rebuild() : window.__applyTheme()")
    page.wait_for_timeout(80)
    restored = hue_counts(Image.open(__import__("io").BytesIO(page.screenshot())).convert("RGB"))
    return before, after, restored


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="substring filter on the label")
    ap.add_argument("--static-only", action="store_true")
    ap.add_argument("--json", default=os.path.join(OUT, "verify.json"))
    args = ap.parse_args(argv)

    os.makedirs(OUT, exist_ok=True)
    pages = [p for p in PAGES if not args.only or args.only in p[0]]
    report = {"static": {}, "runtime": {}}

    print("=" * 100)
    print("STATIC — literal hex colours per file, classified against "
          f"{', '.join(BRAND)} (+/-{HUE_TOL:g} deg hue, sat>{SAT})")
    print("=" * 100)
    for label, rel, _ in pages:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print(f"  {label:<17} MISSING  {rel}")
            continue
        counts, on, off = static_colours(p)
        vex = ", ".join(f"{h}x{n}" for h, n in sorted(off.items(), key=lambda x: -x[1])[:6])
        verdict = "brand-clean" if not off else f"{len(off)} off-brand hex"
        print(f"  {label:<17} {len(counts):>3} hex  {verdict:<20} {vex}")
        report["static"][label] = {"hex_total": len(counts), "on_brand": on, "off_brand": off}

    print()
    print("  (near-achromatic hex is counted as in-family — a grey step between ink and ground\n"
          "   is not a brand violation, which is the false positive GOTCHAS 4.2 is about.)")

    if args.static_only:
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=2)
        return 0

    print()
    print("=" * 100)
    print(f"RUNTIME — headless Chromium {VIEWPORT['width']}x{VIEWPORT['height']} against {BASE}")
    print("=" * 100)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for label, rel, hooks in pages:
            url = f"{BASE}/{rel}"
            ctx = browser.new_context(viewport=VIEWPORT)
            page = ctx.new_page()
            errors, cons = [], []
            page.on("pageerror", lambda e: errors.append(str(e).split("\n")[0][:160]))
            page.on("console", lambda m: cons.append(m.text[:160]) if m.type == "error" else None)
            entry = {"url": url, "errors": errors, "console": cons}
            try:
                page.goto(url, wait_until="load", timeout=20000)
                has_ready = page.evaluate("() => typeof window.__ready !== 'undefined'")
                ready_ok = None
                if has_ready:
                    try:
                        ready_ok = page.evaluate(
                            "() => window.__ready.then(() => true).catch(e => 'rejected: ' + e)")
                    except Exception as e:
                        ready_ok = f"eval failed: {str(e)[:80]}"
                else:
                    page.wait_for_timeout(1200)
                entry["ready"] = ready_ok

                frames, dur = sweep(page, hooks, os.path.join(OUT, "frames", label), label)
                inks = [f[1] for f in frames]
                lums = [f[2] for f in frames]
                hue = Counter()
                for f in frames:
                    for k, v in f[3].items():
                        hue[k] += v
                entry.update({
                    "duration_s": dur,
                    "frames": len(frames),
                    "ink_min": round(min(inks), 3), "ink_max": round(max(inks), 3),
                    "ink_mean": round(float(np.mean(inks)), 3),
                    "luma_min": round(min(lums), 2), "luma_max": round(max(lums), 2),
                    "dead_frames": int(sum(1 for i in inks if i < 0.01)),
                    "hue": dict(hue),
                    "seek": bool(hooks.get("seek") and dur),
                })

                print(f"\n  [{label}]  {rel}")
                print(f"    ready={ready_ok}   duration={dur}   frames={len(frames)} "
                      f"({'seek' if entry['seek'] else 'live'})")
                print(f"    ink%  min {entry['ink_min']:>6.3f}  max {entry['ink_max']:>6.3f}  "
                      f"mean {entry['ink_mean']:>6.3f}   dead frames {entry['dead_frames']}")
                print(f"    luma  min {entry['luma_min']:>6.2f}  max {entry['luma_max']:>6.2f}")
                print(f"    hue   chromatic {hue['chromatic']:,}  orange {hue['orange']:,}  "
                      f"green {hue['green']:,}  OFF-HUE {hue['off_hue']:,}")
                if errors:
                    print(f"    PAGE ERRORS: {errors[:3]}")
                if cons:
                    print(f"    CONSOLE ERRORS: {cons[:3]}")

                if entry["dead_frames"]:
                    dead = [(round(f[0], 2), round(f[1], 3)) for f in frames if f[1] < 0.01]
                    print(f"    ! dead frames at t={dead[:6]}")
                    entry["dead_at"] = dead

                if hooks.get("scenes"):
                    blocks = check_blocks(page)
                    bad = [b for b in blocks if b["min_ink"] < 0.05]
                    entry["blocks"] = blocks
                    entry["blocks_bad"] = [b["i"] for b in bad]
                    print(f"    blocks: {len(blocks) - len(bad)}/{len(blocks)} draw inside their hold "
                          f"(min ink {min(b['min_ink'] for b in blocks):.3f}%)")
                    for b in bad:
                        print(f"      ! block {b['i']} min_ink={b['min_ink']}  {b['text']!r}")

                if hooks.get("theme"):
                    b, a, r = theme_flip(page, hooks["theme"])
                    ok = a["green"] > 0 and a["orange"] == 0
                    back = r["orange"] > 0 and r["green"] == 0
                    entry["theme"] = {"before": b, "after": a, "restored": r,
                                      "flip_ok": ok, "restore_ok": back}
                    print(f"    theme flip: orange {b['orange']:,} -> {a['orange']:,} / "
                          f"green {b['green']:,} -> {a['green']:,}   "
                          f"{'OK' if ok else 'FAIL'}   restore {'OK' if back else 'FAIL'}")

                if hooks.get("isolate"):
                    iso = {}
                    for s in (1, 2, 3, 4):
                        pg2 = ctx.new_page()
                        e2 = []
                        pg2.on("pageerror", lambda e: e2.append(str(e)[:100]))
                        pg2.goto(f"{url}?scene={s}", wait_until="load", timeout=20000)
                        pg2.wait_for_timeout(250)
                        try:
                            pg2.evaluate("() => window.__ready")
                        except Exception:
                            pass
                        pg2.evaluate("() => window.__seek(1.0)")
                        _, ink, _ = measure(pg2.screenshot())
                        iso[s] = {"ink": round(ink, 3), "errors": e2[:1]}
                        pg2.close()
                    entry["isolate"] = iso
                    print("    ?scene=N isolation: " + "  ".join(
                        f"scene{s}={v['ink']:.2f}%" for s, v in iso.items()))

                if hooks.get("presets"):
                    keys = page.evaluate("() => (typeof PRESETS !== 'undefined') ? PRESETS.map(p => p.name) : null")
                    pals = page.evaluate("() => (typeof PALETTES !== 'undefined') ? PALETTES.length : null")
                    entry["presets"] = {"names": keys, "current_palettes": pals}
                    print(f"    presets: {keys}   active palettes: {pals}")

            except Exception as e:
                entry["fatal"] = str(e)[:200]
                print(f"\n  [{label}]  {rel}\n    FATAL: {str(e)[:200]}")
            report["runtime"][label] = entry
            ctx.close()
        browser.close()

    with open(args.json, "w") as fh:
        json.dump(report, fh, indent=2)
    print(f"\nwrote {args.json}")
    print(f"frames under {os.path.join(OUT, 'frames')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
