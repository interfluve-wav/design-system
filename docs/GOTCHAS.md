# Gotchas — learned by actually running the tools

Notes from the motion-design + BonK build sessions. Every entry here was found by
executing something and measuring it, **not** by reading code and reasoning about
it. Most of them are silent: the tool exits 0, the file looks fine, and the output
is wrong.

Rule of thumb behind all of these: **a claim is not a fact until a tool agrees.**
Colours, timings, "the render worked", and even my own assumptions all turned out
to be wrong at least once.

---

## 1. Shell & tooling

### 1.1 ffmpeg eats the loop's stdin, silently corrupting filenames
**Symptom** — a `while read` loop over a spec file wrote `02_smoke.mp4` as
`smoke.mp4`. Only the leading characters vanished; the rest of the line parsed
correctly, so the timings were right and only the label was wrong.

**Cause** — `ffmpeg` reads stdin even when given `-i <file>`. The loop's stdin
*was* the spec file, so ffmpeg consumed the first bytes of the next line before
`read` got to it.

**Fix** — give the loop a private file descriptor, and starve inner commands:
```bash
while IFS= read -r line <&3 || [ -n "$line" ]; do
  ffmpeg ... </dev/null
done 3< "$SPEC"
```
**Why it matters** — it fails *silently and partially*. Any command inside a
`while read` loop that touches stdin (`ssh`, `mysql`, `ffmpeg`, `read` itself,
anything with a prompt) can do this.

### 1.2 When a minimal repro passes but the real script fails, instrument the real script
The `_smoke` bug above passed every isolated test I wrote — the parsing was
provably correct on its own. I burned time rebuilding the repro instead of adding
one `echo` inside the actual script. The corruption only existed *in context*
(ffmpeg running in the loop), which is precisely what the repro omitted.

**Rule** — copy the real script, insert tracing, run that. If the repro passes and
reality fails, the difference *is* the bug, and the difference is whatever you
left out.

### 1.3 A crashing pipeline can be hidden by a passing one
A `printf | cut | awk` chain died with an awk syntax error caused by escaped
quotes inside a heredoc. The command still "ran". Read exit codes.

---

## 2. Captures & rendering

### 2.1 A capture can exit 0 and write a perfectly valid, entirely blank GIF
ffmpeg succeeds, the file has 88 frames and a sensible size, and every frame is
black. Nothing in the exit path complains.

**Worse** — DOM chrome (labels, badges, counters) still renders when the WebGL
canvas fails, so *a small positive ink reading proves nothing*. An early check of
mine returned "has content" on a broken render because the badge text supplied
3.7% ink.

**Fix** — measure, and hide the chrome when you need certainty:
```bash
python3 scripts/brand_audit.py …        # or sample frames for non-black pixels
```

> **Correction 2026-09-27:** the capture script this section used to name
> (`capture_gif.py`) **no longer exists and never lived in the repo** — it was a
> `/tmp` one-liner, so every number it printed was unreproducible. What exists now
> is the other direction: `python3 scripts/check_gif.py render.gif` measures a
> finished GIF (frames, per-frame ink, dead beats, loop seam). Run the spec and the
> capture you actually have, then measure the artifact.

### 2.2 The video timeline starts at page load, not at the animation
`--settle 1.2` + `--reload` are *inside* the recording. A `--trim 0.8` therefore
lands in the dead lead-in before anything painted, producing a black opening.
Trim from the start of **recording**, not from when the animation begins.

### 2.3 Screenshot slowness is irrelevant if renders are a pure function of time
A 1080p screenshot costs ~300–400 ms, which makes naive screenshot sampling
useless for sub-second motion. But if the page exposes `window.__seek(t)` and
rendering is pure (`renderAt(t)`), each frame is a distinct `t` — so slowness
costs nothing and the capture becomes frame-exact with no trim to guess.

**Do this** — expose `__seek` + `__duration` from the start, then capture in
`--mode seek`. It also deletes the entire class of trim bugs in 2.2.

### 2.4 Cancel the rAF loop before seeking
If the preview loop keeps running, it draws its own clock between your seek and
the screenshot, and captures come out as a mix of seeked and live frames.

### 2.5 Pick one time unit and stick to it
I shipped `window.__duration` in **seconds** and `window.__seek` taking
**milliseconds**. Both "worked" — which is exactly why it was dangerous. The
blueprint page used seconds, so seconds won.

### 2.6 Re-uploading a texture every frame
Calling `texImage2D` from a 1080p source canvas 60×/s is a large, invisible cost.
Build GL textures once per scene and rebind.

### 2.7 A shader compile failure kills the whole script
The constructor throws, the page goes black, and nothing explains why. I also
*introduced* invalid GLSL (`tex.a0(0.0)`) that would never have compiled — it was
caught only because I ran the page.

**Fix** — wrap context/program creation in `try/catch` and `console.error` the
reason, so a shader failure degrades loudly instead of silently.

---

## 3. Verification

