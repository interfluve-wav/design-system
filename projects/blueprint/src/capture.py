#!/usr/bin/env python3
"""
Capture blueprint scenes to MP4 + GIF, and assert they actually rendered.

House pipeline (see Bonk motion KB): headless Chromium at 1920x1080 DPR 2,
deterministic frame stepping via window.__seek(t), PNG sequence -> ffmpeg
palettegen/paletteuse.

Two things this script insists on that a plain screenshot loop does not:
  1. frame-identical output — each frame is rendered by seeking to an exact
     timestamp, not by hoping rAF keeps up;
  2. real assertions — frames are checked for ink (the asset is mostly black,
     so a silently blank render is the likely failure mode) and key frames are
     checked for the accent colour where the mark is expected to be filled.

Usage: capture.py [--scene bonk-blueprint] [--fps 30] [--width 1920] [--height 1080]
"""

import argparse
import http.server
import json
import shutil
import socketserver
import subprocess
import threading
from functools import partial
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path("/Users/suhaas/Pictures/motion - design - assets")
DELIVER = Path("/Users/suhaas/Pictures/design - tiles")
SCRATCH = Path("/Users/suhaas/.hermes/cache/scratch")
PORT = 8791


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep the capture log readable
        pass


def serve(directory: Path):
    handler = partial(QuietHandler, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="bonk-blueprint")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--gif-width", type=int, default=1280)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    frames_dir = SCRATCH / f"frames-{args.scene}"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    httpd = serve(ROOT)
    url = f"http://127.0.0.1:{PORT}/projects/blueprint/public/{args.scene}.html"
    print(f"scene : {url}")

    captured = 0
    stats = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=2,
        )
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)

        page.goto(url, wait_until="load")
        page.wait_for_function("window.__ready !== undefined")
        page.evaluate("window.__ready")
        duration = float(page.evaluate("window.__duration"))
        total = int(round(duration * args.fps))
        print(f"duration: {duration}s  frames: {total} @ {args.fps}fps")

        probe = page.evaluate("""() => {
          const c = document.querySelector('canvas');
          return { dpr: window.devicePixelRatio, w: c.width, h: c.height };
        }""")
        print(f"canvas : {probe['w']}x{probe['h']} (dpr {probe['dpr']})")

        for i in range(total):
            t = i / args.fps
            page.evaluate("(t) => window.__seek(t)", t)
            page.screenshot(path=str(frames_dir / f"f{i:04d}.png"))
            captured += 1

        # sanity frames for pixel assertions, rendered through the same path
        for t in (0.6, 2.2, 3.6, 5.4, 7.0):
            page.evaluate("(t) => window.__seek(t)", t)
            page.screenshot(path=str(SCRATCH / f"check-{args.scene}-t{t}.png"))
            stats[str(t)] = str(SCRATCH / f"check-{args.scene}-t{t}.png")

        browser.close()
        if errors:
            print("PAGE ERRORS:")
            for e in errors[:10]:
                print("  ", e[:300])

    httpd.shutdown()
    print(f"captured {captured} frames -> {frames_dir}")
    if captured != total:
        print("FAIL: frame count mismatch")

    ok = assert_frames(frames_dir, total, args.fps)

    tag = args.tag or args.scene
    if ok:
        export(frames_dir, args.fps, args.width, args.height, args.gif_width, tag)
    else:
        print("skipping export — frames failed verification")
    return 0 if ok else 1


def ink_stats(img: Image.Image) -> dict:
    a = np.asarray(img.convert("RGB"), dtype=np.int16)
    lum = a.sum(axis=2)
    nonblack = lum > 36                       # anything meaningfully above black
    # Accent mask by SATURATION, not by hue. The previous test
    # (r > 90 & r > g*1.35 & g > b) was an ORANGE detector: it returns False for
    # pastel yellow (#f5e663), teal (#8fb3a9) and purple (#b0a0d0), so every
    # non-orange variant scored 0 accent pixels and was failed as "NO FILLED
    # MARK". Saturation catches all four and still rejects the mono hairlines,
    # which are grey (max-min ~ 0) whatever their brightness.
    spread = a.max(axis=2) - a.min(axis=2)
    accent = (spread > 25) & (a.max(axis=2) > 60)
    return {
        "nonblack_pct": float(nonblack.mean()) * 100,
        "accent_px": int(accent.sum()),
        "max": int(a.max()),
    }


