#!/usr/bin/env python3
"""Floor v3's four primitives so no panel is ever empty at its own ph=0.

Measured problem: v3's panels are phase-offset (0, .25, .5, .75), so each panel's
empty moment lands at a different t -- but every one of them still HAS one, because
each primitive builds from nothing. The light register exposed it (P10 read 0.000
at t=4.50, P12 read 0.000 at t=1.50); the dark register only passed because the two
failing panels were sampled marginally above a 0.02% threshold.

The floors are not arbitrary. The reference clips are never empty either:
  clip 02 dot-sphere      ink 1.07 -> 2.92 -> 0.16 %   (opens and ends non-zero)
  clip 04 language-specimen  ink 7.59 % at frame ONE    (busy from the first frame)
  clip 01 title-particles  ink 0.19 % at frame one
  clip 03 kinetic-type     ink 0.16 % at frame one
So a persistent minimum is faithful to the reference, not a workaround.

Asserted transformations: every anchor must appear exactly once or the file is
left untouched.
"""
import sys
from pathlib import Path

P = Path("/Users/suhaas/Pictures/motion - design - assets/projects/motion-system/"
         "bonk-motion-system-v3.html")

EDITS = [
    # ── P09 particle field: raise the born floor so the field is present at ph=0 ──
    (
        "    const born = 0.14 + 0.86 * clamp01((burst - hash(i * 5.3 + 2.9) * 0.28) / 0.72);",
        "    const born = 0.32 + 0.68 * clamp01((burst - hash(i * 5.3 + 2.9) * 0.28) / 0.72);\n"
        "    /* raised 0.14 -> 0.32: at 0.14 the field was legible on the black ground but\n"
        "       the light register measured it at 0.005% -- a low-alpha accent over cream\n"
        "       falls outside its own ink threshold. The reference opens at 0.19%. */",
    ),
    # ── P10 dot lattice: separate base radius from modulation, floor both ──
    (
        "      const rr = (u(0.9) + u(3.6) * w) * ignite * (1 - 0.58 * fade);\n"
        "      if (rr < 0.15) continue;\n"
        "      const x = P.px + c * cw, y = P.py + r * ch;\n"
        "      ctx.globalAlpha = (0.28 + 0.72 * w) * (1 - 0.42 * fade);",
        "      /* ignite starts at 0, so at ph=0 every cell had rr=0 and the panel went\n"
        "         blank (measured 0.001% at t=4.50). Base radius and alpha are now floored\n"
        "         independently of the ignition ramp: the field is always present, and the\n"
        "         ramp modulates it rather than creating it. */\n"
        "      const field = 0.42 + 0.58 * ignite;\n"
        "      const rr = (u(1.4) + u(5.2) * w) * field * (1 - 0.45 * fade);\n"
        "      if (rr < 0.1) continue;\n"
        "      const x = P.px + c * cw, y = P.py + r * ch;\n"
        "      ctx.globalAlpha = (0.45 + 0.55 * w) * (1 - 0.30 * fade);",
    ),
    # ── P11 specimen grid: every cell keeps a floor, so the grid is busy at frame one ──
    (
        "      const local = clamp01((reveal - d * 0.42) / 0.58);\n"
        "      const e = cubicOut(local);\n"
        "      if (e <= 0.001) continue;",
        "      const local = clamp01((reveal - d * 0.42) / 0.58);\n"
        "      /* floor of 0.18: clip 04 is BUSY from frame one (ink 7.59% at t=0, peak\n"
        "         at 0.01), so a grid that builds from nothing was unfaithful as well as\n"
        "         empty. The floor fades out with the clear, so the panel still ends light. */\n"
        "      const e = Math.max(cubicOut(local), 0.18 * (1 - clear));\n"
        "      if (e <= 0.001) continue;",
    ),
    # ── P12 kinetic type: bands carry a faint presence before they travel ──
    (
        "    ctx.globalAlpha = (0.35 + 0.65 * e) * (1 - out);",
        "    /* floor of 0.12: the reference opens at 0.16% ink, not zero. Each band is\n"
        "       clipped to its own slice, so a floored band shows its slice faintly rather\n"
        "       than the whole mark ghosting. */\n"
        "    ctx.globalAlpha = (0.12 + 0.88 * e) * (1 - out);",
    ),
]

src = P.read_text()
applied = 0
for old, new in EDITS:
    n = src.count(old)
    if n != 1:
        print(f"ABORT — anchor found {n}x (need exactly 1), file untouched:\n  {old[:90]}...")
        sys.exit(1)
    src = src.replace(old, new)
    applied += 1

P.write_text(src)
print(f"  {applied} floor edits applied -> {P.name}  ({len(src):,} bytes)")
print("  Run twice and it refuses: the anchors are gone after one pass.")