### 3.1 A single screenshot cannot validate a 2–7 s loop
Panels acquire empty tails, or render 0% of their intent while the code runs
clean. Sampling **one** timestamp found neither of the two real bugs; sampling
22–60 found both. The dense sweep is what caught a 0.60 s dead window in a 4.4 s
loop and a 0.60–1.4 s black beat at every scene cut.

### 3.2 Dead beats hide at the seams too
Overlapping scene A's blur-out with scene B's blur-in fixes internal cuts — and
leaves the *loop seam* with the same gap. Make the loop period deliberately
shorter than the final scene's window so the last transition wraps into the first.

### 3.3 Distinguish a legitimate 0% from a bug
A panel reading 0% can be legitimate (a looping primitive that resets) or a bug
(geometry off-panel, or an unintended dead tail). Tell them apart by measuring the
**duration** of the empty window, not by its existence. A 0.20 s reset inside a
4.4 s loop is design; 0.60 s of nothing reads as a pop.

### 3.4 Diagonal-wipe clip geometry fails silently
An off-panel clip polygon renders **nothing**, with no error, while the animation
"runs". Reveal region is `x + y <= thr` with `thr = prog * (W + H)`; branch on the
threshold. Symptom: ink stays near 0% at every timestamp.

### 3.5 `vision_analyze` hallucinates text on spec-sheet images
On the blueprint sheet it confidently reported a typeface attribution ("GOTHAM"),
a category label ("MAIN LOGOTYPE"), and values that appear **nowhere** in the
source. The real rows read `TRACED · RASTER → VECTOR` and `IoU 0.9905`.

**Rule** — trust the source for values; use vision only for form, composition,
and "is this roughly the thing I expect". Never quote numbers it read off a
picture.

### 3.6 Vision times out on big images, repeatedly
Downscale to ~900–1300 px, retry once, then **switch to measurement** instead of
stalling the task. PIL pixel sampling answered most of the questions I was going
to ask anyway.

---

### 3.7 A thresholded-ink metric cannot tell *blurred* from *dark*
`pixels > 60` counts bright pixels. Blur **spreads** light without losing it, so a
heavily blurred frame reports far less "ink" while being no darker at all. An
80%-blurred crossover reads 0.79% ink and looks like a dead beat; its mean
luminance is fine.

→ For a *dark beat* question, use **mean luminance**. Reserve ink coverage for
*is anything drawn at all*.

### 3.8 A ratio against the wrong baseline manufactures defects

Two of these in one session, both reported as real findings before a raw trace
exposed them:

| Metric | Reported | Truth | Why |
|---|---|---|---|
| Nearest-RGB brand audit, tol 26 | 2.9% off-brand (723,333 px) | **0.00%** | Flagged anti-aliased greys between ink and ground. Hue-family audit, with near-achromatic treated as in-family, is the correct check. |
| Crossover "dip depth" vs **mean of both neighbours** | 64.5% worst, 41.8% median | wrong | Averaged a dim block with one 3× brighter. |
| …then vs the **outgoing hold** | 72.9% worst, 38.2% median | still wrong | Adjacent blocks differ from 2.1 to 8.4 in mean luminance, so "the outgoing hold" is not the level the frame *should* be at mid-cut. |
| …finally vs the **dimmer of the two adjacent holds** | — | **24.8% median, 47.4% worst** | This is the one: it asks "did the frame go darker than *either* side?", and it lands on the ~25% that the alpha-blend math predicts independently. |

→ **When several baselines disagree, the one that agrees with an independent
prediction is the correct one.** That is what settled this — not a fourth opinion.

→ **When a metric returns a shocking number, print the raw trace before acting on
it.** Every time, the render was correct and the arithmetic was not; acting on any
of them would have meant refactoring working code to chase a phantom.

→ Ask what the baseline *means*. "Compared to what?" decides whether a number is a
finding or an artifact.

### 3.9 An ink metric that assumes the ground is worse than no metric

Testing "brighter than N" is a **dark-ground** test. Point it at a light-ground render and
it selects the *background*, reporting ~100% ink on every frame and a bbox span of exactly
`0.000` — numbers that look like a pass while auditing nothing. It bit three separate times
in one session: the reference reel (light ground, `#f0f0f0`), a light theme register, and
the capture script's own log, which printed `100.000%` and green-lit the file.

Establish the ground first (modal or median luma of the frame) and measure ink as
**distance from the ground, in either direction**. At a black ground this reproduces the
old fixed threshold exactly, so it is a generalisation and not a behaviour change.
`capture_gif.py` and `panel_coverage.py` both had the bug; both are fixed.

### 3.10 A font that failed to load looks completely plausible

A `@font-face` that 404s does **not** throw — it silently falls back, and the render looks
fine. `document.fonts.check()` is not sufficient on its own either; it can report true for
a face that never painted a glyph.