def assert_frames(frames_dir: Path, total: int, fps: int) -> bool:
    """
    Real checks on real frames. The likeliest silent failure is a blank render
    (mostly-black asset, one wrong alpha, nothing to notice), so: every sampled
    frame must carry ink, and the resolved-mark frames must carry accent pixels.
    """
    samples = sorted(frames_dir.glob("f*.png"))
    sample_idx = [0, int(1.6 * fps), int(2.6 * fps), int(3.9 * fps), int(5.5 * fps), int(7.1 * fps)]
    print("\nframe verification:")
    ok = True
    results = {}
    for idx in sample_idx:
        if idx >= len(samples):
            continue
        img = Image.open(samples[idx])
        st = ink_stats(img)
        t = idx / fps
        results[t] = st
        flag = ""
        if t < 1.0:
            # the opening beat is one dot — near-empty by design, so the
            # meaningful check is that the dot is actually there
            if st["accent_px"] < 150:
                flag = "  <- SEED DOT MISSING"
                ok = False
        elif st["nonblack_pct"] < 0.05:
            flag = "  <- BLANK"
            ok = False
        if 3.8 <= t <= 7.2 and st["accent_px"] < 2000:
            flag = "  <- NO FILLED MARK"
            ok = False
        print(f"  t={t:5.2f}s  ink {st['nonblack_pct']:5.2f}%   accent {st['accent_px']:>7} px   max {st['max']:>3}{flag}")

    # Motion check. A frozen render diffs to exactly zero, so the meaningful
    # assertion is: every pair outside a deliberately static beat must move at
    # all, and the piece as a whole must contain real motion. Requiring large
    # per-frame deltas would fail this piece by design — restrained drifts and
    # held beats are the point of the reference grammar.
    STEP = 3
    holds = [(4.35, 4.75)]           # declared static beat (T.beat window)
    def in_hold(t0, t1):
        return any(a - 0.2 <= t0 and t1 <= b + 0.2 for a, b in holds)

    diffs, frozen = [], []
    for idx in range(int(1.0 * fps), int(6.0 * fps)):
        if idx + STEP >= len(samples):
            break
        t0, t1 = idx / fps, (idx + STEP) / fps
        a = np.asarray(Image.open(samples[idx]).convert("L"), dtype=np.int16)
        b = np.asarray(Image.open(samples[idx + STEP]).convert("L"), dtype=np.int16)
        d = float(np.abs(a - b).mean())
        diffs.append(d)
        if d < 0.0005 and not in_hold(t0, t1):
            frozen.append(round(t0, 2))

    peak = max(diffs) if diffs else 0.0
    alive = sum(1 for d in diffs if d > 0.0005)
    print(f"  motion: peak frame delta {peak:.3f} (need >0.5)")
    print(f"  motion: {alive}/{len(diffs)} pairs changed, {len(frozen)} static outside declared holds")
    if frozen:
        print(f"    static unexpectedly at t = {frozen[:8]}{' ...' if len(frozen) > 8 else ''}")
    if peak <= 0.5 or frozen:
        ok = False

    print("verification:", "PASS" if ok else "FAIL")
    return ok


def export(frames_dir: Path, fps: int, w: int, h: int, gif_w: int, tag: str) -> None:
    DELIVER.mkdir(parents=True, exist_ok=True)
    mp4 = DELIVER / f"{tag}.mp4"
    gif = DELIVER / f"{tag}.gif"
    pal = SCRATCH / f"{tag}-palette.png"

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
        "-i", str(frames_dir / "f%04d.png"),
        "-vf", f"scale={w}:{h}:flags=lanczos", "-c:v", "libx264", "-preset", "slow",
        "-crf", "17", "-pix_fmt", "yuv420p", str(mp4),
    ], check=True)

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
        "-i", str(frames_dir / "f%04d.png"),
        "-vf", f"scale={gif_w}:-1:flags=lanczos,fps={fps},palettegen=stats_mode=diff",
        str(pal),
    ], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
        "-i", str(frames_dir / "f%04d.png"), "-i", str(pal),
        "-lavfi", f"scale={gif_w}:-1:flags=lanczos,fps={fps},paletteuse=dither=bayer:bayer_scale=5",
        "-loop", "0", str(gif),
    ], check=True)

    for p in (mp4, gif):
        print(f"export: {p}  ({p.stat().st_size / 1e6:.1f} MB)")
    print(json.dumps({"mp4": str(mp4), "gif": str(gif)}))


if __name__ == "__main__":
    raise SystemExit(main())
