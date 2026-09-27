"""Render the @bonk.dj reel to MP4 + GIF, and verify the artifact.

Vertical 1080x1920 -- Instagram's format, not the 1920x1080 the earlier motion
assets used. 30 s at 25 fps = 750 frames, driven by window.__seek so every frame
is a distinct timestamp rather than a slice of real time.

PNG frames, not JPEG: this is a black-ground text piece and JPEG ringing shows up
around glyph edges. Mostly-black PNGs compress well (~100 KB each at this size).

Verifies the delivered file, not the intent: frame count, fps, dimensions, dead
frames, and that the ink actually varies across the piece.
"""
import io
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path("/Users/suhaas/Pictures/motion - design - assets")
FRAMES = Path("/Users/suhaas/.hermes/cache/scratch/reel-frames")
OUT = Path("/Users/suhaas/Pictures/design - tiles - motion")
URL = "http://127.0.0.1:8765/projects/instagram/reel.html"
FPS = 25
W, H = 1080, 1920


VER = sys.argv[1] if len(sys.argv) > 1 else "v2"   # module-level: verify() reads it too


def dump():
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL, wait_until="load")
        # __ready is a Promise (the page waits for the font before resolving it).
        # evaluate() awaits promises, so do NOT test `=== true` here -- that would
        # never become true and the render would race an unloaded font.
        pg.evaluate("() => window.__ready")
        dur = pg.evaluate("() => window.__duration")
        n = int(dur * FPS)
        for i in range(n):
            pg.evaluate(f"() => window.__seek({i / FPS})")
            pg.screenshot(path=str(FRAMES / f"{i:04d}.png"))
        br.close()
    return n, dur, errs


def encode(n):
    mp4 = OUT / f"bonk-reel-30s-{VER}.mp4"
    gif = OUT / f"bonk-reel-30s-{VER}.gif"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
         "-i", str(FRAMES / "%04d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
         "-preset", "slow", "-movflags", "+faststart", str(mp4)], check=True)
    # GIF for in-chat review: half rate and 60% scale keeps 30 s under control
    gif_fps = 12.5
    pal = FRAMES.parent / "reel-pal.png"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
         "-i", str(FRAMES / "%04d.png"), "-vf",
         f"fps={gif_fps},scale=648:1152:flags=lanczos,palettegen=max_colors=64",
         str(pal)], check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
         "-i", str(FRAMES / "%04d.png"), "-i", str(pal), "-lavfi",
         f"fps={gif_fps},scale=648:1152:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4",
         "-loop", "0", str(gif)], check=True)
    return mp4, gif


def verify(mp4, gif):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=nb_frames,r_frame_rate,width,height,codec_name", "-of",
         "default=nw=1", str(mp4)], capture_output=True, text=True).stdout.strip()
    print("  MP4:")
    for line in probe.splitlines():
        print(f"    {line}")

    files = sorted(FRAMES.glob("*.png"))
    prev, dead = None, 0
    inks = []
    for f in files[::5]:
        a = np.asarray(Image.open(f).convert("L"), dtype=float)
        inks.append(100 * (a > 40).mean())
        if prev is not None and np.abs(a - prev).mean() < 0.0008:
            dead += 1
        prev = a
    print(f"  ink over {len(files)} frames: min {min(inks):.3f}%  max {max(inks):.3f}%")
    print(f"  near-identical consecutive pairs (sampled): {dead}")
    print(f"  MP4 {mp4.stat().st_size/1e6:.2f} MB   GIF {gif.stat().st_size/1e6:.2f} MB")
    # contact sheet so the arc is reviewable at a glance
    picks = [0, 2, 4, 6, 8, 11, 13, 15, 17, 20, 23, 26, 28, 29.6]
    cols, rows, tw = 5, 3, 216
    th = round(tw * H / W)
    sheet = Image.new("RGB", (tw * cols, th * rows), (20, 20, 20))
    for i, t in enumerate(picks):
        idx = min(int(t * FPS), len(files) - 1)
        im = Image.open(files[idx]).convert("RGB").resize((tw, th), Image.LANCZOS)
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    p = OUT / f"bonk-reel-30s-{VER}-contact-sheet.png"
    sheet.save(p, optimize=True)
    print(f"  contact sheet: {p.name}")


if __name__ == "__main__":
    n, dur, errs = dump()
    print(f"═══ dumped {n} frames over {dur}s at {FPS}fps, {W}x{H}")
    if errs:
        print(f"  PAGE ERRORS: {errs[:3]}")
    else:
        print("  no pageerror")
    mp4, gif = encode(n)
    verify(mp4, gif)