The decisive test: draw the same string twice, once with the font and once with the
fallback, and compare the pixels. Identical output means it never loaded. Measured for
Bonk: 6,062 ink px in Bonk vs 5,543 in the fallback — a **9.4%** difference, which is the
only evidence that the type is actually the brand's.

### 3.11 A primitive that builds from nothing is empty at its own `ph = 0`

Each primitive starts at zero progress, so every one of them has a moment with nothing on
screen. Phase-offsetting panels spreads those moments out rather than removing them, and
sampling can then miss them — one register passes while the other fails, which reads as a
rendering bug rather than a design one. Give each primitive a persistent floor and take
the floor from the reference: reels are rarely empty either (a dot field measured
`1.07 -> 2.92 -> 0.16%`; a specimen grid is busy at `7.59%` on frame one).

**Alpha is not register-neutral**, so the floor cannot be a literal. 12% orange on black
reads plainly; 12% teal on cream reads as nothing. Make it a CSS custom property beside the
palette. And check the floor clears the ground by enough to be *measured*: on cream
`#f5f9e9` with ink `#36453b`, `a=0.09` gives luma 223 and `a=0.38` gives 175 against a
180 threshold. Finally, check geometry too — a banded reveal translates its content out of
its own clip at zero progress, so it paints nothing at any opacity, which is exactly what a
registration ghost exists to prevent.

## 4. Brand

### 4.1 Never trust an existing render's palette — grep it
`projects/blurreveal/public/v1-scene1.html` contained **ten hex values and every one was
off-brand**: teal `#0b3d3a`, coral `#ff4d4d`, violet `#1b1440`, a `#0a0014`
stage, and a `#ff006e` **pink** wordmark dot. It looked plausible in isolation.

An earlier round of dotcut / design-tiles / wordmark renders used sunset and
rainbow palettes for the same reason. Both had to be rebuilt.

> **Update 2026-09-27:** `v1-scene1.html` was moved to the Trash as the pre-v4
> pass. The evidence survives in `v1-scene1-bonk-mess.gif` — measured max ink
> **100%** and a mean frame-to-frame delta of **24.5** against ~1.0 for the v2–v4
> renders. See `docs/WHAT-WORKS.md` §2.

**Rule** — before building on any file, list its colours and classify them against
the authoritative design doc. `design.md` for Bonk: brand surface is black
`#000000`–`#161616` + white + `#ff6b1a` **only**. Volumo green `#00ff85` is an
in-app accent and never a brand surface.

### 4.2 Brand colour at low alpha is not a different colour
`#ff6b1a` at 20% over black is `(51, 21, 5)`, hue ≈ 20°. A naive nearest-RGB
check flags those as violations and reports thousands of false positives on a
correct render. **Filter by hue family**, skip near-achromatic pixels, and print
the histogram so the verdict is legible.

**…and a saturation cut alone is not enough.** The first run of
`scripts/brand_audit.py` reported **11,419 off-hue px** on a correct v4 render.
Every one of them was hue 60–70°, example `#010100` — one unit of red on
otherwise-black. `#010100` has **S = 1.00** by the ratio definition while being
visually black, so the near-achromatic filter never fired. Require a **value
floor** as well (`--val 0.10`); v4 then measures **0**.

**And comments are not colours.** A hex scan flagged v4's header comment — which
*describes v1's off-brand palette* — as four off-brand values in a brand-correct
file. Strip `<!-- -->`, `/* */` and `//` before scanning, and report the scan's
false positives next to its hits.

### 4.3 `mix-blend-mode: difference` inverts into off-brand hues
It looks great on black and turns magenta/cyan the moment the background isn't.
Plain colour on black is safer.

### 4.4 A documented brand asset may not exist
`design.md` cited `BonkWordmark.tsx` — the component doesn't exist.
`@fontsource/bungee-inline` is cited as the wordmark font — it isn't installed.
`UI_STANDARDS.md` still specifies `#e91e63` pink pills and `rgba(0,200,255)` blue
selected rows, both violating the single-accent rule.

**Rule** — verify a doc against the repo (`ls`, `grep`) before building on it, and
report the drift rather than silently picking a side.

---

## 5. Assets & tools

### 5.1 The brand mark is not a font — hunt for the traced asset first
An intro and a motion-system demo both rendered the wordmark with
`fillText('Bonk')` / a substituted mono font, while the project **already had the
mark traced to vector paths** with cap-height, stem-width, ink-coverage metrics, a
per-letter column map, an ink profile, and an IoU-0.9905 trace pipeline — one
folder over, untracked.

Traced geometry is *better* animation material than live text: per-letter wipe
windows and ink profiles come free, with no font loading, no metric guessing and
no FOUT.

**Rule** — before animating any letterform, search for existing traced assets and
the pipeline that produced them:
```bash
find . \( -iname '*wordmark*' -o -iname '*logo*' -o -iname '*trace*' -o -iname '*blueprint*' \)
grep -rl 'viewBox\|<path d=\|_MARK' --include=*.js --include=*.html .
```

