#!/usr/bin/env python3
"""Set Bonk as the text face in the motion system, replacing IBM Plex Mono.

The brand's own type, not a borrowed mono. Bonk Variable carries wght 300-700 and
slnt -10-0, and its cmap covers every character the labels use (measured: 665
glyphs, 0 missing from the 75-char label charset), so no fallback is ever reached.

Served as woff2 (133 KB) with the ttf (474 KB) behind it as a fallback. The family
was copied into the project's served font dir first -- a page cannot @font-face a
file from outside its own document root.
"""
import sys
from pathlib import Path

P = Path("/Users/suhaas/Pictures/motion - design - assets/projects/motion-system/"
         "bonk-motion-system-v3.html")

EDITS = [
    (
        "  @font-face {\n"
        "    font-family: 'PlexMono Bonk';\n"
        "    src: url('../blueprint/public/fonts/IBMPlexMono-Regular.ttf') format('truetype');\n"
        "    font-weight: 400; font-display: block;\n"
        "  }\n"
        "  @font-face {\n"
        "    font-family: 'PlexMono Bonk';\n"
        "    src: url('../blueprint/public/fonts/IBMPlexMono-SemiBold.ttf') format('truetype');\n"
        "    font-weight: 600; font-display: block;\n"
        "  }",
        "  /* Bonk's own type, not a borrowed mono. Variable: wght 300-700 and slnt -10-0,\n"
        "     declared as a weight RANGE so canvas ctx.font can pick 400 or 600 off the\n"
        "     same file. woff2 first (133 KB), ttf behind it (474 KB). */\n"
        "  @font-face {\n"
        "    font-family: 'Bonk';\n"
        "    src: url('../blueprint/public/fonts/Bonk-VF.woff2') format('woff2'),\n"
        "         url('../blueprint/public/fonts/Bonk-VF.ttf') format('truetype');\n"
        "    font-weight: 300 700;\n"
        "    font-style: normal;\n"
        "    font-display: block;\n"
        "  }",
    ),
    (
        "function mono(size, weight) {\n"
        "  ctx.font = `${weight || 400} ${size}px 'PlexMono Bonk', ui-monospace, monospace`;\n"
        "}",
        "/** Bonk, the brand's own typeface. Renamed from mono() -- it is no longer one. */\n"
        "function typeface(size, weight) {\n"
        "  ctx.font = `${weight || 400} ${size}px 'Bonk', ui-sans-serif, sans-serif`;\n"
        "}",
    ),
    ("  mono(size || 12, weight);", "  typeface(size || 12, weight);"),
    (
        "  try { await document.fonts.load(\"400 12px 'PlexMono Bonk'\"); } catch (e) {}\n"
        "  try { await document.fonts.load(\"600 12px 'PlexMono Bonk'\"); } catch (e) {}",
        "  try { await document.fonts.load(\"400 12px 'Bonk'\"); } catch (e) {}\n"
        "  try { await document.fonts.load(\"600 12px 'Bonk'\"); } catch (e) {}",
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
leftover = src.count("PlexMono")
print(f"  {len(EDITS)} edits applied -> {P.name}  ({len(src):,} bytes)"
      f"   PlexMono refs remaining: {leftover}")
