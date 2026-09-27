#!/usr/bin/env python3
"""Retract the blueprint's construction furniture when the mark lands, in every render.

The bug, in all three files: the letter COLUMN rules got a dedicated retraction
(`rulesOut`, added after they were measured putting ~12k px of grey inside the finished
mark's box) but the SEEDED geometry -- the expanding ring, the centre cross, and the
centre circle -- was left on `guideAlpha` alone, so it stayed at half strength over the
resolved artwork until `dimsAway`, ~2s later. Seeded geometry that never leaves.

The seeded circle at the mark's centre is the "spiral" that comes in during the first
frames and never fades: radius u(44) at 0.5 alpha, sitting in the negative space between
glyphs, so it reads as a circle drawn on the finished mark.

v3 additionally has the superscript brackets I added; its overlap bracket sits under the
letter k and had the same problem.

Only the LABELLED dimensions (top width, left height, x-height, stroke) wait for
dimsAway. Those are the blueprint's content. Everything here is scaffolding.

Every edit is an asserted transformation: if an anchor does not appear exactly once, the
file is left untouched and the run reports it. Run this twice and it will refuse on the
second pass, which is the intended tripwire -- it is not idempotent by design.
"""

import sys
from pathlib import Path

PUB = Path("/Users/suhaas/Pictures/motion - design - assets/projects/blueprint/public")

V12_FURN = "furnitureOut: [3.10, 3.85],"
V3_FURN = "furnitureOut: [3.25, 4.00],"

FURN_COMMENT = """
  /* Construction furniture that reads as lines OVER the finished artwork retracts as
     the mark lands. The seeded ring, the centre cross and the centre circle used to sit
     at partial alpha on top of the resolved mark for another ~2s (they carried only
     guideAlpha, which is tied to dimsAway) -- seeded geometry that never leaves. Only
     the LABELLED dimensions wait for dimsAway. */"""

FURN_CALC = """
  /* furniture retracts on the mark's landing, independently of the labelled dimensions */
  const furnAlpha = 1 - win(t, T.furnitureOut[0], T.furnitureOut[1]);"""

# ── edits applied to all three ───────────────────────────────────────────────
COMMON = [
    # 1. the timeline entry
    ("  rulesOut: [%s],",
     "  rulesOut: [%s],\n" + FURN_COMMENT + "\n  %s",
     None),                                              # special-cased per file

    # 2. the factor itself
    ("const guideAlpha = 1 - guidesOut;",
     "const guideAlpha = 1 - guidesOut;" + FURN_CALC,
     None),

    # 3. the cap / base rules
    ("""    ctx.globalAlpha = guideAlpha;
    hairCentre(top, left - u(42), right + u(42)""",
     """    ctx.globalAlpha = guideAlpha * furnAlpha;
    hairCentre(top, left - u(42), right + u(42)""",
     None),

    # 4. the centre cross
    ("ctx.globalAlpha = 0.85 * guideAlpha;",
     "ctx.globalAlpha = 0.85 * guideAlpha * furnAlpha;",
     None),

    # 5. the seeded centre circle  <- the "spiral"
    ("ctx.globalAlpha = 0.5 * guideAlpha;",
     "ctx.globalAlpha = 0.5 * guideAlpha * furnAlpha;",
     None),

    # 6. the expanding seed ring: fade it fully out before it stops being drawn, so it
    #    exits at zero alpha instead of popping off at ~0.085
    ("ctx.globalAlpha = 0.32 * (1 - clamp01((t - 0.15) / 0.75));",
     "ctx.globalAlpha = 0.32 * (1 - clamp01((t - 0.15) / 0.55));",
     "optional"),
]