### 5.2 Previews must load the real component
A hand-built CDN preview drifted from the shipped component immediately. It also
blanked twice: an import map missing `react/jsx-runtime`, then an `esm.sh` URL
404ing because `?external=react,react-dom` contains a slash.

**Fix** — bundle the actual component with esbuild from the project's own
`node_modules`. The preview then *cannot* diverge.

### 5.3 Ease strings are not portable between libraries
GSAP's `'power2.out'` is not a valid Framer Motion easing. Passing it through
fails silently or falls back. Bridging two libraries requires an explicit
mapping table.

### 5.4 The most reusable asset is often the least protected
`projects/blueprint/` (traced wordmark, metrics, verify pipeline), `projects/motion-system/` and
`projects/libs-dev/` are all **untracked** in git. The most valuable thing in the folder
has no version control.

---

### 5.5 A superseded mark keeps getting used until it has one obvious home

Old marks stay on disk because old renders and old GIFs reference them — but nothing marks
them as old, so the next render reaches for whatever path it saw last. Every render now
loads from `projects/logo/current/`, and that folder's README lists what is superseded and
why. Nothing was deleted.

Two exports of the same mark should never be assumed identical. A newer export differed
from the older one by `+14.666` in x on one glyph, `+20.633` on another, and `+15.5` in y
on all of them — re-laid-out horizontally and padded vertically, with the aspect moving
`3.2844 -> 3.1162`. A rescale would have been wrong by 5%.

## 6. Claims I made and had to retract

Kept here on purpose — these were stated confidently and were wrong.

| Claim | Reality |
|---|---|
| "WebGL does not work in plain headless Chromium." | **False.** Measured identical ink (3.548%) with and without software-GL flags. The black capture was a **trim** bug (2.2). I removed the claim from the script comment and rewrote it to say the opposite. |
| "The blur-reveal GIF is black — WebGL failed." | It was a dead **trim lead-in**; the content after it was fine. |
| "The motion system is brand-correct." | It demoed every primitive on substitute **text**, not the real mark (5.1). |
| "The intro is done." | It used JetBrains Mono where a traced wordmark existed. |
| "The brand audit flags 2.9% off-brand pixels — 723,333 of them." | **The check was wrong, not the render.** Nearest-RGB matching flagged anti-aliased greys. The hue-family audit found **0.00%** across 4,608,000 px (3.8). |
| "The cuts dim the frame by 42%, worst 65%." | Wrong baseline **twice** — first the mean of both neighbours (65%), then the outgoing hold (38%). Measured against the dimmer adjacent hold the true flash is **24.8% median / 47.4% worst**, matching the alpha-blend prediction (3.8). |
| "The blur peaks are making the frame dark." | Thresholded ink conflates *blurred* with *dark*. Mean luminance was flat (3.7). |
| "Run `scripts/brand_audit.py` / `scripts/panel_coverage.py`" | **Neither file existed.** The docs pointed at a verification method that was never written down as code, so its numbers could not be reproduced. Both exist now, plus `check_gif.py` and `check_cuts.py`. |
| "The v4 GIF is 232 frames @ 15 fps, 11.0 MB." | 232 frames is right; the rest is not. **70 ms/frame = 14.3 fps**, **11.50 MB**, and **1280×720**, not 1080p. Frame count is not a spec. |
| "11,419 off-brand px in the v4 render" *(my own first run, 2026-09-27)* | Phantom. Saturation-only metric; every hit was hue 60–70° at `#010100` — one unit of red on black. Needs a value floor. Real count: **0**. |
| "`motion-system-v2`'s theme flip is broken" *(my own first run, 2026-09-27)* | The **test** was incomplete — it flipped `--accent` and left `--accent-soft` (`#ffb37a`, hue 26°) orange. Flipping both: 0 orange. |

**Rule** — before writing a cause into a comment, a skill, or a report, test the
alternative. A wrong comment is worse than no comment, because the next reader
believes it.

---

## 7. The check that pays for itself

> **Update 2026-09-27:** these scripts are now real, in `scripts/`. Until this
> date the paths below were documented but **the files did not exist** — every
> number in the docs was produced by ad-hoc one-liners, which is exactly why some
> of them could not be reproduced.

```bash
# 0. does it render at all — errors, ink, hue, every timed block, theme flip
python3 scripts/verify_renders.py                 # all artifacts
python3 scripts/verify_renders.py --only v4       # one

# 1. is anything actually drawn, at every point in the cycle?
python3 scripts/panel_coverage.py ./frames --cols 4 --rows 2 --box … --gap …

# 2. is every chromatic pixel inside the brand hue family?
python3 scripts/brand_audit.py './frames/*.png' --allowed ff6b1a,ffffff,000000 --hue-tol 25

# 3. measure the delivered artifact, not the page that made it
python3 scripts/check_gif.py render.gif           # frames, dead beats, loop seam

# 4. how hard does each cut flash?
python3 scripts/check_cuts.py --fps 30            # dip vs the DIMMER adjacent hold
```

