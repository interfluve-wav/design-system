# Build ledger — Bonk design + motion

**Running record.** Everything built, everything delivered, and the launch-video plan.
Append to §7 as work lands; keep §3 and §4 honest or the rest of the file is decoration.

Last updated **2026-09-27 06:20 EDT**.
Verification in §4 was re-run in this pass — not inherited from an earlier summary.

---

## 0. Where everything lives (paths moved this session)

| What | Path |
|---|---|
| Build sandbox | `/Users/suhaas/Pictures/motion - design - assets` |
| Delivered GIFs / MP4s | `/Users/suhaas/Pictures/design - tiles - motion` |
| Public repo (partial) | https://github.com/interfluve-wav/design-system |

> ⚠️ **The GIF folder was renamed mid-session: `design - tiles` → `design - tiles - motion`.**
> Every `~/Pictures/design - tiles/...` path written before 2026-09-27 06:10 is now stale,
> including the ones in `README.md` §"Green Finder tags". The five green-tagged items were
> re-checked with `mdls` after the move and all five still carry **Green**; two still carry
> **bomb** as well. Nothing was lost — the paths in prose are what need fixing.

`projects/motion-assets/` (`ripple.html`) appeared during this session and was **not** in
`README.md` — it has been added to the table in §2 and to the README's project list.

---

## 1. Live links

Server is **running** at the time of writing. If a link 404s, restart it:

```bash
bash "/Users/suhaas/Pictures/motion - design - assets/scripts/serve.sh"
```

All 17 entry points below were checked with `scripts/check_links.py` — **17/17 return HTTP
200**. Re-run that after any rename or new project; a ledger full of dead links is worse
than no ledger.

| Project | Link |
|---|---|
| **blur-reveal v4** (the launch reel) | http://127.0.0.1:8765/projects/blurreveal/public/v4-scenes.html |
| blur-reveal v4, light theme | http://127.0.0.1:8765/projects/blurreveal/public/v4-light-scenes.html |
| **motion system v3** (real new mark) | http://127.0.0.1:8765/projects/motion-system/bonk-motion-system-v3.html |
| motion system v2 | http://127.0.0.1:8765/projects/motion-system/bonk-motion-system-v2.html |
| blueprint (mark construction) | http://127.0.0.1:8765/projects/blueprint/public/bonk-blueprint.html |
| blueprint v2 | http://127.0.0.1:8765/projects/blueprint/public/bonk-blueprint-v2.html |
| blueprint v3-sup | http://127.0.0.1:8765/projects/blueprint/public/bonk-blueprint-v3-sup.html |
| dotcut (BONK as negative space) | http://127.0.0.1:8765/projects/dotcut/public/dotcut-demo.html |
| bonk-logo | http://127.0.0.1:8765/projects/dotcut/public/bonk-logo.html |
| bonk-wordmark poster | http://127.0.0.1:8765/projects/dotcut/public/bonk-wordmark.html |
| design-tiles | http://127.0.0.1:8765/projects/design-tiles/public/design-tiles-demo.html |
| libs-dev showcase | http://127.0.0.1:8765/projects/libs-dev/bonk-libsdev.html |
| logo lockup compare | http://127.0.0.1:8765/projects/logo/logo-lockup-compare.html |
| bonk superscript mark | http://127.0.0.1:8765/projects/logo/bonk-sup.html |
| motion-assets / ripple (new) | http://127.0.0.1:8765/projects/motion-assets/ripple.html |
| font specimen | http://127.0.0.1:8765/fonts/specimen.html |
| intro preview | http://127.0.0.1:8765/projects/motion-system/bonk-intro-preview.html |

**These are localhost links — they work on this Mac only.** There is no public host yet.
That is the single biggest gap before a launch video can point anywhere (§6.1).

---

## 2. What's built — by project

Eight projects, framework-agnostic, each opens with no build step.

