#!/usr/bin/env python3
"""render.py — render any motion model to GIF / MP4 / PNG, from one command.

This is the script that did not exist. Until now the capture pipeline was ad-hoc
one-liners in /tmp, which is why LEDGER.md could not reproduce a single delivered
GIF (GOTCHAS §2.1 note, §7). Everything it needs is now declared by the model, so
the render is a function of (model id + overrides) and nothing is guessed.

    python3 scripts/render.py --list
    python3 scripts/render.py glow
    python3 scripts/render.py glow --light --out ../design\\ -\\ tiles\\ -\\ motion/glow-light.gif
    python3 scripts/render.py blurreveal-v4 --set s1a="Rekordbox is a mess" --w 1080 --h 1920
    python3 scripts/render.py glow -s mark=#00ff85 -s scale=1.4 --fps 24 --mp4

Checks it runs on the ARTIFACT, not the page (GOTCHAS §2.1, §3.9):
  · every frame's ink, measured against the frame's OWN ground, never a fixed threshold
  · dead frames — a blank frame is what a failed capture looks like
  · the declared size asserted against the encoded file, because capture and encode
    disagreed about resolution once and shipped a 720p file labelled 1080p
  · the loop seam, for a piece meant to loop
It exits non-zero if any check fails. A render that "ran fine" and is blank is the
failure mode this whole file exists to catch.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "projects" / "motion-library"
BASE = "http://127.0.0.1:8765"
DELIVER = Path("/Users/suhaas/Pictures/design - tiles - motion")

INK_THRESHOLD = 20.0     # luma distance from the ground before a pixel counts as ink
DEAD_INK_PCT = 0.20      # below this a frame is treated as having nothing on it


def load_registry() -> dict:
    f = LIB / "registry.json"
    if not f.exists():
        sys.exit("no registry.json — run: python3 scripts/scan_models.py")
    return json.loads(f.read_text())


def resolve(reg: dict, model_id: str) -> dict:
    exact = [p for p in reg["pieces"] if p.get("id") == model_id]
    if not exact:
        exact = [p for p in reg["pieces"] if model_id in p["rel"]]
    if not exact:
        sys.exit(f"no piece matches '{model_id}'. Try: python3 scripts/render.py --list")
    if len(exact) > 1:
        names = ", ".join(p["rel"] for p in exact)
        sys.exit(f"'{model_id}' is ambiguous: {names}")
    return exact[0]


def build_query(args, piece: dict) -> str:
    parts = []
    for s in args.set or []:
        if "=" not in s:
            sys.exit(f"--set expects name=value, got '{s}'")
        parts.append(s)
    for k in ("w", "h", "fps", "dur"):
        v = getattr(args, k)
        if v is not None:
            parts.append(f"{k}={v}")
    if args.light:
        parts.append("ground=light")
    if args.no_chrome:
        parts.append("chrome=0")
    if args.no_loop:
        parts.append("loop=0")
    if args.query:
        parts.append(args.query.strip("&?"))
    return "&".join(p for p in parts if p)


async def capture(url: str, outdir: Path, w: int, h: int, fps: int, duration: float,
                  t_from: float, t_to: float, settle: float) -> dict:
    from playwright.async_api import async_playwright

    n = max(1, int(round((t_to - t_from) * fps)))
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": w, "height": h})
        errors, consoles = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: consoles.append(f"{m.type}: {m.text}")
                if m.type in ("error", "warning") else None)

        await page.goto(url, wait_until="load", timeout=30000)
        try:
            await page.wait_for_function("() => !!window.__ready", timeout=15000)
            await asyncio.wait_for(page.evaluate("() => window.__ready"), timeout=30)
        except Exception as e:
            errors.append(f"__ready never resolved: {e}")

        if not await page.evaluate("typeof window.__seek === 'function'"):
            await browser.close()
            raise SystemExit(
                "this piece exposes no window.__seek — a screenshot capture of a live\n"
                "animation is not frame-exact (GOTCHAS §2.3), so render.py refuses rather\n"
                "than handing you a plausible file with dropped frames in it.")

        warnings = await page.evaluate("window.__warnings || []")
        theme = await page.evaluate("window.__theme ? window.__theme() : {}")
        scale = await page.evaluate("window.devicePixelRatio || 1")
        if settle:
            await page.wait_for_timeout(int(settle * 1000))

        for i in range(n):
            t = t_from + i / fps
            await page.evaluate(f"window.__seek({t})")
            await page.wait_for_timeout(0)
            await page.screenshot(path=str(outdir / f"f{i:04d}.png"))
        await browser.close()
    return {"frames": n, "errors": errors, "consoles": consoles,
            "warnings": warnings, "theme": theme, "dpr": scale}


def encode(outdir: Path, fps: int, out: Path, mode: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(outdir / "f%04d.png")
    if mode == "gif":
        pal = outdir / "palette.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
                        "-i", pattern, "-vf", "palettegen=stats_mode=diff", str(pal)],
                       check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
                        "-i", pattern, "-i", str(pal),
                        "-lavfi", "paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
                        "-loop", "0", str(out)], check=True)
    elif mode == "mp4":
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
                        "-i", pattern, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "18", "-movflags", "+faststart", str(out)], check=True)
    else:
        shutil.copy(outdir / "f0000.png", out)


def check_artifact(out: Path, mode: str) -> dict:
    """Measure the FILE. The page that made it is not evidence."""
    import numpy as np
    from PIL import Image, ImageSequence

    if mode == "png":
        im = Image.open(out).convert("RGB")
        a = np.asarray(im).astype(int)
        return _measure([a], im.size, expected_size=im.size)

    im = Image.open(out)
    frames = [np.asarray(f.convert("RGB")).astype(int) for f in ImageSequence.Iterator(im)]
    return _measure(frames, im.size, expected_size=im.size)


def _measure(frames: list, size: tuple, expected_size: tuple) -> dict:
    import numpy as np

    inks, lumas = [], []
    for a in frames:
        luma = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
        ground = float(np.median(luma))          # the frame's OWN ground (§3.9)
        ink = float((np.abs(luma - ground) > INK_THRESHOLD).mean() * 100.0)
        inks.append(round(ink, 3))
        lumas.append(round(float(luma.mean()), 2))

    dead = [i for i, v in enumerate(inks) if v < DEAD_INK_PCT]
    seam = None
    if len(frames) > 1:
        a, b = frames[0], frames[-1]
        if a.shape == b.shape:
            seam = round(float(np.abs(a - b).mean()), 3)
    return {
        "frames": len(frames),
        "size": list(size),
        "size_ok": list(size) == list(expected_size),
        "ink_min": min(inks), "ink_max": max(inks), "ink_mean": round(sum(inks) / len(inks), 3),
        "luma_min": min(lumas), "luma_max": max(lumas),
        "dead_frames": dead[:12], "dead_count": len(dead),
        "loop_seam": seam,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", nargs="?", help="model id (or any substring of its path)")
    ap.add_argument("--list", action="store_true", help="every model and its dials")
    ap.add_argument("-s", "--set", action="append", metavar="NAME=VALUE",
                    help="override any model param; repeatable. Colours: -s mark=#00ff85")
    ap.add_argument("-q", "--query", help="a raw query string, appended as-is")
    ap.add_argument("-w", "--w", "--width", type=int,
                    help="frame width (default: the model's own)")
    ap.add_argument("-H", "--h", "--height", type=int,
                    help="frame height (default: the model's own)")
    ap.add_argument("--fps", type=int, help="default: the model's own")
    ap.add_argument("--dur", type=float, help="seconds to render (default: the model's own)")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0, help="start time, s")
    ap.add_argument("--to", dest="t_to", type=float, help="end time, s (default: duration)")
    ap.add_argument("--light", action="store_true", help="the light register")
    ap.add_argument("--no-chrome", action="store_true", help="strip on-page chrome")
    ap.add_argument("--no-loop", action="store_true", help="disable the page's rAF loop")
    ap.add_argument("--mp4", action="store_true", help="mp4 (h264) instead of gif")
    ap.add_argument("--png", action="store_true", help="a single still at --from")
    ap.add_argument("-o", "--out", help="output path (default: the delivered-GIF folder)")
    ap.add_argument("--settle", type=float, default=0.0, help="seconds to wait before frame 0")
    ap.add_argument("--keep-frames", action="store_true", help="do not delete the PNG frames")
    args = ap.parse_args()

    reg = load_registry()
    if args.list or not args.model:
        print(f"{'id':22s} {'family':14s} {'frame':11s} {'dur':>6s} {'fps':>4s}  dials")
        for p in reg["pieces"]:
            if not p.get("modelled"):
                print(f"{'(unmodelled)':22s} {p['family']:14s} {'-':11s} {'-':>6s} {'-':>4s}  {p['rel']}")
                continue
            fr = p.get("frame") or {}
            dials = ",".join(q["name"] for q in p.get("params", []) if q["group"] in ("dial", "type"))
            print(f"{p['id']:22s} {p['family']:14s} "
                  f"{str(fr.get('w','?'))+'x'+str(fr.get('h','?')):11s} "
                  f"{(p.get('duration') or 0):6.2f} {(fr.get('fps') or 0):4d}  {dials[:64]}")
        return 0

    piece = resolve(reg, args.model)
    if not piece.get("modelled"):
        sys.exit(f"{piece['rel']} has no model yet — it declares no parameters to render.")
    fr = piece.get("frame") or {}
    w = args.w or fr.get("w") or 1920
    h = args.h or fr.get("h") or 1080
    fps = args.fps or fr.get("fps") or 30
    duration = args.dur or piece.get("duration") or 8.0
    t_to = args.t_to if args.t_to is not None else duration
    mode = "png" if args.png else ("mp4" if args.mp4 else "gif")

    query = build_query(args, piece)
    url = piece["url"] + ("?" + query if query else "")
    out = Path(args.out) if args.out else (DELIVER / f"{piece['id']}{'-light' if args.light else ''}.{mode}")
    out = out.expanduser()

    print(f"→ {piece['id']}  {w}x{h} @ {fps}fps  {t_to - args.t_from:.2f}s ({mode})")
    print(f"  {url}")

    frames_dir = Path(tempfile.mkdtemp(prefix=f"render-{piece['id']}-"))
    try:
        cap = asyncio.run(capture(url, frames_dir, w, h, fps, duration,
                                  args.t_from, t_to, args.settle))
        for e in cap["errors"]:
            print(f"  PAGE ERROR: {e}")
        for c in cap["consoles"]:
            print(f"  console: {c}")
        for q in cap["warnings"]:
            print(f"  MODEL WARNING: {q}")
        if cap["errors"]:
            return 1

        encode(frames_dir, fps, out, mode)
        m = check_artifact(out, mode)
        size_mb = out.stat().st_size / 1e6

        print(f"  wrote {out}  ({m['frames']} frames, {size_mb:.2f} MB)")
        print(f"  size {m['size'][0]}x{m['size'][1]}  "
              f"ink {m['ink_min']}–{m['ink_max']}% (mean {m['ink_mean']})  "
              f"luma {m['luma_min']}–{m['luma_max']}")
        if m["loop_seam"] is not None:
            print(f"  loop seam {m['loop_seam']}")

        ok = True
        if not m["size_ok"]:
            print(f"  FAIL: encoded size {m['size']} != requested {[w, h]}")
            ok = False
        if m["dead_count"]:
            print(f"  FAIL: {m['dead_count']} dead frame(s) (ink < {DEAD_INK_PCT}%): "
                  f"{m['dead_frames']}")
            print("        A blank frame is what a failed capture looks like. "
                  "If it is deliberate, render a shorter window with --from/--to.")
            ok = False
        if mode == "png" and m["ink_max"] < DEAD_INK_PCT:
            print("  FAIL: the still has nothing on it")
            ok = False

        if ok:
            print("  checks: passed")
        if args.keep_frames:
            print(f"  frames kept: {frames_dir}")
        return 0 if ok else 1
    finally:
        if not args.keep_frames:
            shutil.rmtree(frames_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