Run these before claiming a render works. "Looks right" has been wrong every single
time it was the only evidence. `scripts/verify_renders.py` writes `docs/verify-report.txt`,
which is the raw transcript behind `docs/WHAT-WORKS.md` — regenerate it rather than
quoting this file.

---

## 8. Theming & motion

### 8.1 `smootherstep` peaks its velocity exactly where a crossfade is worst

A crossfade composites `α·A + (1−α)·B`, so its rate of change is `|α′| · |A − B|` —
largest **mid-crossover**, where two different contents overlap. `smootherstep` is
the "smoothest" standard curve and puts its **peak** velocity (1.875) precisely
there. A trapezoid velocity profile (ease 18%, constant middle, ease 18%; peak 1.22)
cut the max frame delta **44%**.

Corollary: **spikiness (max/median frame delta) holding flat while the mean falls
means the problem is structural, not a shortage of easing.** Stop tuning curves and
go find what is broken.

### 8.2 Blur should peak where the overlap peaks

A linear blur ramp leaves both scenes half-sharp at the midpoint — two readable
texts superimposed. Reach full blur **by** the midpoint, so the disruptive moment is
two smears blending instead of two texts fighting.

### 8.3 A move that resets per scene snaps at every cut

A push-in restarting at scale 1.0 on each scene is continuous *within* a scene and
discontinuous *across* them. Run one move over the whole loop — and if the reel
loops, make it travel out **and back**, or a monotonic ramp snaps at the seam
instead.

### 8.4 A texture-baked colour cannot see CSS

Rasterising text into a WebGL texture puts it beyond CSS's reach, so a hardcoded
constant becomes the only way to change it and every variant becomes a code edit.
Read custom properties at texture-build time, and expose a rebuild hook:

```js
window.__rebuild = () => { readTheme(); rebuildTextures(); renderAt(lastT); };
```

The GL **clear colour is the ground** and must come from the theme too, or a light
theme renders on black. Query-param overrides (`?accent=%2300ff85`) let a variant be
previewed with no JS at all.

### 8.5 A theme hook that re-reads without repainting renders stale

`window.__seek()` cancels the rAF loop. So a theme hook that only re-reads the
variables changes every value and repaints **nothing** — while the theme reader
reports the new colour perfectly. Caught live:

```
before flip:                orange=387,826  green=0
after flip, NO re-render:   orange=387,826  green=0     <- stale frame
  __theme() reports accent=#00ff85                       <- variable DID change
after flip + re-render:     orange=0        green=387,853
```

It is the same failure the pixel-count check exists to catch, sitting in the API
rather than the render. **Re-read and redraw in the same hook**, and keep a `lastT`
so the hook knows which frame to repaint.

For a canvas-only render (no textures) the low-churn conversion is to keep the
existing constant *names*, make them `let`, and mirror CSS into them — every call
site stays untouched:

```js
let ACCENT = '#ff6b1a';          // fallback only; CSS is the source of truth
function applyTheme(){
  const cs = getComputedStyle(document.documentElement);
  ACCENT = cs.getPropertyValue('--accent').trim() || ACCENT;
}
function applyThemeAndRedraw(){ applyTheme(); renderAt(lastT); }
window.__applyTheme = applyThemeAndRedraw;
```

Read once at boot, never per frame — `getComputedStyle` is far too slow for a render
loop. And a conversion is provably non-destructive when you compare pixel counts
against numbers recorded before it: blueprint held at 357,128 orange @3.0 s and
387,826 @5.5 s across the refactor.

### 8.6 Verify a theme flip by counting pixels, not by reading the variable

A flip that reports the right value while rendering the old one is the failure mode
that matters. Count pixels of the old colour and the new: accent → green produced
**7,366 green px and 0 orange px**.

### 8.7 Derive per-item timings; don't hand-tune one per item

Twelve blocks with hand-tuned holds drift the moment any copy changes. Scale the
hold to line length (`~15 ms/char`, floored and capped) and there is nothing to
re-tune.

### 8.8 Expose the layout so the verifier doesn't re-derive the timing

If a checker recomputes block windows from the same constants in a second place, the
two formulas drift and the check silently tests nothing. Export it:

```js
window.__scenes = () => SCENES.map(s => ({ i, scene, cut, hold, start, holdFrom, holdTo }));
```

Plus `window.__seek(seconds)` and `window.__duration` for frame-exact capture, and a
`__theme()` reader. Hooks are what turn a render into something checkable.

### 8.9 Not every hex is a theme token

Converting a file's colours to CSS means deciding **which** colours are theme. Most
are; some are functional and must stay fixed.

`dotcut-demo.html`'s `rasterizeText()` paints black, then white, onto an offscreen
canvas and reads it back as a `0`/`1` mask. Those two colours exist purely to
guarantee maximum separation for the threshold. Theme them and the mask quietly
inverts or empties the moment ink and ground are similar — a render bug with no
error and no stack trace, sitting in a function nowhere near the palette code.

