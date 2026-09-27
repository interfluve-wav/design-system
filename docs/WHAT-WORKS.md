# What works

Measured, not asserted. Every number below came from a command in `scripts/`
run against this folder at **2026-09-27 00:35–00:50 EDT**, headless Chromium
139.0.7258.5 at 1280×720 over `http://127.0.0.1:8765`.

The point of this file is that it is *checkable*: nothing here is inherited from
an earlier session's summary. Where an earlier claim turned out to be wrong or
sloppy, it is corrected in §4 rather than quietly dropped.

Re-run it:

```bash
python3 -m http.server 8765 --bind 127.0.0.1        # from this folder
python3 scripts/verify_renders.py                   # everything → docs/verify-report.txt
python3 scripts/verify_renders.py --only v4         # one artifact
python3 scripts/check_gif.py <file.gif> [...]
python3 scripts/check_cuts.py --fps 30
python3 scripts/brand_audit.py '<frames>/*.png' --allowed ff6b1a,ffffff,000000
python3 scripts/panel_coverage.py <frames> --cols 4 --rows 2
```

Brand source of truth is `bonk-beta/design.md`, which was read and does say
what the docs claim: `--brand-orange #ff6b1a`, jet black `#000000`–`#161616`,
white text, Volumo green `#00ff85` as an in-app accent only.

---

## 1. Verdict table

| Artifact | Renders | Brand-clean | Hooks | Verdict |
|---|---|---|---|---|
| `projects/blurreveal/public/v4-scenes.html` | ✅ | ✅ 0 off-hue px | `__seek`/`__scenes`/`__theme`/`__rebuild` | **works, use this** |
| `projects/blueprint/public/bonk-blueprint.html` | ✅ | ✅ | `__seek`/`__theme`/`__applyTheme` | works; black at both ends (§3.1) |
| `projects/motion-system/bonk-motion-system-v2.html` | ✅ | ✅ | `__seek`/`__theme`/`__applyTheme` | works |
| `projects/motion-system/bonk-motion-system.html` (v1) | ✅ | ✅ | none | works, live-only |
| `projects/design-tiles/public/design-tiles-demo.html` | ✅ | ✗ multi-palette | `__tiles` | works; palette is off-brand by design |
| `projects/libs-dev/bonk-libsdev.html` | ✅ | ✅ 0 off-hue px | none | works |
| `projects/dotcut/public/dotcut-demo.html` | ✅ | ✗ multi-palette | `PRESETS`/`PALETTES` | works; 4 presets, palettes read from CSS |
| `projects/dotcut/public/bonk-logo.html` | ✅ | ✗ multi-palette | `__bonk.setPalette` | works |
| `projects/dotcut/public/bonk-wordmark.html` | ✅ | ✗ 14,445 off-hue px | none | works (static poster) |
| `fonts/specimen.html` | ✅ | ✅ | none | works (static) |
| `projects/motion-system/bonk-intro-preview.html` | ✅ | ✅ | none | works; 1 dead beat (§3.2) |
| `logo/logo-lockup-compare.html` | ⚠️ paints | ✗ | none | **throws on load** (§3.3) |
| `index.html`, `demo.html`, `dotcut-A.html`, `blurreveal.html` | ❌ | — | — | **dead over plain HTTP** (§3.4) |

"Multi-palette" is not a defect in itself — those pages *are* palette switchers
with non-brand presets (KALEIDO/NEON/rainbow). They are not brand surfaces, so a
brand audit on them is informative only as a label.

---

## 2. What works, with the numbers

### `projects/blurreveal/public/v4-scenes.html` — the only blur-reveal scene file retained

- `window.__ready` resolves **true**, no page errors, no console errors.
- `__duration` = **15.485 s**; 16 frames swept frame-exactly via `__seek`, **0 dead frames**.
- Ink coverage 1.506% – 4.959% (mean 3.781%); mean luminance 2.12 – 8.69.
- **12/12 blocks draw inside their hold window** (3 samples per block, min ink 1.608%).
- Brand: **0 off-hue px** over 381,113 chromatic px / 14,745,600 sampled px.
- Theme contract holds: flipping `--accent` **and** `--accent-soft` to `#00ff85`
  gives orange 16,020 → **0** px and green 0 → 16,051 px; restoring gives orange
  back and green → 0. `__rebuild()` re-reads *and* repaints.
- `?scene=N` isolation works for all four: scene1 3.20% · scene2 4.82% ·
  scene3 4.27% · scene4 1.68% ink.
- Cut dimming, re-measured at 30 fps: **median 24.2%, worst 39.6%** over 11 cuts
  (baseline = the dimmer of the two adjacent holds). This is the known unfixed
  defect — two alpha-blended passes, the second multiplying the first by `1−α`.

### The delivered GIFs (`scripts/check_gif.py`)

| File | Frames | Size | ms/frame | Length | Dead frames | Loop seam |
|---|---|---|---|---|---|---|
| `bonk-blurreveal-v4-all-scenes.gif` | 232 | **1280×720** | 70 (14.3 fps) | 16.24 s | none | 0.000 |
| `bonk-blurreveal-v3.gif` | 98 | 1440×810 | 40 (25 fps) | 3.92 s | none | 0.000 |
| `bonk-blurreveal-v2.gif` | 88 | 1920×1080 | 50 (20 fps) | 4.40 s | none | 1.936 |
| `v1-scene1-bonk-mess.gif` | 132 | 1920×1080 | 40 (25 fps) | 5.28 s | none | 7.528 |

`v1` is the outlier by measurement, not by opinion: max ink **100%** (blown-out
frames) and a mean frame-to-frame delta of **24.5** against ~1.0 for the others.

---

## 3. Known defects — real, reproducible