# ── v3-sup only: the superscript furniture (band, alignment bracket, overlap bracket) ──
V3_ONLY = [
    # the overlap bracket -- the line under the k
    ("""    ctx.globalAlpha = guideAlpha;
    [xL, xR].forEach((x) => hair(x + 0.5, yB - u(6), x + 0.5, yB + u(6), ACCENT_2, 1));""",
     """    ctx.globalAlpha = guideAlpha * furnAlpha;
    [xL, xR].forEach((x) => hair(x + 0.5, yB - u(6), x + 0.5, yB + u(6), ACCENT_2, 1));"""),

    # the superscript band dimension
    ("""    ctx.globalAlpha = guideAlpha;
    hair(x + 0.5, cy - h, x + 0.5, cy + h, ACCENT_2, 1);""",
     """    ctx.globalAlpha = guideAlpha * furnAlpha;
    hair(x + 0.5, cy - h, x + 0.5, cy + h, ACCENT_2, 1);"""),

    # the top-alignment bracket
    ("""    ctx.globalAlpha = guideAlpha;
    hair(x0 + 0.5, ySup + 0.5, xSup + 0.5, ySup + 0.5, ACCENT_2, 1.4);""",
     """    ctx.globalAlpha = guideAlpha * furnAlpha;
    hair(x0 + 0.5, ySup + 0.5, xSup + 0.5, ySup + 0.5, ACCENT_2, 1.4);"""),

    # the x-height plane crosses the superscript's descender, so it goes with the
    # furniture too; its DIMENSION stays, and that is the labelled statement
    ("""    ctx.globalAlpha = 0.55 * guideAlpha;
    hairCentre(yx, left - u(30), right + u(30), win(t, T.capLine[0] + 0.1, T.capLine[1] + 0.15), ACCENT, 1);
    ctx.globalAlpha = guideAlpha;
    text('X', left - u(34), yx + u(4), ACCENT_SOFT, u(10), 'right', 600);""",
     """    ctx.globalAlpha = 0.55 * guideAlpha * furnAlpha;
    hairCentre(yx, left - u(30), right + u(30), win(t, T.capLine[0] + 0.1, T.capLine[1] + 0.15), ACCENT, 1);
    ctx.globalAlpha = guideAlpha * furnAlpha;
    text('X', left - u(34), yx + u(4), ACCENT_SOFT, u(10), 'right', 600);"""),

    # column rules follow the furniture out
    ("  rulesOut: [3.95, 4.55],", "  rulesOut: [3.40, 4.10],"),
]


def apply(path: Path, edits, furn: str) -> int:
    src = original = path.read_text()
    misses, applied = [], 0
    for edit in edits:
        old, new = edit[0], edit[1]
        level = edit[2] if len(edit) > 2 else None
        if old.startswith("  rulesOut: [%s],") and level is None:
            # v1/v2 anchor on their own rulesOut line
            pass
        n = src.count(old)
        if n != 1:
            if level == "optional":
                misses.append(f"    (optional) {n}x  {old[:60]!r}")
                continue
            misses.append(f"    !! {n}x  {old[:60]!r}")
            continue
        src = src.replace(old, new)
        applied += 1
    hard = [m for m in misses if m.strip().startswith("!!")]
    if hard:
        print(f"  {path.name}: ABORT — {len(hard)} anchor(s) not unique")
        for m in misses:
            print(m)
        return 0
    path.write_text(src)
    print(f"  {path.name}: {applied} edits applied, {len(src) - len(original):+d} bytes")
    for m in misses:
        print(m)
    return applied


def main() -> int:
    total = 0
    # v1 and v2: same shapes, same rulesOut window
    for name in ("bonk-blueprint.html", "bonk-blueprint-v2.html"):
        p = PUB / name
        edits = list(COMMON)
        edits[0] = ("  rulesOut: [3.05, 3.70],      // construction rules leave once the mark is solid",
                    "  rulesOut: [3.05, 3.70],      // construction rules leave once the mark is solid\n"
                    + FURN_COMMENT + "\n  " + V12_FURN)
        total += apply(p, edits, V12_FURN)

    p = PUB / "bonk-blueprint-v3-sup.html"
    # v3 routes the cap/base rules AND the cross through drawGuides(), so those two
    # inline anchors do not exist; the whole helper is furniture, so retract it at the
    # call site in one edit instead.
    v3_common = [COMMON[0], COMMON[1], COMMON[4], COMMON[5]]
    v3_common[0] = ("  rulesOut: [3.95, 4.55],",
                    "  rulesOut: [3.95, 4.55],\n" + FURN_COMMENT + "\n  " + V3_FURN)
    v3_common.append((
        "drawGuides(guideAlpha, top, bot,",
        "drawGuides(guideAlpha * furnAlpha, top, bot,"))
    edits = v3_common + [(e[0], e[1]) for e in V3_ONLY]
    total += apply(p, edits, V3_FURN)

    print(f"\n{total} edits across 3 blueprint renders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