→ **Grep the hexes, then classify each one before replacing it.** Theme tokens go to
`:root`; functional literals (masks, threshold canvases, `getImageData` probes) stay
hardcoded, with a comment saying why — otherwise the next sweep "fixes" them.

→ A mixed file also needs a *different* reading strategy: dotcut's palettes were
per-preset arrays of pairs, not one flat palette, so they became `[data-preset=…]`
rules plus a `--palette-count` the JS reads. Assume one flat palette and you will
silently drop presets.

### 8.10 Text sized in grid cells but drawn in canvas pixels

Symptom: negative-space lettering never reads — glyphs are a faint sliver in a field
they should dominate.

`rasterizeText()` supersamples into a canvas of `cols*6 × rows*6` (`LETTER_SC = 6`),
then downsamples by majority vote. But the font was sized `size = rows * 1.05` —
grid **cells**, not canvas **pixels**. The canvas is 6× the cell count, so every
glyph came out 6× too small. The width fit then compounded it, flattening a
four-letter word into a one-cell-tall sliver.

Measured on a 45×28 grid: `"BONK"` carved a **6×1** box — 5 of 1260 cells, 3.6% of
grid height. After the fix: **41×10, 217 cells**.

- → **A scale factor in a coordinate system you're not drawing in is invisible to
  code review.** `rows * 1.05` reads as reasonable; it's only wrong because of a
  constant defined elsewhere.
- → **Never hardcode a cap-height ratio** (0.72em etc.) when `measureText()` exists.
  Set a size, measure `actualBoundingBoxAscent + actualBoundingBoxDescent`, scale:

  ```js
  let size = Math.floor(H);            // canvas px, not cells
  setFont(size);
  const mm = ctx.measureText("H");
  const inkH = mm.actualBoundingBoxAscent + mm.actualBoundingBoxDescent;
  size = Math.floor(size * (H * 0.92) / inkH);
  ```

### 8.11 One letter at a time never spells a word

Second defect in the same render: it drew `LETTERS[letterIdx % LETTERS.length]` — a
**single** character per scene, cycling B → O → N → K. The word was never on screen,
so no amount of sizing or spacing could make the grid spell it.

→ If a render is meant to spell something, assert the **whole string** reaches the
rasteriser. Cycling a letter list and joining one look nearly identical; the
variable name `currentLetter` was fine in both. `const word = LETTERS.join("")`.

### 8.12 Real tracking needs per-glyph drawing

`fillText(text, …)` gives no inter-letter control, and canvas ignores CSS
`letter-spacing`. Measure and place each glyph yourself:

```js
const ws  = glyphs.map(g => ctx.measureText(g).width);
const gap = size * TRACKING;                    // em fraction, so it scales
const total = ws.reduce((a,b)=>a+b,0) + gap * (glyphs.length - 1);
let px = W/2 - total/2;
glyphs.forEach((g,i)=>{ ctx.fillText(g, px + ws[i]/2, y); px += ws[i] + gap; });
```

Two traps: the width fit **must include `gap`** or the last letter runs off the
canvas; and with `textAlign="center"` the x you pass is the glyph's **centre**, so
advance from the centre or the whole line drifts by half a letter.

→ **Verification: print the mask as ASCII** (`#` = carved, `.` = solid) and read it.
On a 45×28 grid that's a legible 45-character block — it catches "reads as a word"
and "letters are separated" in one glance, with no vision model and no pixel
statistic that can be subtly wrong.

### 8.13 Tuning the easing of a transition that has no delta

You "make it smoother", measure, and the number does not move at all.

dotcut's default preset draws in `dominant` mode, where the scene pattern is not
allowed to carve outside the letterform — so **every scene produces an identical
mask**. `applyScene()` does `from.set(live); target=next`, so `from` and `target` hold
the same values, `changing = from[i] !== target[i]` is false for every cell, `prog`
stays 0, and the morph loop rewrites what was already there.

Measured across 189 consecutive rAF frames: changed cells min **0**, max **0**. There
is nothing to interpolate. Swapping `easeOut` → `smootherstep` and widening the window
moved the visible per-frame delta from 0.462 to 0.466 — i.e. nowhere.

→ **Before tuning a transition's curve, assert the transition moves data.** Log
`Σ|target − from|` over a full cycle. A curve change on a zero-delta transition is a
no-op, and it will happily pass any "did it break anything?" test.

### 8.14 A full-frame colour ramp dominates perceived smoothness

With nothing morphing, what reads as "the cut" is the palette swap — and every scene
had its own palette, so one full-frame colour change every ~1.5s *was* the animation.

That ramp was a fixed 0.45s (`paletteMix += dt*2.2`) with `easeInOut` on top, showing
up as ~6 luma per frame against a total range of only 42.

