"""Re-capture glow / typeon / ripple after the explicit font load was added.

Each page is driven frame-by-frame through window.__seek, so every frame is a
distinct timestamp rather than a slice of real time. Encodes an MP4 (the usable
asset) and a small GIF (for review) per piece.

Reports the loop seam for each -- the last frame versus the first. glow was
re-captured specifically to close that seam, so the number is the point of this
run, not decoration.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path("/Users/suhaas/Pictures/motion - design - assets")
OUT = Path("/Users/suhaas/Pictures/design - tiles - motion")
FRAMES = Path("/Users/suhaas/.hermes/cache/scratch/recap-frames")
FPS = 25
W, H = 1920, 1080

ASSETS = [
    ("glow", "projects/motion-assets/glow.html"),
    ("typeon", "projects/motion-assets/typeon.html"),
    ("ripple", "projects/motion-assets/ripple.html"),
]

VER = sys.argv[1] if len(sys.argv) > 1 else "v2"
ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None   # e.g. "typeon"


def run(name, rel):
    print(f"\n═══ {name} ═══")
    url = f"http://127.0.0.1:8765/{rel}"
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)

    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url, wait_until="load")
        pg.evaluate("() => window.__ready")      # awaits the font promise
        dur = pg.evaluate("() => window.__duration")
        # fonts.check is not proof, but zero delta against a fallback is disproof
        font_ok = pg.evaluate("() => document.fonts.check(\"700 16px 'Bonk'\")")
        n = int(dur * FPS)
        for i in range(n):
            pg.evaluate(f"() => window.__seek({i / FPS})")
            pg.screenshot(path=str(FRAMES / f"{i:04d}.png"))
        br.close()

    print(f"  {n} frames over {dur}s at {FPS}fps  {W}x{H}   Bonk loaded: {font_ok}")
    if errs:
        print(f"  PAGE ERRORS: {errs[:2]}")

    mp4 = OUT / f"bonk-{name}-{VER}.mp4"
    gif = OUT / f"bonk-{name}-{VER}.gif"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", str(FRAMES / "%04d.png"), "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "slow",
                    "-movflags", "+faststart", str(mp4)], check=True)
    pal = FRAMES.parent / "recap-pal.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", str(FRAMES / "%04d.png"), "-vf",
                    f"fps=12.5,scale=960:540:flags=lanczos,palettegen=max_colors=96",
                    str(pal)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", str(FRAMES / "%04d.png"), "-i", str(pal), "-lavfi",
                    f"fps=12.5,scale=960:540:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
                    "-loop", "0", str(gif)], check=True)

    files = sorted(FRAMES.glob("*.png"))
    first = np.asarray(Image.open(files[0]).convert("L"), dtype=float)
    last = np.asarray(Image.open(files[-1]).convert("L"), dtype=float)
    mid = np.asarray(Image.open(files[len(files) // 2]).convert("L"), dtype=float)
    mid2 = np.asarray(Image.open(files[len(files) // 2 + 1]).convert("L"), dtype=float)
    inks = []
    dead = 0
    prev = None
    for f in files:
        a = np.asarray(Image.open(f).convert("L"), dtype=float)
        inks.append(100 * (a > 40).mean())
        if prev is not None and np.abs(a - prev).mean() < 0.001:
            dead += 1
        prev = a
    seam = np.abs(last - first).mean()
    delta = np.abs(mid2 - mid).mean()
    print(f"  ink {min(inks):.3f}% .. {max(inks):.3f}%   dead frames {dead}")
    print(f"  per-frame delta {delta:.4f}")
    print(f"  loop seam {seam:.4f}  ({'CLOSED' if seam <= max(delta * 3, 0.05) else 'STILL POPS'} "
          f"— {seam / delta if delta else float('inf'):.1f}x the frame delta)")
    print(f"  MP4 {mp4.stat().st_size/1e6:.2f} MB   GIF {gif.stat().st_size/1e6:.2f} MB")


for name, rel in ASSETS:
    if ONLY and name not in ONLY:
        continue
    run(name, rel)