| Project | What it is | Entry point | Verified? |
|---|---|---|---|
| `blueprint/` | Real traced BONK wordmark — source of truth for mark geometry + the trace/verify pipeline. 3 registers: v1, v2, v3-sup | `public/bonk-blueprint.html`, `-v2`, `-v3-sup` | ✅ renders; 2 dead frames (§4) |
| `blurreveal/` | The promo reel. 4 scenes, CSS-themeable, dark + light | `public/v4-scenes.html`, `public/v4-light-scenes.html` | ✅ **dark is the clean one** |
| `dotcut/` | Circle-grid negative space; B/O/N/K carved as holes | `public/dotcut-demo.html`, `bonk-logo.html`, `bonk-wordmark.html` | ✅ renders (ground check needed, §4) |
| `motion-system/` | Motion primitives on the real traced mark. v1/v2/v3 + intro preview | `bonk-motion-system-v3.html` | ✅ **v3: 0 dead frames, 0 off-hue, theme flip both ways** |
| `design-tiles/` | Word tiles with per-glyph colour blocks | `public/design-tiles-demo.html` | ✅ renders |
| `cards-closeby/` | Sentence-as-tiles horizontal bar, fly-in + shuffle | source only, no demo | — |
| `libs-dev/` | Component-library showcase render | `bonk-libsdev.html` | ✅ renders, brand-clean |
| `logo/` | Wordmark SVG, lockup comparison, alt-mark reference, **canonical mark** | `logo-lockup-compare.html`, `current/README.md` | ⚠️ lockup page throws (§4) |
| `motion-assets/` | New this session — `ripple.html` | `ripple.html` | not yet verified |

**The mark.** `projects/logo/current/bonk-mark.js` is canonical — built from the *exact vector
data*, not a trace. `627 × 262`, origin `{687, 869}`. Verified against the asset: IoU `0.9777`
raw, `0.999161` at 1 px, **`1.000000` at 2 px**. A render must subtract `MARK.origin` or the
whole mark shifts by ~800 px. `blueprint/public/wordmark-paths.js` is **a different drawing**
(IoU 0.342, 4 glyphs vs 6) and must not be used in new work.

---

## 3. Delivered files

Location: `/Users/suhaas/Pictures/design - tiles - motion`
**62 GIFs** (31 at root + 31 in subfolders) · **5 MP4s** · **3 PNGs**.

### Reels — the launch candidates (root)

| File | Size | Made |
|---|---|---|
| `bonk-blurreveal-v4-all-scenes.gif` | 11.0 MB | 09-27 00:11 — **the reel: 232 frames, 1280×720, 14.3 fps, 16.24 s** |
| `bonk-motion-system-v3-newlogo.gif` | 3.6 MB | 09-27 05:12 — **newest, real mark** |
| `bonk-motion-system-v3-newlogo-light.gif` | 3.6 MB | 09-27 05:13 |
| `bonk-motion-system-v3-bonktype.gif` / `-light` | 3.7 MB ea | 09-27 04:52–53 |
| `bonk-motion-system-v3-primitives.gif` / `-light` | 3.7 MB ea | 09-27 04:14–15 |
| `bonk-libsdev-showcase.gif` | 9.1 MB | 09-26 10:26 |
| `bonk-motion-system-v2-mark.gif` | 14.9 MB | 09-26 23:13 |

### Blueprint (mark construction)

`bonk-blueprint-v3-sup-teal-purple.gif` + `.mp4` · `bonk-blueprint-v2-pastel-yellow.gif` ·
`bonk-blueprint-sequence-full.gif` (6.7 MB) · `bonk-blueprint-evidence.gif` ·
three `-retract` variants (gif + mp4) · `bonk-watermark-sup-teal-purple.gif` + `.mp4`.

### blur-reveal history

`bonk-blurreveal-v2.gif` (5.1 MB) · `-v3.gif` (5.7 MB) · **`-v4-all-scenes.gif`** ·
light-theme runs: `-v4-light.gif`, `-v2/-v3/-v4`, `-v5-30fps.gif` (14.8 MB),
`-speed15.gif` (10.3 MB).

### dotcut

`bonk-dotcut-bonk-word.gif` / `-v2` / `-v3` · `dotcut-default.gif`.