### 3.1 `blueprint` is black at both ends of its 8 s loop
Dead frames at t = **0.00 s** (0.003% ink) and t = **7.47 s** (0.004%). Ink peaks
at 19.255% in between, so the sequence works; the two ends are empty. Either
deliberate (construction starts and resolves to nothing) or the tail is longer
than the content — decide which, because as a loop it reads as a 1 s black beat.

### 3.2 `intro-preview` has one dead beat
t = **1.26 s** → 0.000% ink, with 11.9% either side. A ~0.4 s gap between intro
phases, or a stage that fails to paint. One frame at 0.42 s spacing is the
resolution limit of the check — sample finer before calling it a bug.

### 3.3 `logo/logo-lockup-compare.html` throws on load
`pageerror: Cannot read properties of undefined (reading '0')` — every run. It
still paints 1.178% ink, so the failure is silent unless you listen for errors.
It is also 0 orange / 7,580 green px: the lockup comparison is rendering the
**off-brand** variant.

### 3.4 Four pages are dead over plain HTTP
`index.html`, `demo.html`, `dotcut-A.html`, `blurreveal.html` all fail with:

```
Failed to load module script: ... the server responded with a MIME type of "video/mp2t"
```

They `import './src/*.ts'`, and `python3 -m http.server` maps `.ts` to MPEG
transport stream. Consequences: `blurreveal.html` renders a **white** page
(100% ink, luma 255 — the trap where "has ink" is not "has content"),
`dotcut-A.html` is entirely **black** (5/5 dead frames), `index.html` and
`demo.html` are near-black. These need Vite (`vite.config.ts` is present). Do not
judge them from a static server — and do not judge a canvas failure from DOM
chrome, which is the same trap from the other side.

---

## 4. Corrections to earlier claims

| Earlier claim | Reality |
|---|---|
| "v4 GIF: 232 frames @ 15 fps, 11.0 MB" | 232 frames is right. It is **70 ms/frame = 14.3 fps**, **11.50 MB**, and **1280×720**, not 1920×1080. |
| "`scripts/brand_audit.py` / `scripts/panel_coverage.py`" (GOTCHAS §7) | **These did not exist.** The docs told you to run scripts that were never written. They exist now, and every number in this file came out of them. |
| "0 off-brand px over 4,608,000 samples" (v3/v4) | Different sample count here (14,745,600 px over 16 frames at 720p) and the same verdict: **0 off-hue px**. |
| "theme flip → 7,366 green px, 0 orange" | Reproduced in form, different resolution: 16,020 orange → **0**, 0 green → 16,051. The first run of my own harness reported a **FAIL** on `motion-system-v2`; that was my test, not the render (§5.2). |
| Cut dimming "24.8% median / 47.4% worst" | Median confirmed: **24.2%**. Worst is **sampling-dependent** — 39.6% at 30 fps/720p vs 47.4% recorded earlier at a coarser rate. Quote the median, and the method with it. |
| `v1-scene1.html` "preserved as the off-brand before-artifact" | Now in the Trash by request. The evidence survives in `v1-scene1-bonk-mess.gif` (§2) and in GOTCHAS §4.1. |

---

## 5. Measurement traps this pass walked into

Kept because each one produced a confident wrong number first.

### 5.1 Saturation alone manufactures phantom off-hue pixels
The first audit reported **11,419 off-hue px** on a correct v4 render. All of
them: hue 60–70°, example `#010100` — one unit of red on otherwise-black.
`#010100` has **S = 1.00** by the ratio definition while being visually black.
Fix: require a value floor too (`--val 0.10`). v4 then reads **0**. A saturation
cut without a brightness floor is not a brand check.

### 5.2 The theme flip has to flip *every* accent token
Flipping `--accent` alone left **1,820 orange px** on `motion-system-v2` and
looked like a broken theme hook. It was `--accent-soft` (`#ffb37a`, hue 26°,
inside the orange family) still holding its old value. Flip both: **0 orange**,
restore clean. A partial flip is a partial test.

### 5.3 Comments are not colours
The static scan called v4 "4 off-brand hex" — `#0b3d3a`, `#1b1440`, `#ff006e`,
`#0a0014`. All four appear only in v4's header comment *describing what v1 got
wrong*. Strip comments before scanning hex; report the scan's false positives in
the same breath as its hits.

---

## 6. Removed (2026-09-27)

By request — v4 onward only, CSS-themeable only. Moved to the macOS Trash, not
deleted, so they are recoverable:

- `projects/blurreveal/public/v1-scene1.html` — WebGL, off-brand palette, the class of
  file GOTCHAS §4.1 exists to catch
- `projects/blurreveal/public/text - copy.html` — the v2 pass (was `v2-scenes.html`)
- `projects/blurreveal/public/v3-scenes.html` — v3, CSS-themeable but scene 1 only

`projects/blurreveal/public/` now contains exactly `v4-scenes.html`.

Their GIFs in `Pictures/design - tiles/` were **left in place** — the request was
about scenes, and the v1 GIF is the surviving evidence for the off-brand lesson.

---

## 7. Not verified by this pass

Stated plainly so nobody inherits an unearned number:

- **The cut-dimming fix.** Not attempted. It needs both scene textures mixed in a
  single shader pass; the current render composites two alpha-blended draws.
- **`panel_coverage.py` has never caught a real bug yet.** It is written to the
  documented interface and runs, but the multi-panel capture sheets it exists for
  were not part of this pass. Treat it as unproven tooling.
- **Anything about `dotcut`'s letter rendering.** The `BONK` tracking/spacing work
  is in flight in another session; `dotcut-demo.html` was only audited, not judged.
- **The typeface lab** (`~/Documents/typeface-lab/`) — untouched here.
