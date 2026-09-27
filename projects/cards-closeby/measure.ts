export const REF_FS = 16;
export const BASELINE_Y = 13;

export interface GlyphMetrics {
  ch: string;
  x: number;
  w: number;
  top: number;
  bottom: number;
}

export interface WordMetrics {
  width: number;
  glyphs: GlyphMetrics[];
}

export function measureWord(word: string, fontFamily: string, weight: string): WordMetrics | null {
  const cv = document.createElement("canvas");
  cv.width = 2048;
  cv.height = 64;
  const ctx = cv.getContext("2d");
  if (!ctx) return null;

  ctx.font = `${weight} ${REF_FS}px ${fontFamily}`;
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";

  const metrics = ctx.measureText(word);
  const fullW = metrics.width;
  const ascent = metrics.actualBoundingBoxAscent;
  const descent = metrics.actualBoundingBoxDescent;

  const bm: GlyphMetrics[] = [];
  let cx = 0;
  for (const ch of word) {
    const gm = ctx.measureText(ch);
    const g: GlyphMetrics = {
      ch,
      x: cx,
      w: gm.width,
      top: -ascent,
      bottom: descent,
    };
    cx += gm.width;
    bm.push(g);
  }

  return { width: fullW, glyphs: bm };
}