### Earlier marks / superseded (kept, not deleted)

`bonk - textured bg - render/` × 4 · `empty - big center - box/` × 4 ·
`logo - small - splash/` × 6 (`dotcut-*`, `bonk-logo-v3-*`) ·
`video - sketch/` × 2 · `v1-scene1-bonk-mess.gif` + `-v2` (the off-brand before-artifact).

### Design tiles (message GIFs)

`design - message - tiles/` × 9 · `kaleido - flash - bitmap/` × 2.

### 🟢 Protected — never delete or archive

All five carry a **green** Finder tag; two also carry **bomb** (meaning *not yet established*,
so treat as don't-know rather than safe to remove). **Re-verified after the rename**:

| New path | Tags |
|---|---|
| `design - tiles - motion/kaleido - flash - bitmap/` | Green |
| `design - tiles - motion/design - message - tiles/design-tiles-by-dj-for-a-dj.gif` | Green, bomb |
| `design - tiles - motion/design - message - tiles/design-tiles-by-dj copy.gif` | Green, bomb |
| `motion - design - assets/projects/blueprint/` | Green |
| `motion - design - assets/projects/design-tiles/` | Green |

Check with: `mdls -name kMDItemUserTags -raw <path>`

---

## 4. Verification status

Fresh run, `2026-09-27 06:07 EDT`, headless Chromium at **1280×720** over
`http://127.0.0.1:8765`. Full transcript: `docs/verify-report.txt`.

| Artifact | Ready | Duration | Ink % min–max | Dead | Off-hue px | Verdict |
|---|---|---|---|---|---|---|
| `blurreveal` v4 (dark) | ✅ | 15.485 s | 1.506 – 4.959 | 0 | **0** | **works, use this** |
| `blurreveal` v4 light | ✅ | 15.485 s | — (light ground) | 0 | 204,412 | renders; see note |
| `motion-system` v3 | ✅ | 6 s | 1.712 – 4.589 | 0 | **0** | **works** |
| `motion-system` v2 | ✅ | 4.4 s | 7.790 – 13.777 | 0 | **0** | works |
| `motion-system` v1 | — | live-only | 3.435 – 11.265 | 0 | 0 | works, no hooks |
| `blueprint` | ✅ | 8 s | 0.003 – 19.255 | **2** | 0 | works; black at both ends |
| `blueprint` v2 | ✅ | 8 s | 0.003 – 10.667 | **2** | 911,512 | pastel by design |
| `blueprint` v3-sup | ✅ | 8.7 s | 0.000 – 11.302 | **2** | 33,890 | teal/purple by design |
| `dotcut-demo` | — | live-only | — (light ground) | 0 | 1,760,978 | renders; 4 presets |
| `bonk-logo` | — | live-only | 38.261 – 100 | 0 | 2,430,141 | palette switcher |
| `bonk-wordmark` | — | live-only | 1.603 | 0 | 14,445 | static poster |
| `design-tiles` | — | live-only | 2.271 – 3.147 | 0 | 86,125 | palette is off-brand by design |
| `libsdev` | — | live-only | 28.028 – 28.206 | 0 | **0** | works |
| `logo-lockup` | — | live-only | 1.178 | 0 | 5,145 | ⚠️ **throws on load** |
| `bonk-sup` | — | live-only | 21.786 | 0 | 21,435 | teal/purple by design |
| `font-specimen` | — | live-only | 5.668 | 0 | 0 | works (static) |
| `intro-preview` | — | live-only | 0.000 – 11.939 | **1** | 0 | 1 dead beat |

Theme contract: `blurreveal-v4`, `blueprint` ×3, `motion-system` v2/v3 all flip
orange → 0 and green 0 → N, and restore. **`blurreveal-v4-lt` restore FAILED** this pass.

### The two rows that are *not* defects

An ink metric is "pixels with luma > 60" — true for the dark brand surfaces, meaningless on a
light page, where a blank sheet reads 100% ink. Measured grounds (`scripts/ground_check.py`):

- `blurreveal-v4-lt` — mean frame luma **240–245**, 96.7% of pixels above 200. Light page.
- `dotcut-demo` — mean RGB **(206, 145, 140)**, 47% above 200. Light page.

Both were then **looked at**, not just counted:

- `v4-lt` renders a legible centred lockup, scene 1: *"Duplicate rows. / Broken cues. XML /
  export hell."* — with teal accents, which is why it reads 204k off-hue. By design.
- `dotcut-demo` renders **BONK** carved out of a cream dot grid on magenta. Real content.
- `motion-system-v3` renders the real **bonk dj** mark, orange on black, with the identity
  panel. Correct mark, not `wordmark-paths.js`.
- `blurreveal-v4` renders the scene-1 quote — **and the on-page demo chrome is baked into the
  capture**: a `BONK` mark top-left, a `V2 · BLUR-REVEAL` badge top-right, a
  `CUT · DIAGONAL` label. Any capture carries that chrome unless it's stripped (§6.3).

### Live defects

1. **`blueprint` is black at both ends** — t=0.00 s (0.003% ink) and t=7.47 s (0.004%).
   Peaks at 19.255% between. As a loop it reads as a 1 s black beat. Same in v2 and v3-sup.
2. **`intro-preview` dead beat** at t=1.26 s (0.000%, 11.9% either side). Sample finer before
   calling it a bug — 0.42 s spacing is the resolution limit.
3. **`logo-lockup-compare.html` throws on load** —
   `pageerror: Cannot read properties of undefined (reading '0')`. It still paints, so the
   failure is silent unless you listen for errors. It also renders the **off-brand** variant.
4. **`blurreveal-v4-lt` theme restore fails.** Flip succeeds, restore does not.
5. **Cut dimming** on v4 — median **24.2%**, worst 39.6% at 30 fps. Not fixed; needs both scene
   textures mixed in one shader pass instead of two alpha-blended draws.

### Script changes made this session

- `scripts/verify_renders.py` — the `PAGES` list still held **pre-refactor paths**
  (`blurreveal/public/...` with no `projects/`), so it reported every entry point MISSING.
  Fixed, and extended to the newer artifacts (`v4-light`, `blueprint` v2 + v3-sup,
  `motion-system` v3, `bonk-sup`). The four dead Vite pages were dropped — they no longer
  exist at the root.
- `scripts/check_cuts.py` — same stale path, fixed.
- New `scripts/ground_check.py` — is a high ink% real content, or a light ground?
- New `scripts/make_vision_frames.py` — downscale frames to ~320 px; vision times out on 720p.
- New `scripts/serve.sh` — one command to bring up the preview server the links need.
- New `scripts/check_links.py` — asserts every §1 link returns 200. **17/17 now.**

**The class of bug, not the instance:** a folder refactor silently invalidated hardcoded
paths in two verification scripts, and they kept *succeeding* while measuring nothing —
`MISSING` rows are not failures in that harness. Any time this tree is reorganised, re-run
`verify_renders.py` and read the first column before trusting a single number below it.

---

## 5. Launch video — the plan

Source: `design - tiles - motion/bonk - new plan (blur-reveal).md` (written 09-11).

### The long cut — 4 scenes, no voiceover (≈15.5 s)

| # | Copy | Asset |
|---|---|---|
| 1 | Rekordbox metadata is a mess. / Duplicate rows. Broken cues. XML export hell. / Staring at a corrupted library hours before a gig. / We've all been there! | `v4-scenes.html?scene=1` — 3.20% ink |
| 2 | It's about time we managed things smarter & faster. / Meet Bonk DJ. / …so you can focus on the important part — Music! | `?scene=2` — 4.82% |
| 3 | Read and write directly to your Rekordbox.db / No more XML round-trips or sync errors (unless that's what you're into) / Bulk edit tags… | `?scene=3` — 4.27% |
| 4 | Beta live now. Help us test… / Get started: **bonkmusic.app** | `?scene=4` — 1.68% |

All four isolate via `?scene=N` and hold inside their windows (12/12 blocks draw — measured).

### The short cut — 15 s, fast-cut text cards

`0–4 s` rekordbox metadata is broken · `4–8 s` duplicate rows. broken cues. xml hell. ·
`8–13 s` bonk fixes it. free. direct rekordbox sync & access. · `13–15 s` bonkmusic.app

### Why this is buildable today rather than shot

Every scene is a pure function of time and exposes the capture hooks, so frames come from
`__seek(t)` — not screen recording, no dropped frames, no drift:

- `window.__seek(seconds)` + `window.__duration` — drive to an exact time
- `window.__scenes()` — resolved block layout with hold windows
- `window.__theme` / `__applyTheme` / `__rebuild` — re-read CSS **and repaint**

Colour lives in CSS custom properties. A rasterised canvas reads them at build time, so a
theme flip needs `__rebuild()`, not just a variable change.

### Shot list, in order

1. Cold open on scene 1 — the corrupted-library quote. Hold 3 s.
2. `blueprint` construction, 0.5 s in to skip the black head, cut at 7.4 s. It draws the
   mark from geometry; strongest "this is a real tool" beat.
3. `motion-system` v3 primitives — the 8 motion primitives on the real mark, 6 s.
4. `dotcut` — BONK carved out of the dot grid. Best texture/interstitial beat.
5. Scenes 2–3 of blur-reveal — the turn from problem to product.
6. End card: scene 4 → `bonkmusic.app`. Needs a URL that resolves (§6.1).

---

## 6. Gaps before a launch video can ship

1. **No public host.** Everything is localhost + local files. The public repo
   (`interfluve-wav/design-system`) tracks **only `projects/dotcut/`** — the other seven
   projects have no version control at all. Options: GitHub Pages on that repo, or
   Cloudflare Pages. Either gives real links and costs nothing.
2. **No MP4 at launch quality.** Delivered motion is GIF, **1280×720 at 14.3 fps**. Fine for
   a README, not for a launch video. The `__seek` hooks make a 1080p/60 fps MP4 render a
   scripted job, not a re-do — but it hasn't been done for v4.
3. **Demo chrome is baked into captures.** `V2 · BLUR-REVEAL`, `CUT · DIAGONAL`, the top-left
   BONK mark. Strippable via a `?chrome=0` flag or a CSS override; not stripped yet.
4. **Audio.** Nothing exists. No music bed, no SFX.
5. **No 9:16 / 1:1 cut.** Reels and shorts need a portrait render; the pages are 16:9.
6. **Blueprint has no clean loop.** Black at both ends — fine for a shot, not for a loop.
7. **The typeface lab** (`~/Documents/typeface-lab/`) is outside this sandbox and untouched.

---

## 7. Changelog

Newest first. One line per pass, with what changed and what it was measured against.

**2026-09-27 06:20** — Ledger created (`LEDGER.md`), linked from `README.md`.
- Inventoried 9 projects, 62 GIFs, 5 MP4s, 3 PNGs.
- Re-ran verification against the current tree → §4. First run of the harness since the
  `projects/` refactor.
- Fixed the stale `PAGES` paths in `verify_renders.py` and `check_cuts.py`; added
  `ground_check.py`, `make_vision_frames.py`, `serve.sh`, `check_links.py`.
- Confirmed all 5 green Finder tags survived the `design - tiles → design - tiles - motion`
  rename, and corrected the stale paths in `README.md`.
- Read the launch script and mapped its 4 scenes to verified assets and measured ink.
- Checked the four "not a defect" rows by eye, not just by number: `v4-lt`, `dotcut-demo`,
  `motion-system-v3` and `blurreveal-v4` all render real content.

**2026-09-27 05:12** — `bonk-motion-system-v3-newlogo[-light].gif` delivered.
**2026-09-27 04:52** — `bonk-motion-system-v3-bonktype[-light].gif`.
**2026-09-27 04:14** — `bonk-motion-system-v3-primitives[-light].gif`.
**2026-09-27 03:42** — blueprint `-retract` variants, gif + mp4.
**2026-09-27 00:11** — `bonk-blurreveal-v4-all-scenes.gif`.
