#!/usr/bin/env python3
"""
Derive bonk-blueprint-v2.html from bonk-blueprint.html.

v2 changes vs v1:
  · mark      : the LOWERCASE lockup (bonk + small dj), or "bonk" outlined from
                Bonk-VF.ttf -- switchable with ?mark=lockup|font
  · colour    : pastel yellow #f5e663 replaces the brand orange, everywhere it
                appeared as a literal (theme var, JS fallbacks, and the single
                hardcoded glow rgba that v1 carried inline)
  · metrics   : lowercase means the x-height governs, not a cap height. The left
                dimension no longer claims to measure the cap height (it never did),
                and a nested x-height dimension is added.
  · glyphs    : 6 windows instead of 4, so the per-letter resolve stagger is retuned
                to keep the last letter landing on the beat.

Asserted transforms, not a rewrite: every replacement must match exactly once or the
build aborts. The source file is verified byte-identical before and after.
"""
import hashlib
from pathlib import Path

PUB = Path("/Users/suhaas/Pictures/motion - design - assets/projects/blueprint/public")
SRC = PUB / "bonk-blueprint.html"
DST = PUB / "bonk-blueprint-v2.html"

src = SRC.read_text()
before = hashlib.sha256(SRC.read_bytes()).hexdigest()

edits = []          # (label, old, new)


def edit(label, old, new):
    edits.append((label, old, new))


# ── 1. title ────────────────────────────────────────────────────────────────────
edit("title",
     "<title>BONK — blueprint reveal</title>",
     "<title>bonk.dj — blueprint reveal v2</title>")

# ── 2. theme: pastel yellow, plus a real variable for the glow ──────────────────
edit(":root theme",
     """  :root{
    --ground:#000000;
    --accent:#ff6b1a;
    --accent-soft:#ffb37a;
    --hair:rgba(255,255,255,0.30);
    --hair-dim:rgba(255,255,255,0.16);
    --hair-bright:rgba(255,255,255,0.62);
    --label:rgba(255,255,255,0.44);
  }""",
     """  :root{
    --ground:#000000;
    /* v2 swaps the brand orange for pastel yellow. The glow is a variable now too:
       v1 hardcoded its glow as a raw rgba literal inline in the canvas code, which is
       exactly the kind of stray number that survives a palette change and turns up
       still orange. That literal is gone; the colour comes from here. */
    --accent:#f5e663;
    --accent-soft:#fdf2ad;
    --accent-glow:rgba(245,230,99,0.38);
    --hair:rgba(255,255,255,0.30);
    --hair-dim:rgba(255,255,255,0.16);
    --hair-bright:rgba(255,255,255,0.62);
    --label:rgba(255,255,255,0.44);
  }""")

# ── 3. header comment ───────────────────────────────────────────────────────────
edit("header comment",
     """/**
 * BONK — blueprint reveal  (motion system part 1: construction -> mark)
 *
 * Grammar borrowed from the reference reel: a primitive becomes construction
 * geometry, the geometry is measured, and the measurement resolves into the
 * finished mark. What is NOT borrowed: the reference annotates a typeface with
 * type metrics; this annotates the real Bonk mark with its own traced numbers
 * (cap height, stroke, per-letter column windows, ink profile) pulled from
 * wordmark-paths.js. Nothing on screen is a decorative fake figure.
 *
 * House rules (bonk design.md): jet black canvas, ONE accent (#ff6b1a), mono
 * hairlines, no gradients, no noise, subtle drift only.
 *
 * Rendering is a pure function of time: renderAt(t) for t in [0, DURATION].
 * The rAF loop calls it during preview; the capture harness calls __seek(t)
 * so the exported GIF is frame-identical to playback.
 */""",
     """/**
 * bonk.dj — blueprint reveal, v2  (motion system part 1: construction -> mark)
 *
 * v2 differs from v1 in three ways, all of them measurement-honest:
 *   1. the mark is LOWERCASE (bonk + a small dj) and comes from real geometry --
 *      either the canonical SVG lockup (bonk-mark-v2.js) or "bonk" outlined from
 *      Bonk-VF.ttf (bonk-mark-font.js). Nothing is traced from a raster, so there
 *      is no IoU to report and none is claimed. ?mark=lockup|font switches.
 *   2. the accent is pastel yellow, not the brand orange.
 *   3. lowercase means the X-HEIGHT governs the mark, not a cap height. v1's left
 *      dimension was labelled with the cap height while it measured the whole box;
 *      on an uppercase mark those coincide to within a unit so it read true. On a
 *      lowercase mark they differ by nearly 2x and it would have read as a lie.
 *      That dimension is now labelled with the height it actually spans, and a
 *      nested x-height dimension carries the metric that matters.
 *
 * Grammar borrowed from the reference reel: a primitive becomes construction
 * geometry, the geometry is measured, and the measurement resolves into the
 * finished mark. What is NOT borrowed: the reference annotates a typeface with a
 * type-designer's placeholder figures; this annotates the real mark with its own
 * measured numbers -- x-height, ascender, baseline, stroke, per-glyph column
 * windows, ink profile. Nothing on screen is a decorative fake figure.
 *
 * House rules (bonk design.md): jet black canvas, ONE accent, mono hairlines, no
 * gradients, no noise, subtle drift only. v2's accent is pastel yellow; v1 used
 * the brand orange. Nothing else about the surface changes.
 *
 * Rendering is a pure function of time: renderAt(t) for t in [0, DURATION].
 * The rAF loop calls it during preview; the capture harness calls __seek(t)
 * so the exported GIF is frame-identical to playback.
 */""")
