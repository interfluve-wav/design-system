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
cd dotcut/public
python3 -m http.server 8000
# then open http://localhost:8000/dotcut-demo.html
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
