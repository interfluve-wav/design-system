#!/usr/bin/env python3
"""Make v3's remaining floors ground-aware, because alpha is not register-neutral.

After the first floor pass, the DARK (brand) register measured 0 empty samples in
all four panels. The LIGHT register still had two failures:
  P12 kinetic type  reads exactly 0.000 at its ph=0  (t=1.50, 1.75)
  P11 specimen grid reads 0.017 / 0.019 at its ph=0  (t=3.00, 3.50)
Both are the same physics: 12% orange over black is plainly visible, 12% teal over
cream is not. A fixed alpha floor cannot serve both registers, so the floor becomes
a theme token -- CSS stays the single source of truth for register-dependent values.

P09 and P10 are deliberately NOT touched: their floors (0.32 and 0.42) already
clear BOTH registers, and rewriting passing code is how regressions start.
"""
import sys
from pathlib import Path

P = Path("/Users/suhaas/Pictures/motion - design - assets/projects/motion-system/"
         "bonk-motion-system-v3.html")

EDITS = [
    # theme token: dark register
    (
        "    --label:rgba(255,255,255,0.44);\n  }",
        "    --label:rgba(255,255,255,0.44);\n"
        "    /* Lowest alpha at which a primitive still reads as PRESENT on this\n"
        "       ground. Not a taste value: 0.12 is visible on black and invisible on\n"
        "       cream, so the two registers need different floors for the same\n"
        "       geometry. Measured: 0.12 on the light register left panels at 0.000%. */\n"
        "    --floor:0.12;\n  }",
    ),
    # theme token: light register
    (
        "    --label:rgba(89,104,105,0.92);\n  }",
        "    --label:rgba(89,104,105,0.92);\n    --floor:0.44;\n  }",
    ),
    # mirror it into the JS fallbacks
    (
        "let INK         = '#ffffff';",
        "let INK         = '#ffffff';\nlet FLOOR       = 0.12;      // register-dependent; see :root --floor",
    ),
    (
        "  INK         = g('--ink',         INK);",
        "  INK         = g('--ink',         INK);\n"
        "  FLOOR       = parseFloat(g('--floor', String(FLOOR))) || FLOOR;",
    ),
    # P11: floor comes from the register
    (
        "      const e = Math.max(cubicOut(local), 0.18 * (1 - clear));",
        "      const e = Math.max(cubicOut(local), FLOOR * (1 - clear));",
    ),
    # P12: floor comes from the register
    (
        "    ctx.globalAlpha = (0.12 + 0.88 * e) * (1 - out);",
        "    ctx.globalAlpha = (FLOOR + (1 - FLOOR) * e) * (1 - out);",
    ),
]

src = P.read_text()
for old, new in EDITS:
    n = src.count(old)
    if n != 1:
        print(f"ABORT — anchor found {n}x (need exactly 1), file untouched:\n  {old[:90]}...")
        sys.exit(1)
    src = src.replace(old, new)

P.write_text(src)
print(f"  {len(EDITS)} edits applied -> {P.name}  ({len(src):,} bytes)")