edit("JS fallbacks",
     """let ACCENT       = '#ff6b1a';
let ACCENT_SOFT  = '#ffb37a';""",
     """let ACCENT       = '#f5e663';
let ACCENT_SOFT  = '#fdf2ad';
let ACCENT_GLOW  = 'rgba(245,230,99,0.38)';""")

edit("applyTheme reads the glow",
     """  ACCENT      = g('--accent',      ACCENT);
  ACCENT_SOFT = g('--accent-soft', ACCENT_SOFT);""",
     """  ACCENT      = g('--accent',      ACCENT);
  ACCENT_SOFT = g('--accent-soft', ACCENT_SOFT);
  ACCENT_GLOW = g('--accent-glow', ACCENT_GLOW);""")

edit("__theme reports the glow",
     "window.__theme = () => ({ ground: GROUND, accent: ACCENT, accentSoft: ACCENT_SOFT });",
     "window.__theme = () => ({ ground: GROUND, accent: ACCENT, accentSoft: ACCENT_SOFT, accentGlow: ACCENT_GLOW });")

edit("glow uses the variable",
     "      ctx.shadowColor = 'rgba(255,107,26,0.35)';",
     "      ctx.shadowColor = ACCENT_GLOW;")

# ── 5. load both mark modules, pick per ?mark= ──────────────────────────────────
edit("script tags",
     '<script src="./wordmark-paths.js"></script>',
     '<script src="./bonk-mark-v2.js"></script>\n<script src="./bonk-mark-font.js"></script>')

edit("mark selection",
     "const MARK = window.BONK_MARK;",
     """/* Two real sources, same schema, so the renderer below is source-agnostic.
   ?mark=font  swaps in "bonk" outlined from Bonk-VF.ttf. */
const MARK_SOURCES = { lockup: window.BONK_MARK_V2, font: window.BONK_MARK_FONT };
const MARK_KEY = (new URLSearchParams(location.search).get('mark') || 'lockup').toLowerCase();
const MARK = MARK_SOURCES[MARK_KEY] || MARK_SOURCES.lockup;
const PROVENANCE = {
  lockup: ['SVG · CANONICAL LOCKUP', 'bonk + small dj'],
  font:   ['BONK VARIABLE · wght 700', 'OUTLINED VIA FONTTOOLS'],
};
const PROV = PROVENANCE[MARK_KEY] || PROVENANCE.lockup;""")

# ── 6. fold the mark's own origin into the transform ────────────────────────────
edit("origin offset",
     "  const m = new DOMMatrix().translate(ox, oy).scale(s, s);",
     """  /* v2 mark modules carry `origin` (the ink bbox's top-left in source units) because
     their path data is NOT pre-normalised to 0,0 the way v1's traced mark was. Folding
     it into the transform beats rewriting 5 KB of path data by hand. */
  const org = MARK.origin || { x: 0, y: 0 };
  const m = new DOMMatrix().translate(ox - org.x * s, oy - org.y * s).scale(s, s);""")

