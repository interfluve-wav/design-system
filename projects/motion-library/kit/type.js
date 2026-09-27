/* ══════════════════════════════════════════════════════════════════════════
   type.js — measured glyph layout, written once.

   Every bug this file exists to prevent was paid for separately, in a different
   piece, by someone re-deriving glyph metrics by hand (GOTCHAS §8.10–§8.12):

     · a size computed in GRID CELLS but drawn in CANVAS PIXELS came out 6x too
       small, and read as reasonable in code review — a scale factor in a
       coordinate system you are not drawing in is invisible
     · a hardcoded cap-height ratio (0.72em) instead of measureText()
     · `fillText(whole string)` cannot do tracking — canvas ignores CSS
       letter-spacing entirely — so per-glyph placement is mandatory
     · with textAlign="center" the x you pass is the glyph's CENTRE, so
       advancing by width drifts the line by half a letter
     · the width fit MUST include the tracking gap or the last letter runs off

   So: never hand-roll this again. If a piece needs letters placed, it calls
   MotionType. All of the above is handled once, here, and measured.

     const L = MotionType.fit(ctx, M.params.label, {
       size: H * 0.06, tracking: M.params.tracking, maxW: W * 0.8
     });
     MotionType.draw(ctx, L, W / 2, H / 2);
     // per-glyph reveal windows come free:
     L.glyphs.forEach(g => clipTo(g.x, g.w) && ctx.fillText(g.ch, g.cx, L.baseline));
   ══════════════════════════════════════════════════════════════════════════ */
(function (global) {
'use strict';

function font({ family, weight, style, size }){
  return (style ? style + ' ' : '') + (weight || 400) + ' ' + size + 'px ' +
         (family || "'Bonk','Bonk Display',system-ui");
}

/* the ink height of ONE glyph, measured — never assumed.
   A capital H has no overshoot and no descender, so it gives the true
   cap-height of the loaded face, which is what "fit this word to that box"
   actually means. */
function inkHeight(ctx, probe){
  const m = ctx.measureText(probe || 'H');
  const a = m.actualBoundingBoxAscent, d = m.actualBoundingBoxDescent;
  if (a === undefined || (a === 0 && d === 0)) {
    /* old engine: fall back to the font box, and say so in the layout */
    return { h: (m.fontBoundingBoxAscent || 0) + (m.fontBoundingBoxDescent || 0),
             measured: false };
  }
  return { h: a + d, ascent: a, descent: d, measured: true };
}

/* ── fit ───────────────────────────────────────────────────────────────────
   Returns a layout object. Nothing is drawn. The returned size is the size
   AFTER fitting, so callers must draw with `layout.font`, not with their own
   re-derived string. */
function fit(ctx, text, opt){
  opt = opt || {};
  const str    = String(text == null ? '' : text);
  const chars  = Array.from(str);
  const track  = opt.tracking == null ? 0.10 : opt.tracking;
  const fitH   = opt.capFrac == null ? 0.92 : opt.capFrac;
  let   size   = Math.max(1, opt.size || 100);

  /* measure at the requested size, then solve for the size that satisfies
     whichever constraint binds — height first, then width. */
  const probe = opt.probe || 'H';
  ctx.font = font({ ...opt, size });
  const ink = inkHeight(ctx, probe);

  if (opt.maxH && ink.h > 0){
    size = size * ((opt.maxH * fitH) / ink.h);
  }

  ctx.font = font({ ...opt, size });
  const widths = chars.map(c => ctx.measureText(c).width);
  const gap    = size * track;
  let   total  = widths.reduce((a, b) => a + b, 0) + gap * Math.max(0, chars.length - 1);

  /* the width fit includes the gaps, or the last letter runs off the canvas */
  if (opt.maxW && total > opt.maxW){
    const k = opt.maxW / total;
    size  *= k;
    for (let i = 0; i < widths.length; i++) widths[i] *= k;
    total *= k;
  }

  const ink2 = (() => { ctx.font = font({ ...opt, size }); return inkHeight(ctx, probe); })();
  const gapF = size * track;

  /* CENTRE OF ADVANCE, not left edge. With textAlign:'center' the x passed to
     fillText is the glyph centre, so the cursor must advance along centres or
     the whole line drifts by half a letter. */
  let cursor = -total / 2;
  const glyphs = chars.map((ch, i) => {
    const w  = widths[i];
    const cx = cursor + w / 2;          // centre, relative to the line's centre
    cursor  += w + gapF;
    return { ch, i, w, cx, x: cx - w / 2, gap: i < chars.length - 1 ? gapF : 0 };
  });

  return {
    text: str,
    glyphs,
    size,
    gap: gapF,
    total,
    ascent:  ink2.ascent  || 0,
    descent: ink2.descent || 0,
    inkHeight: ink2.h,
    measured: ink2.measured,
    font: font({ ...opt, size }),
    opt
  };
}

/* ── draw ──────────────────────────────────────────────────────────────────
   (x, y) is the CENTRE of the line box. align picks which edge y refers to. */
function draw(ctx, L, x, y, opt){
  opt = opt || {};
  const align = opt.baseline || 'middle';       // middle | alphabetic | top
  const base  = align === 'middle' ? y + L.inkHeight / 2
              : align === 'top'    ? y + L.ascent
              : y;
  const save  = ctx.textAlign;
  ctx.textAlign = 'center';
  ctx.font = L.font;
  const per = opt.perGlyph;                     // (g, i, base) => boolean  |draw?
  L.glyphs.forEach((g, i) => {
    if (per && per(g, i, base) === false) return;
    ctx.fillText(g.ch, x + g.cx, base);
  });
  ctx.textAlign = save;
  return base;
}

/* ── verification ──────────────────────────────────────────────────────────
   GOTCHAS §8.12: a render meant to spell something should be READ BACK as a
   character grid. On a 45x28 grid that is a legible block of text; it catches
   "does it spell the word" and "are the letters separated" at a glance, with
   no vision model and no pixel statistic that can be subtly wrong. */
function ascii(mask, cols, rows, on, off){
  on = on === undefined ? '#' : on;
  off = off === undefined ? '.' : off;
  const out = [];
  for (let r = 0; r < rows; r++){
    let line = '';
    for (let c = 0; c < cols; c++) line += mask[r * cols + c] ? on : off;
    out.push(line);
  }
  return out.join('\n');
}

/* fit a whole line to a box and report whether it actually fits — used by the
   scanner to catch a model whose copy outgrew its frame after an override */
function overflows(L, box){
  return { w: L.total > (box.w || Infinity), h: L.inkHeight > (box.h || Infinity) };
}

global.MotionType = { fit, draw, ascii, overflows, font, inkHeight };
})(window);
