#!/usr/bin/env python3
"""The registration ghost must use the register-aware floor, not a literal 0.09.

Last light-register failure, and it is not an alpha problem: at ph=0 P12's bands are
translated out of their OWN clips, so they paint nothing whatever their opacity. The
element whose stated job is to guarantee a panel is never empty is the registration
ghost -- so the ghost is what has to carry the floor.

Measured on cream (#f5f9e9) with INK #36453b:
  a=0.09 -> g 223   above the 180 ink threshold, i.e. invisible to any check
  a=0.44 -> g 167   registers, but a heavy outline on a light ground
  a=0.38 -> g 175   registers, and reads as a light-mid outline
So the light floor drops to 0.38. On the dark register this same change lifts the
ghost from 0.09 (g 23) to 0.12 (g 31), which is the point: it now clears the ink
threshold there too, instead of sitting one level below it.
"""
import sys
from pathlib import Path

P = Path("/Users/suhaas/Pictures/motion - design - assets/projects/motion-system/"
         "bonk-motion-system-v3.html")

EDITS = [
    ("    --floor:0.44;\n  }", "    --floor:0.38;\n  }"),
    (
        "    ctx.globalAlpha = 0.09;\n    ctx.strokeStyle = INK;",
        "    /* FLOOR, not a literal. At 0.09 this ghost cleared neither register's ink\n"
        "       threshold, yet it is precisely the element that guarantees no panel is\n"
        "       ever empty -- P12's bands translate out of their own clips at ph=0, so\n"
        "       nothing else is on screen. Register-aware or it does not do its job. */\n"
        "    ctx.globalAlpha = FLOOR;\n    ctx.strokeStyle = INK;",
    ),
]

src = P.read_text()
for old, new in EDITS:
    n = src.count(old)
    if n != 1:
        print(f"ABORT — anchor found {n}x (need exactly 1), file untouched:\n  {old[:80]}...")
        sys.exit(1)
    src = src.replace(old, new)
P.write_text(src)
print(f"  {len(EDITS)} edits applied -> {P.name}  ({len(src):,} bytes)")