# ── 6b. widen the fit budget for wide marks ─────────────────────────────────────
edit("fit budget for wide marks",
     "  const targetW = Math.min(W * 0.40, (H * 0.60) * (MARK.width / MARK.height));",
     """  /* v1's budget was W*0.40, which is the BINDING constraint for any mark wider than
     about 1.9:1 -- and v2's lowercase lockup is 2.39:1. On a 16:9 frame that produced
     a 512x214 mark: a thin band with dead space above and below it. v1 never showed
     this because its uppercase mark was 1.18:1 and therefore height-limited.
     The budget now comes from the data block's position instead: the mark is centred
     at W*0.455 and the block sits at W*0.845, so 2*(0.845-0.455-0.06) = 0.66 is the
     widest it can go while keeping ~6% clearance. 0.62 sits inside that.
     Marks that were already height-limited are unaffected. */
  const targetW = Math.min(W * 0.62, (H * 0.60) * (MARK.width / MARK.height));""")

# ── 7. retune the resolve stagger for 6 glyphs ──────────────────────────────────
edit("resolve stagger for 6 glyphs",
     "  resolve: [2.55, 0.30],       // start, per-letter duration\n  resolveStagger: 0.09,",
     """  resolve: [2.55, 0.30],       // start, per-letter duration
  /* v1 had 4 letters at 0.09 stagger, landing the last one on T.beat (3.12).
     v2 has 6: (3.12 - 2.55 - 0.30) / 5 = 0.054 keeps that landing. */
  resolveStagger: 0.054,""")

# ── 8. metrics: x-height governs ────────────────────────────────────────────────
edit("normMetrics",
     """function normMetrics() {
  return {
    capHeight: MARK.metrics.capHeight,
    strokeWidth: MARK.metrics.stemWidth,
    inkCoveragePct: MARK.metrics.inkCoveragePct,
    letterCount: MARK.metrics.letterCount,
  };
}""",
     """function normMetrics() {
  /* Lowercase: the governing vertical metric is the x-height. `ascender` and
     `baseline` come along so the vertical dimensions can be drawn honestly --
     ascenders overshoot the x-height and the j descends below the baseline, so
     the box height is NOT the x-height and must not be labelled as one. */
  const met = MARK.metrics;
  return {
    xHeight: met.xHeight,
    ascender: met.ascender,
    baseline: met.baseline != null ? met.baseline : met.ascender,
    strokeWidth: met.stemWidth,
    inkCoveragePct: met.inkCoveragePct,
    letterCount: met.letterCount,
  };
}""")

edit("renderAt destructure",
     "  const { capHeight, strokeWidth, inkCoveragePct, letterCount } = normMetrics();",
     "  const { xHeight, ascender, baseline, strokeWidth, inkCoveragePct, letterCount } = normMetrics();")

# ── 9. the left dimension stops mislabelling itself ─────────────────────────────
edit("height dimension label",
     "      text(fmt(capHeight), 0, 0, ACCENT_SOFT, u(13), 'center', 600);",
     """      /* labelled with the height it actually spans (ascender top to j descender),
         not the cap height. On v1's uppercase mark those matched to within 1 unit. */
      text(fmt(MARK.height), 0, 0, ACCENT_SOFT, u(13), 'center', 600);""")

