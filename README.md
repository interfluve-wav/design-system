# design-system

A collection of self-contained, framework-agnostic design components and interactive demos. Each system lives in its own subfolder with source code, a standalone demo, and render assets.

## Components

### dotcut (`dotcut/`)

A dense grid of ~42 circles on a square lattice. Circles open into rings by boring a hole from their center, and a letter (B/O/N/K) or pattern cuts through as negative space — the glyph is always a hole in the surface, never drawn on top. The grid cycles through 6 scenes (text, rings, columns, checker, boxes, bars), each carrying a different letter (B→O→N→K→B→O...).

**Key design constraints:**
- Single composite `Path2D` filled in one `ctx.fill(path, "evenodd")` call — no per-cell draw calls
- Letter rasterized at grid resolution (one sample per cell) and AND'd with the pattern mask
- Two patterns legible at once: carve (scene) + texture (style field) on perpendicular axes
- Circle color and background color are matched pairs so the glyph keeps reading as negative space

**Files:**
- `src/` — TypeScript source (scenes, engine, React wrapper)
- `public/dotcut-demo.html` — standalone demo (opens in any browser, no build step)
- `assets/` — renders and reference captures

**Run the demo:**
```bash
cd cards-close=off/public
python3 -m http.server 8000
# then open http://localhost:8000/cards-demo.html
```

### cards-close=off (`cards-close=off/`)

A short lowercase sentence ("design is how it works") rendered as a seamless horizontal bar of adjacent solid-color SVG tiles. Each word is its own rectangle, auto-sized to glyph widths, uniform height, no gaps, the whole bar rounded as one unit. Each tile carries a bold, saturated, deliberately-clashing swatch with baked-in auto-contrast text (white on dark, near-black on bright). On reveal the tiles fly in via `clip-path`-style `grid-template-columns` transitions (text never distorts). The bar then idly shuffles — each tile re-rolls to a different swatch on its own timer, and hovering a tile re-rolls it immediately. Plain DOM/CSS, no canvas or framework. Reduced-motion shows the assembled bar, static.

**Key design constraints:**
- Framework-agnostic core: mount on any element, `start()`/`stop()`/`destroy()` lifecycle
- Word measurement via off-screen canvas `measureText` → per-letter SVG `<rect>` masks + `<text>` overlay
- Clip-open animation uses `grid-template-columns` (`0fr → 1fr`) with `overflow: hidden`, not `scaleX` — text never distorts
- Shuffle loop is a single `requestAnimationFrame` tick checking per-tile timers
- Hover re-roll excludes colors currently in use by other tiles for contrast
- `prefers-reduced-motion` short-circuits to `renderStill()` (static assembled bar)

**Files:**
- `src/palette.ts` — word list, swatch array with baked foreground colors, random selection helpers
- `src/measure.ts` — off-screen canvas word/letter measurement utilities
- `src/engine.ts` — `DesignTiles` class: DOM construction, layout, fly-in, shuffle loop, hover
- `src/index.ts` — barrel export
- `src/style.css` — host container styles
- `public/cards-demo.html` — standalone demo (opens in any browser, no build step)
- `assets/` — renders and reference captures

**Run the demo:**
```bash
cd cards-close=off/public
python3 -m http.server 8000
# then open http://localhost:8000/cards-demo.html
```

## Adding a new system

```
mkdir systems/<name>
# Add source to systems/<name>/src/
# Add demo to systems/<name>/public/
# Add renders to systems/<name>/assets/
# Update this README
```

## License

MIT
