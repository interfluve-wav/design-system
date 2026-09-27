## DotCut Integration Guide

### Mounting
1. **Import and mount** — Drop `<DotCutView>` into any React component. It auto-creates the canvas, sets up ResizeObserver for DPR-capped redraws, and respects `prefers-reduced-motion`.

2. **Tweak parameters** — Pass props to control the grid: `cols` (default 42), `squareness` (0 = circle, 1 = rounded square), `hold` / `morph` (durations in ms), `brush` (pointer retraction radius), `fill` (scale factor 0-1).

### Testing workflow
- **Static mode** — Use `<DotCutView autoplay={false} />` to freeze on scene 0 ("A"). Great for verifying the glyph rasterization, the even-odd ring compositing, and pixel-perfect circle contacts.
- **Step through scenes** — Call `engine.advance()` from React dev tools or a temporary button to cycle one scene at a time. Each transition is a fresh morph with per-cell delay.
- **Check edge cases** — Resize the window to verify the grid recomputes (pitch from width / (cols + 2×margin), whole rows fitted and centered). Test DPR 1 and 2 to confirm pixel density handling.

### Performance
- The engine accumulates one `Path2D` per frame under even-odd rule — no per-cell `fill()` calls. If you see jank, check that `this.cols * this.rows` isn't exceeding ~5000 on very large viewports.
- rAF loop pauses when `document.hidden` or `prefers-reduced-motion: reduce`. Tab over to another window — the loop should stop consuming CPU.

### Wiring into Bonk
- Place the component inside the existing React viewport structure (`src/components/`).
- Import from `@/dotcut` (already aliased via the barrel `src/dotcut/index.ts`).
- For the pointer brush: the host element receives `onPointerMove` events mapped through `toCell()` to fractional cell coordinates. The brush retracts circles in a squared-falloff radius — test by hovering over different grid regions.
