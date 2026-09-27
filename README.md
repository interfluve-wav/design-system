# design-system

Working sandbox for Bonk's design + motion work: the brand mark, motion reels, and
self-contained HTML demos. Each project is framework-agnostic, opens in a browser with
**no build step**, and renders in real brand tokens.

> **Public repo:** [interfluve-wav/design-system](https://github.com/interfluve-wav/design-system)
> — everything is tracked except `_archive/`. See *Git state*.

> **→ `LEDGER.md`** is the running record: every artifact, every delivered file, fresh
> verification numbers, and the launch-video plan. Read it before asking what exists.

## Layout

```
projects/      the work — self-contained pieces
cards-close=off/  its own thing at the root (added upstream)
docs/          what works, what broke, and why
scripts/       verification tooling
preflight.py   blocks a render that would duplicate an existing asset
LEDGER.md      running record + launch-video plan
assets/gifs/   14 exported GIFs (gitignored)
fonts/         base-neue, nerds-grotesk
_archive/      scratch + cruft held back for review (gitignored)
```

### ⚠️ `src/` and `node_modules/` are symlinks — not part of this folder

```
src          -> ~/Documents/GitHub/bonk-beta/src
node_modules -> ~/Documents/GitHub/bonk-beta/node_modules
```

They exist so the preview harness can bundle **real** components with esbuild from the
app's own modules. `du` will not count them; this folder is ~62 MB.

**Never put a trailing slash on them.** `rm -rf src` removes a harmless link.
`rm -rf src/` follows the link and deletes the actual app source.

### 🟢 Green Finder tags are protected — never delete

Five items carry a **green** Finder tag and must never be deleted or archived:

| Where | Item |
|---|---|
| here | `projects/blueprint/` |
| here | `projects/design-tiles/` |
| `~/Pictures/design - tiles - motion/` | `kaleido - flash - bitmap/` |
| `~/Pictures/design - tiles - motion/` | `design - message - tiles/design-tiles-by-dj-for-a-dj.gif` |
| `~/Pictures/design - tiles - motion/` | `design - message - tiles/design-tiles-by-dj copy.gif` |

> **The GIF folder was renamed** from `design - tiles/` to `design - tiles - motion/` on
> 2026-09-27. All five tags were re-verified with `mdls` at the new paths. If you find
> `~/Pictures/design - tiles/` in older notes, it no longer exists.

Tag data survives `mv`, so check the **destination** after any move. Verify with:

```bash
mdls -name kMDItemUserTags -raw <path>     # prints "( Green)" etc.
```

Some items in `design - tiles - motion/` also carry a **`bomb`** tag
(`dotcut-default.gif`, `logo - small - splash/dotcut-bonk-mix.gif`) — meaning not yet
established, so treat those as *don't-know* rather than safe-to-remove.

## projects/

| Project | What it is | Entry point |
|---|---|---|
| `blueprint/` | **The real traced BONK wordmark** — source of truth for mark geometry, plus the trace/verify pipeline | `public/bonk-blueprint.html` |
| `blurreveal/` | Blur-reveal promo reel, all 4 scenes, CSS-themeable (dark + light) | `public/v4-scenes.html` |
| `dotcut/` | Circle-grid negative-space engine; B/O/N/K carved as holes, 4 palettes | `public/dotcut-demo.html` |
| `motion-system/` | 8 motion primitives applied to the real mark — v1/v2/v3 | `bonk-motion-system-v3.html` |
| `motion-library/` | The parameterised piece kit + browsable gallery | `index.html` |
| `motion-assets/` | New — per-shot motion pieces | `ripple.html` |
| `instagram/` | 30s reel + 5-slide carousel sources and their renderers | `reel.html` |
| `design-tiles/` | Word tiles with per-glyph colour blocks | `public/design-tiles-demo.html` |
| `cards-closeby/` | Sentence-as-tiles horizontal bar, fly-in + shuffle | source only |
| `libs-dev/` | Component-library showcase render | `bonk-libsdev.html` |
| `logo/` | Wordmark SVG, lockup comparisons, alt-mark reference, **canonical `current/bonk-mark.js`** | `logo-lockup-compare.html` |

Also in `dotcut/public/`: `bonk-logo.html` (wordmark carved as negative space) and
`bonk-wordmark.html` (static wordmark + tagline poster).

## cards-close=off (`cards-close=off/`, at the repo root)

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

## Preview

```bash
cd "/Users/suhaas/Pictures/motion - design - assets"
python3 -m http.server 8765 --bind 127.0.0.1
# then http://localhost:8765/projects/dotcut/public/dotcut-demo.html
```

Animated renders expose hooks for deterministic capture — use them rather than
screen-recording:

- `window.__seek(seconds)` + `window.__duration` — drive a scene to an exact time
- `window.__scenes()` — resolved block layout (multi-block reels)
- `window.__theme` / `__applyTheme` / `__rebuild` — re-read CSS **and repaint**

Colour lives in CSS custom properties (`:root`), never hardcoded in JS — a rasterised
canvas still reads them at build time.

## Git state

Tracked in the public repo — **everything except `_archive/`**.

`_archive/` is held back deliberately: pre-change copies, superseded versions, and
duplicate font binaries. It stays on disk as a local safety net and is listed in
`.gitignore` so it cannot drift into the published history.

`src/` and `node_modules/` are ignored too, being symlinks into the sibling bonk-beta
checkout. Both patterns are **root-anchored** (`/src`, `/node_modules`) so they cannot
swallow real source at `projects/*/src/` or `cards-close=off/src/`.

History is authored as `interfluve <interfluv3@gmail.com>`.

## docs/

| File | What it is |
|---|---|
| `GOTCHAS.md` | tooling / rendering / verification / brand gotchas — symptom → cause → fix |
| `WHAT-WORKS.md` | per-file verification status, plus what was removed and when |
| `verify-report.txt` | raw transcript behind `WHAT-WORKS.md`; regenerate, don't trust |
| `DotCut-Integration.md` | how to wire dotcut into bonk-beta |

## _archive/

Held back, **not deleted** — prune once you've eyeballed it.

- `root-scratch/` — 21 Jul-31 scratch screenshots + stray demo HTML from the first sessions
- `cruft/` — 9 `.DS_Store` files (paths preserved), the empty `assets/assets/` nested dupe
- `pre-pathfix/` — every `.md` file and the Obsidian KB as they were *before* the
  2026-09-27 refactor moved projects into `projects/`

## Adding a project

```
projects/<name>/{src,public,assets}
```

Add a `public/<name>.html` that opens with no build step, expose `__seek` if it animates,
keep colour in CSS, then add a row to the table above.

## License

MIT