→ Ramp it over a multiple of the preset's own morph time (1.6 × `MORPH_MS`) rather
than a fixed constant, so fast presets still finish before the next advance:

| | 0.45 s | 1.0 s |
|---|---|---|
| p99 step | 6.09 | **3.13** |
| max step | 8.78 | **3.89** |
| worst frame, % of range | 21 % | **9 %** |
| frames > 5 luma | 4 | **0** |

→ Look at the **full-frame** terms first. Per-cell effects were never where this
smoothness lived.

### 8.15 Measure animation smoothness in-page, not with screenshots

Screenshots **block the page**. Sampling every 40 ms gave ~200 ms between real frames,
inflating every delta and making a one-frame max look like a sustained defect.

Downscale the live canvas to ~64×40 *inside* the page on each rAF frame and record the
mean luminance:

```js
const sc=document.createElement('canvas'); sc.width=64; sc.height=40;
const sctx=sc.getContext('2d',{willReadFrequently:true});
const rec=()=>{
  sctx.drawImage(canvas,0,0,64,40);
  const d=sctx.getImageData(0,0,64,40).data;
  let s=0; for(let i=0;i<d.length;i+=4) s+=0.299*d[i]+0.587*d[i+1]+0.114*d[i+2];
  window.__lum.push(s/2560);
  if(window.__lum.length<240) requestAnimationFrame(rec);
};
requestAnimationFrame(rec);
```

Reading `live`/`bore` directly is cheaper but only describes the variables; the canvas
readout says what is actually on screen.

→ **A p50 near zero with occasional large steps means "still, then pop"** — that is
what "not smooth" looks like numerically, and a mean hides it completely. Report the
distribution, not the average.

### 8.16 Flip every token, or the theme test lies

Testing a theme hook by flipping one variable reported `motion-system-v2` as
**broken**: after `--accent` → `#00ff85` the frame still held **1,820 orange px**.

The render was fine. `--accent-soft` is `#ffb37a` — hue **26°**, inside the orange
family — and was still holding its old value because the test never touched it.

→ **Enumerate the tokens the file reads and set all of them**, then assert the old
colour goes to **0 px**, not just that the new one appears. A partial flip is a
partial test, and it fails in the direction that wastes your afternoon.

→ Corollary for the render itself: two tokens in the same hue family are
indistinguishable to a hue-family audit. If you need them to differ, give them
different hues or audit by exact colour.

### 8.17 A page that imports `.ts` is dead on a static server

`python3 -m http.server` maps `.ts` to **MPEG transport stream**, so every
`import './src/x.ts'` fails with a MIME-type error. Four harness pages
(`index.html`, `demo.html`, `dotcut-A.html`, `blurreveal.html`) have been sitting
in this folder unrenderable for that reason.

→ The trap is what they look like: `blurreveal.html` renders **pure white**
(100% ink, luma 255) and passes any "has content" check; `dotcut-A.html` renders
pure black and fails it. Two different-looking failures, one cause.

→ **Listen for `pageerror`/console errors, not just pixels.** A page can look
plausible and be throwing on every load — `logo-lockup-compare.html` did exactly
that (`Cannot read properties of undefined (reading '0')`) while still painting
1.178% ink.

### 8.18 A font stack takes the FIRST available family — so a "fallback" you mean to use is unreachable

`motion-assets/glow.html` declares `const fam = '"Bonk","Bonk Display",system-ui'`.
Both families resolve, so `'Bonk'` always wins and **`'Bonk Display'` can never be
reached**. The same stack appears in four sibling pieces, and
`instagram/carousel.html` lists no display cut at all (`"Bonk",system-ui`).
Measured: every one of those stacks resolves to the **text cut** (781.8 at
300px), not the display cut (655.5).

→ **Order is the whole mechanism.** A stack is a preference list, not a set. If
you write a fallback you actually want, you have written a no-op.

→ Corollary: this is invisible. The page renders, the glyphs are the right
*design family*, and only the metrics are wrong — so it reads as "the spacing
looks off" rather than "the font didn't load".

### 8.19 The logotype is set in the display cut — its tracking is calibrated there

`logo-spec.md` states the lockup's **−2.8% tracking against `BonkDisplay-Bold`'s
default metrics**. Setting the lockup in the text face applies that correction to
the wrong numbers. Measured at 300px:

| face | ink | per-glyph gaps |
|---|---|---|
| `'Bonk'` (text) | 736 | **13, 19, 24** |
| `'Bonk Display'` | 615 | **9, 4, 3** |

→ The text face is **19.7% wider with visibly uneven gaps**. At the spec's own
numbers the word runs 2.45em, so the mark placed at 2.0892em lands **inside the
word**. In the display cut the word is 2.057em and the mark starts at 2.087em —
a hair past the end, the way a real logotype sets.

→ So: **the wordmark and the running text are different cuts, and a piece needs
both.** `--font` for labels, a separate face for the brand.

### 8.20 Scale-invariant ratios pass in any face, which is not a test

