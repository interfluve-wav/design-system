#!/usr/bin/env python3
"""
Trace the real Bonk wordmark raster into vector contours.

Why: the blueprint-reveal motion study needs the *actual* brand geometry to
stroke, measure and resolve. Bungee Inline (the documented wordmark stand-in)
is not installed, and it isn't condensed like the real mark — so we derive
contours from the shipped raster instead of substituting a face.

Pipeline: raster -> luminance threshold -> hand-written P4 PBM -> potrace
(bezier fitting) -> bake potrace's affine + resolve relative commands ->
normalize to origin -> blueprint/public/wordmark-paths.js (window.BONK_MARK).

Also emits real measurements of the mark (cap height, stem width, per-letter
splits) which the scene uses for its construction lines and annotations.
"""

import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path("/Users/suhaas/Documents/GitHub/bonk-beta/src/assets/auth/bonk-wordmark.png")
OUT_DIR = Path("/Users/suhaas/Pictures/motion - design - assets/blueprint/public")
TMP = Path("/Users/suhaas/.hermes/cache/scratch")
INK_THRESHOLD = 110

NUM = r"-?\d*\.?\d+(?:[eE][-+]?\d+)?"


def shell(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"FAILED {' '.join(cmd)}\n{proc.stderr[:800]}")


def write_pbm(mask: np.ndarray, dest: Path) -> None:
    """P4 PBM: bit 1 = black = foreground. potrace traces the 1s."""
    h, w = mask.shape
    packed = np.packbits(mask.astype(np.uint8), axis=1)  # pads each row to a byte
    with open(dest, "wb") as fh:
        fh.write(f"P4\n{w} {h}\n".encode())
        fh.write(packed.tobytes())


def bake_path(d: str, tx: float, ty: float, sx: float, sy: float) -> str:
    """
    Resolve potrace's mixed absolute/relative path data into all-absolute
    commands with the potrace affine baked in.

    potrace emits M/m, L/l, C/c and Z, often with several coordinate pairs per
    command. In SVG a relative command's later pairs are relative to the point
    produced by the *previous* pair — not to the command's starting point — so
    the running point has to advance pair by pair. Getting this wrong silently
    tears the letterforms apart instead of throwing.
    """
    out: list[str] = []
    cur = (0.0, 0.0)
    sub = (0.0, 0.0)

    def emit(cmd: str, p: tuple[float, float]) -> None:
        out.append(f"{cmd} {tx + sx * p[0]:.3f} {ty + sy * p[1]:.3f}")

    for part in re.findall(r"[A-Za-z][^A-Za-z]*", d):
        cmd = part[0]
        nums = [float(n) for n in re.findall(NUM, part[1:])]

        if cmd in "Zz":
            out.append("Z")
            cur = sub
            continue

        if cmd in "Mm":
            pts = list(zip(nums[0::2], nums[1::2]))
            if cmd == "m":
                cur = (cur[0] + pts[0][0], cur[1] + pts[0][1])
            else:
                cur = pts[0]
            sub = cur
            emit("M", cur)
            # extra pairs after a moveto are implicit linetos
            for x, y in pts[1:]:
                cur = (cur[0] + x, cur[1] + y) if cmd == "m" else (x, y)
                emit("L", cur)
            continue

        if cmd in "Ll":
            for x, y in zip(nums[0::2], nums[1::2]):
                cur = (cur[0] + x, cur[1] + y) if cmd == "l" else (x, y)
                emit("L", cur)
            continue

        if cmd in "Cc":
            coords = nums
            for i in range(0, len(coords), 6):
                trio = coords[i:i + 6]
                if len(trio) < 6:
                    raise SystemExit("truncated cubic in potrace output")
                pts = [(trio[j], trio[j + 1]) for j in range(0, 6, 2)]
                if cmd == "c":
                    # each control point and the endpoint are relative to the
                    # running point, which advances only at the endpoint
                    abs_pts = [
                        (cur[0] + pts[0][0], cur[1] + pts[0][1]),
                        (cur[0] + pts[1][0], cur[1] + pts[1][1]),
                        (cur[0] + pts[2][0], cur[1] + pts[2][1]),
                    ]
                else:
                    abs_pts = pts
                cur = abs_pts[-1]
                out.append(
                    "C " + " ".join(
                        f"{tx + sx * x:.3f} {ty + sy * y:.3f}" for x, y in abs_pts
                    )
                )
            continue

        raise SystemExit(f"unhandled path command '{cmd}'")

    return " ".join(out)


