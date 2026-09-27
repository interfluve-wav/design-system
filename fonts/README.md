# Type library

Two display families, cleaned and verified. Source packs were the telegram-distributed
originals; filenames and name tables carried the distributor's watermark, and two pieces of
binary metadata were wrong. Both are fixed here.

```
fonts/
  base-neue/
    static/        54 roman + 54 oblique statics (TTF, glyf)
    variable/      BaseNeueVar.ttf   — 3 axes, 108 named instances
  nerds-grotesk/
    NerdsGrotesk-Regular.otf         — single weight, CFF/OpenType, 394 glyphs
  specimen.html                     — live specimen (needs a local server, see below)
  specimen.png                      — full-page render
```

## Base Neue

Power Type™ Foundry / Teguh Arief — power-type.com

A proper superfamily: **6 widths × 9 weights × 2 slants = 108 statics**, plus one variable file
that spans the whole space.

| axis | values |
|---|---|
| width | super condensed 62.5% · condensed 75% · normal 100% · wide 112.5% · expanded 125% · super expanded 150% |
| weight | thin 250 · extra light 275 · light 300 · regular 400 · medium 500 · semibold 600 · bold 700 · extra bold 800 · black 900 |
| slant | roman · oblique (drawn, 7.00°) |

Widths map cleanly onto CSS `font-stretch`, so the whole family is addressable as one
`font-family: 'Base Neue'`:

```css
h1 { font-family:'Base Neue'; font-weight:900; font-stretch:62.5%; }          /* super condensed black */
p  { font-family:'Base Neue'; font-weight:400; font-stretch:100%; }           /* regular */
em { font-family:'Base Neue'; font-weight:400; font-style:oblique 7deg; }     /* oblique  */
```

The variable file carries `wdth 50–150`, `wght 100–900`, `obli 0–1` and **108 named instances**,
so `'wght' 250 / 'wdth' 62.5` reproduces any static exactly.

### What was wrong and what changed

1. **Filenames** — every file arrived as `BaseNeue-CondensedBlack [tёlеġřa₥ - @аłł4dёšiġñer].ttf`,
   the bracket being the distributor's watermark in homoglyph-mixed Cyrillic. Stripped; the pack's
   real names (`BaseNeue-CondensedBlack`) kept.
2. **Name tables** — the Base Neue files were clean internally, but the Nerds Grotesk OTF had
   `t.me/all4designer` appended to **9 name records**, including family, style, copyright and the
   designer's URL. Scrubbed; original attribution preserved.
3. **Oblique italic metadata (the real bug)** — all 54 obliques shipped with `post.italicAngle = 0`
   and the italic bit unset, despite being genuinely slanted. InDesign, Figma and Word therefore
   cannot auto-pair `Wide Black` with its oblique — you had to pick the style by name. The slant was
   measured off the outlines (two independent methods, agreeing within 1°: mean stem edge vs
   principal axis of the `I` contour) and written back as `7.00°` ± 0.03 across all 54 files, with
   `head.macStyle` bit 0 and `OS/2.fsSelection` ITALIC set.
4. **Bold roman false positives** — `Normal Bold`, `Condensed Bold`, `Wide Bold`, `Expanded Bold`,
   `SuperCondensed Bold`, `SuperExpanded Bold` had the macStyle italic bit set on a *roman*, which
   makes macOS mis-group them. The whole library now reads `italicAngle = 0` for romans, `7.00°`
   for obliques, and no roman claims to be italic.

The variable file was deliberately left alone: its slant lives on the `obli` axis and its default
instance is roman.

### Caveat worth knowing

Weight **250 is a true hairline** — 22/1000 em, ~0.37px when set at 34px. It survives on retina and
in the specimen, but it will break up in print or at small sizes; set it 40px+ or use Extra Light.
The step from 250 → 275 (22 → 63 units) is a 3× jump, the largest gap in the ramp.

## Nerds Grotesk

Stéphanie Brusick — madebyste.com. One weight only, CFF-flavoured OpenType, 394 glyphs.
Straight display grotesk; no width or weight axis, so pair it rather than flex it.

## Provenance

Both families came from a telegram asset-distribution pack (the `.url` shortcut files in the
original archives point at `t.me/all4designer` and `t.me/design_supply`). Treat them as **personal
and demo use**; the foundries hold the licences, and neither pack came with one. Don't ship either
face inside a product or a client deliverable without buying them — Power Type and Made by Ste both
sell them directly.

## Using the specimen

It fetches fonts over relative URLs, so `file://` will trip Chrome's local-file policy — serve it:

```bash
cd fonts && python3 -m http.server 8000
# open http://localhost:8000/specimen.html
```

`specimen.html` is generated, not hand-written: `@font-face` declarations are emitted from the
binaries' own weight/width/slant metadata, so if the page renders correctly the family is wired
correctly. `specimen.png` is the full-page render at 2× with all 110 faces confirmed loaded and zero
fallback rendering.
