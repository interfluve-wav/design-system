export interface Glyph {
  ch: string;
  x: number;
  y: number;
  w: number;
  h: number;
  top: number;
  bottom: number;
}

export interface WordMetrics {
  width: number;
  glyphs: Glyph[];
  ascent: number;
  descent: number;
}

// Reference font size for measuring; engine scales results down to display size.
export const REF_FS = 72;

// Baseline Y for the reference font size.
export const BASELINE_Y = 0;

let canvas: HTMLCanvasElement | null = null;
let ctx: CanvasRenderingContext2D | null = null;

function getCanvas() {
  if (canvas) return { canvas, ctx: ctx as CanvasRenderingContext2D };
  canvas = document.createElement("canvas");
  canvas.width = 1;
  canvas.height = 1;
  const c = canvas.getContext("2d", { willReadFrequently: true });
  if (!c) throw new Error("2d context not available");
  ctx = c;
  ctx.font = "normal 500 " + REF_FS + "px system-ui";
  ctx.textBaseline = "top";
  return { canvas, ctx: c };
}

export function measureWord(
  word: string,
  fontFamily: string,
  fontWeight: string = "500",
): WordMetrics | null {
  try {
    const { ctx } = getCanvas();
    ctx.font = fontWeight + " " + REF_FS + "px " + fontFamily;
    ctx.textBaseline = "top";

    const full = ctx.measureText(word);
    const fm = full.fontBoundingBoxAscent ?? REF_FS * 0.7;
    const fd = full.fontBoundingBoxDescent ?? REF_FS * 0.3;

    const glyphs: Glyph[] = [];
    let x = 0;
    for (const ch of word) {
      const gm = ctx.measureText(ch);
      const gw = gm.width;
      const top = -fm;
      const bottom = fd;
      glyphs.push({
        ch,
        x,
        y: top,
        w: gw,
        h: fm + fd,
        top,
        bottom,
      });
      x += gw;
    }

    return {
      width: full.width,
      glyphs,
      ascent: fm,
      descent: fd,
    };
  } catch {
    return null;
  }
}