def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not SRC.exists():
        raise SystemExit(f"missing source raster: {SRC}")

    pbm = TMP / "mark.pbm"
    svg = TMP / "mark.svg"

    # The shipped wordmark is opaque white-on-black (no alpha to lean on), so
    # threshold luminance directly and write the bitmap ourselves — magick's
    # PBM polarity bit us once, and potrace traces whatever the 1s are.
    img = Image.open(SRC)
    mask = np.array(img.convert("L")) > 110
    ink = float(mask.mean()) * 100
    if not 5.0 < ink < 60.0:
        raise SystemExit(f"implausible ink coverage {ink:.1f}% — check threshold/polarity")

    write_pbm(mask, pbm)
    shell([
        "potrace", str(pbm),
        "-s", "-o", str(svg),
        "--turdsize", "12",
        "--alphamax", "1.0",
        "--opttolerance", "0.3",
    ])

    raw = svg.read_text()

    # potrace wraps everything in one <g transform="translate(tx,ty) scale(sx,sy)">
    g = re.search(
        r'<g transform="translate\((' + NUM + r'),(' + NUM + r')\)\s*'
        r'scale\((' + NUM + r'),(' + NUM + r')\)"',
        raw,
    )
    if not g:
        raise SystemExit("could not find potrace transform block")
    tx, ty, sx, sy = (float(v) for v in g.groups())

    ds = re.findall(r'<path d="([^"]+)"', raw)
    if not ds:
        raise SystemExit("potrace produced no path data")
    # potrace emits one compound path: outer contours + the inline channel holes
    d_baked = re.sub(r"\s+", " ", bake_path(" ".join(ds), tx, ty, sx, sy)).strip()

    # ── bbox + normalize to origin ────────────────────────────────────────
    pts = [(float(a), float(b)) for a, b in re.findall(rf"({NUM}) ({NUM})", d_baked)]
    if not pts:
        raise SystemExit("no coordinates after baking")
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    minx, miny, maxx, maxy = xs.min(), ys.min(), xs.max(), ys.max()

    def shift(match: re.Match) -> str:
        cmd = match.group(1)
        nums = [float(n) for n in re.findall(NUM, match.group(2))]
        pairs = [f"{nums[i] - minx:.3f} {nums[i + 1] - miny:.3f}" for i in range(0, len(nums), 2)]
        return f"{cmd} " + " ".join(pairs)

    d_norm = re.sub(r"\s+", " ", re.sub(r"([MLC])([^MLCZ]+)", shift, d_baked)).strip()

    W = maxx - minx
    H = maxy - miny

    # ── real measurements from the mask: letter splits + stroke widths ────
    col = mask.sum(axis=0)
    row = mask.sum(axis=1)

    letters: list[dict] = []
    in_letter = False
    start = 0
    for x in range(len(col)):
        filled = col[x] > 0
        if filled and not in_letter:
            in_letter, start = True, x
        elif not filled and in_letter:
            in_letter = False
            letters.append({"x0": start, "x1": x, "w": x - start})
    if in_letter:
        letters.append({"x0": start, "x1": len(col), "w": len(col) - start})

    # drop specks; keep anything plausibly a letter stem
    widest = max((l["w"] for l in letters), default=0)
    letters = [l for l in letters if l["w"] >= widest * 0.03]

    # stem width: median horizontal run of ink through the x-height band
    band = mask[int(mask.shape[0] * 0.35): int(mask.shape[0] * 0.65), :]
    runs: list[int] = []
    for r in band:
        run = 0
        for v in r:
            if v:
                run += 1
            elif run:
                runs.append(run)
                run = 0
        if run:
            runs.append(run)
    stem = float(np.median(runs)) if runs else 0.0

    ink_rows = np.nonzero(row)[0]
    ink_cols = np.nonzero(col)[0]
    # The baked path is in raster pixels with the ink origin subtracted, so
    # every metric must live in that same space (no extra scaling — mixing a
    # scaled letters list with an unscaled path silently misaligns them).
    ink_x0 = float(ink_cols[0])
    metrics = {
        "capHeight": round(float(ink_rows[-1] - ink_rows[0] + 1), 2),
        "stemWidth": round(stem, 2),
        "inkCoveragePct": round(ink, 2),
        "letterCount": len(letters),
    }

    letters_norm = [
        {"x0": round(l["x0"] - ink_x0, 2), "x1": round(l["x1"] - ink_x0, 2), "w": round(l["w"], 2)}
        for l in letters
    ]

    # Column-wise ink density, downsampled to a fixed bucket count. The scene
    # morphs its ruler ticks into this profile — a waveform of the mark's own
    # ink rather than a decorative squiggle.
    buckets = 96
    edges = np.linspace(0, len(col), buckets + 1).astype(int)
    density = np.array([col[edges[i]:edges[i + 1]].mean() for i in range(buckets)])
    peak = density.max() or 1.0
    profile = [round(float(d / peak), 3) for d in density]

    payload = (
        "// generated by blueprint/src/trace.py — do not hand-edit\n"
        "// geometry traced from bonk-beta/src/assets/auth/bonk-wordmark.png\n"
        "window.BONK_MARK = "
        + json.dumps({
            "d": d_norm,
            "width": round(W, 3),
            "height": round(H, 3),
            "letters": letters_norm,
            "metrics": metrics,
            "profile": profile,
        }, separators=(",", ":"))
        + ";\n"
    )
    dest = OUT_DIR / "wordmark-paths.js"
    dest.write_text(payload)

    print(f"source    : {SRC.name} ({mask.shape[1]}x{mask.shape[0]}), ink {ink:.1f}%")
    print(f"mark size : {W:.1f} x {H:.1f} units")
    print(f"path      : {d_norm.count('M')} subpaths, {len(d_norm)} chars")
    print(f"letters   : {[(l['x0'], l['x1']) for l in letters_norm]}")
    print(f"metrics   : {metrics}")
    print(f"written   : {dest}")


if __name__ == "__main__":
    main()