# ── 10. add the nested x-height dimension ───────────────────────────────────────
edit("x-height dimension",
     "  // stroke-width dimension across the first stem",
     """  /* Nested x-height dimension: the metric that actually governs a lowercase mark.
     Sits inside the left cap line so the two verticals read as a pair -- the outer
     measuring the box, the inner measuring the letters. */
  if (t >= T.dimLeft[0] + 0.25 && guidesOut < 0.9) {
    const p = expoOut(win(t, T.dimLeft[0] + 0.25, T.dimLeft[1] + 0.25));
    const x = left - u(24);
    const yb = top + baseline * s;
    const yx = yb - xHeight * s;
    ctx.globalAlpha = guideAlpha;
    hair(x + 0.5, yx, x + 0.5, yb, ACCENT_SOFT, 1);
    [0, 1].forEach((k) => {
      const y = k ? yb : yx;
      hair(x - u(6), y + 0.5, x + u(6), y + 0.5, ACCENT_SOFT, 1);
    });
    if (p > 0.85) {
      ctx.globalAlpha = guideAlpha * clamp01((p - 0.85) / 0.15);
      text(fmt(xHeight), x - u(11), (yb + yx) / 2, ACCENT_SOFT, u(12), 'right', 600);
      ctx.globalAlpha = 1;
    }
    ctx.globalAlpha = 1;
  }

  // stroke-width dimension across the first stem""")

# ── 11. data block: honest provenance and the real metrics ──────────────────────
edit("data block rows",
     """      ['BONK / WORDMARK', ACCENT, 13, 600],
      ['TRACED · RASTER → VECTOR', LABEL, 11, 400],
      ['IoU 0.9905', LABEL, 11, 400],
      ['', null, 0, 0],
      [`W ${fmt(MARK.width)}`, null, 12, 400],
      [`H ${fmt(capHeight)}`, null, 12, 400],
      [`STROKE ${fmt(strokeWidth)}`, null, 12, 400],
      [`INK ${inkCoveragePct.toFixed(1)}%`, null, 12, 400],
      [`LETTERS ${letterCount}`, null, 12, 400],""",
     """      ['bonk.dj / WORDMARK', ACCENT, 13, 600],
      [PROV[0], LABEL, 11, 400],
      [PROV[1], LABEL, 11, 400],
      ['', null, 0, 0],
      [`W ${fmt(MARK.width)}`, null, 12, 400],
      [`H ${fmt(MARK.height)}`, null, 12, 400],
      [`X-HEIGHT ${fmt(xHeight)}`, null, 12, 400],
      [`ASCENDER ${fmt(ascender)}`, null, 12, 400],
      [`STROKE ${fmt(strokeWidth)}`, null, 12, 400],
      [`INK ${inkCoveragePct.toFixed(1)}%`, null, 12, 400],
      [`GLYPHS ${letterCount}`, null, 12, 400],""")

# ── 12. __config hook, mirroring the blurreveal v4 pattern ──────────────────────
edit("__config hook",
     "window.__duration = DURATION;",
     """window.__duration = DURATION;
/* Resolved config, so a variant can be ASSERTED rather than eyeballed: a ?mark=
   switch that silently fell back, or a palette that failed to apply, still renders
   a valid-looking reel. Check the resolved numbers, not the source. */
window.__config = () => ({
  markKey: MARK_KEY, markSource: MARK.source,
  markW: MARK.width, markH: MARK.height, origin: MARK.origin,
  glyphs: MARK.letters.length, metrics: MARK.metrics,
  accent: ACCENT, accentSoft: ACCENT_SOFT, accentGlow: ACCENT_GLOW, ground: GROUND,
  duration: DURATION,
});""")

# ── apply, asserting each match ─────────────────────────────────────────────────
out = src
for label, old, new in edits:
    n = out.count(old)
    if n != 1:
        raise SystemExit(f"ABORT: '{label}' matched {n} times, expected exactly 1")
    out = out.replace(old, new)

DST.write_text(out)

after = hashlib.sha256(SRC.read_bytes()).hexdigest()
assert before == after, "SOURCE FILE WAS MODIFIED — this build must be non-destructive"

# ── verify no orange survives anywhere ─────────────────────────────────────────
import re
orange = re.findall(r'#ff6b1a|#ffb37a|255,\s*107,\s*26|ff,\s*6b,\s*1a', out, re.I)
print(f"wrote {DST.name}: {len(out):,} bytes  ({len(edits)} asserted edits)")
print(f"source untouched: sha256 {after[:16]}… matches before ✓")
print(f"orange literals remaining: {len(orange)}  {'✓' if not orange else '✗ ' + str(orange)}")
print(f"pastel-yellow references: {out.count('#f5e663')} (#f5e663) + {out.count('#fdf2ad')} (#fdf2ad)")