`verify_lockup.py` measured `markDrop` and `markGap` in **em** and compared them
to the spec's em values. Both are normalised by the font size and the values are
em-based, so the check **passes identically in every face** — including the wrong
one. It reported PASS while all four brand pieces were set in the text face.

→ **A check that cannot fail is not a check.** Ask of every assertion: what would
this look like if the thing were broken? If nothing changes, delete it or replace
it with a measurement that moves — here, the word's absolute width in em, and
whether the mark clears the word at all.

### 8.21 If the test passes the value itself, it is testing its own constant

The same verify called `BonkMotion.lockup(ctx, { ..., family: FAMILY })` with
`FAMILY = "Bonk Display"` defined **at the top of the test file**. It was
measuring its own hardcoded string, not the runtime's default — so the runtime's
default could be anything and the test would still pass.

→ **Exercise the default, not a restatement of it.** Omit the argument and let
the code under test choose. The comment at that call site now says so, because
the temptation to "make it explicit" is exactly the bug.

### 8.22 A ruler that cannot separate the target from the default

Hunting 8.18, a probe read `getComputedStyle(document.body).fontFamily` to find
each page's stack. Bodies that declare no `font-family` return **`Times`** — and
Times measures **650.5** for `'bonk'` at 300px, while the display cut measures
**655.5**. Five units apart. Every row was reported as "display cut".

→ **Two failures at once:** the probe read a *computed* value that was never set
(so it measured the default), and then its verdict thresholds could not tell that
default from the answer. Both produced confident output.

→ **Sanity-check a probe by running it on a case whose answer you already know.**
Had it been pointed at `'Bonk'` alone — a stack that obviously resolves to the
text cut — it would have said "display cut" and the defect would have been
apparent immediately.

→ Always print the reference values alongside the verdicts, as the fixed version
does. A verdict without its calibration is an opinion.

### 8.23 A bounding box is not a mass

`07-push-in` centres the logotype inside a ring. Measured, the box was centred to
**0.5px** — and the composition still read off-centre, because the box runs from
the word's top to the **mark's bottom-right corner**, and that corner is mostly
empty. Centring the box centres nothing.

```
                       box centre        ink centroid
  offset from ring     (639.0, 358.0)    (622.2, 350.0)
  error                —                 (-17.3, -9.5)
```

Worse, the mark widens the box on the **right**, so centring the box pushes the
**word left by 7px** — the mass the eye actually reads gets dragged off-axis by an
element that has almost no ink in it.

→ **Centre on the mass when a composition has an axis.** A lockup standing alone
can centre its box; a lockup inside a ring, a frame or a baseline must centre the
**word** and let the mark hang. That is a dial, not a constant —
`--brandCentre: 'word' | 'box'`.

→ **When geometry says "centred" and the eye disagrees, measure the centroid.**
Both numbers are true; only one of them is what anyone sees.

### 8.24 Measure text in the state you will draw it

`drawBrand` measured the word to work out where to place it — but it measured
**before** `drawLockup` set `letterSpacing`. `ctx.measureText` honours the
letterSpacing in force at the moment of the call, so it returned the **untracked**
width: ~12px wider at this size. The word landed half that far off-centre, and the
symptom looked like a placement bug rather than a measurement bug.

→ **Set the drawing state first, measure second, restore after.** Anything that
changes metrics — `letterSpacing`, `font`, `fontStretch`, `textRendering` — must be
applied before the measurement that depends on it.

### 8.25 `measureText().width` is the advance, not the ink

For `'bonk'` in the display cut at 300px the **advance** is 650.5 and the **ink** is
615. The difference is the side bearings: invisible, and enough to shift anything
centred on it.

```
  ink-left  = pen - actualBoundingBoxLeft     (left is negative for this face)
  ink-right = pen + actualBoundingBoxRight
  ink width = right + left
```

→ **Use the bounding-box fields for anything positional.** `.width` answers "how
far does the pen advance" — the right answer for laying out a run of text, the
wrong one for centring a single word.

### 8.26 An extracted palette is a photograph of the system, not the system

Five hexes arrived from a colour extractor as a proposed brand palette. Two were
exact tokens. One was white off by 1/255. One — `#E96218` — turned out to be the
brand orange **exactly**, at alpha **0.9141** over black (delta `0.1, -0.19, -0.23`,
identical **21.2°** hue). Only `#190E07` was genuinely foreign.

→ **Never adopt an extracted palette wholesale.** An extractor samples rendered
pixels, so it reports the system as *photographed*: dimmed, composited, and
codec-shifted. Check each value against the spec, and for any that is absent, test
whether it is a token composited at some alpha **before** inventing a name for it.

→ **A hex absent from the codebase is not evidence of a new colour.** A `grep`
over the repo plus `design.md` settles it in seconds.

→ **The gap is the useful finding.** `design.md` defines a lighter orange
(`#ffb37a`) but **no darker one**, so the "new" colour filled a real hole rather
than duplicating a token.



