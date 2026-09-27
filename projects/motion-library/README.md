# The motion model contract

**Read this before touching any piece in `projects/`.** It is the difference between
a folder of one-off renders and a library you can retune without re-reading the code.

A **piece** is one self-contained HTML file that renders one motion idea, in the brand
tokens, with no build step. A **model** is that piece's declared parameter surface —
the copy, the colours, the type size, the frame, the timing — exposed so that a human,
a URL, or `scripts/render.py` can change any of it without opening the file's internals.

---

## 1. Why this exists

Before the kit, every piece was bespoke. Changing the words meant editing a scene
array; changing the type size meant hunting a hand-tuned fraction; each piece invented
its own URL params (`?ground=light` here, `?scene=N` there, `?words=` somewhere else);
and the capture scripts lived in `/tmp` and were lost, so a delivered GIF could not be
reproduced. The single most-reusable asset in the folder had no version control.

Four rules, each one paid for by an actual failure (see `docs/GOTCHAS.md`):

| Rule | Why |
|---|---|
| Colour lives in CSS custom properties, **never** hardcoded in JS | a rasterised canvas reads them at build time; a hardcoded hex makes every variant a code edit (§8.4) |
| Copy lives in the model's `text` block, **never** inline in a draw call | one string change should not require finding the draw call |
| Type is placed by `MotionType`, never by hand | hand-rolled glyph metrics produced a 6×-too-small word and a line drifting by half a letter (§8.10, §8.12) |
| Every mutation path ends in a **repaint**, not just a re-read | a hook that re-reads without repainting reports the new colour and renders the old one (§8.5) |

---

## 2. The block

At the top of the piece's `<script>`, before anything else:

```js
const MODEL = MotionModel.define({
  id:      'glow',                              // unique, kebab-case, used by the CLI
  title:   'bonk — glow',
  family:  'motion-assets',                     // the folder it lives in
  purpose: 'the logo as a window — a soft light drifts through the mark',

  frame:    {w: 1920, h: 1080},                 // the aspect it is COMPOSED for
  duration: 10,                                 // seconds
  fps:      30,

  colours: ['--ground','--mark','--light','--label','--label-dim','--accent'],

  text: {                                       // EVERY user-visible string
    label:  'bonk',
    sub:    'music library',
    kicker: 'in order',
  },

  type:  { size: 0.0175, scale: 1, tracking: 0.10 },

  dials: { markW: 0.735, markDim: 0.115, lightPeak: 0.98 },
  dialDocs: { markW: 'mark width as a fraction of the frame width' },

  fonts: ["700 40px 'Bonk'", "italic 400 40px 'Bonk'"],

  notes: 'free prose — the design rationale, kept with the numbers',
});
```

Then wire it up, and nothing else:

```js
MODEL.onApply(() => readTheme());   // re-read the theme; the kit repaints after
MODEL.renderAt(t => draw(t));       // the kit owns __seek / __duration / __ready
```

Name the binding **`MODEL`**, never `M`. Several pieces already use `M` for the brand
*mark* (`const {M, s, gw} = markGeo()`), so an `M` for the model is shadowed inside
`draw()` and silently reads as the mark.

### Rules for the block

- **`colours` is the complete surface.** A theme audit flips every name in this list
  (§8.16). If a colour affects the render and is not listed, the audit is lying.
- **Nothing chromatic outside `:root`.** Functional literals are the exception and must
  carry a comment saying why — `dotcut` paints black/white onto an offscreen canvas and
  reads it back as a 0/1 mask; theming those two colours inverts the mask (§8.9).
- **Nothing copy-shaped outside `text`.** No string literal in a draw call. If a piece
  draws a caption, a tile, a scene line or a label, it belongs in `text`.
- **Numbers that a human would tune go in `dials`.** Fractions of the frame, alphas,
  radii — with a `dialDocs` line each.
- **Colours are read from CSS, not copied into JS.** Keep the piece's own `:root`; the
  kit writes resolved values as inline styles on `<html>`, which win over it.

---

## 3. Overriding it

Everything, from outside, with no code edit:

| | |
|---|---|
| copy | `?label=bonk&sub=library&kicker=in%20order` |
| colour | `?--mark=%2300ff85` — or `?mark=%2300ff85` when no copy key owns `mark` |
| type | `?size=0.02&scale=1.4&tracking=0.14` |
| frame | `?w=1080&h=1080` |
| timing | `?dur=6&fps=30` |
| dials | `?markW=0.85&markDim=0.2` |
| register | `?ground=light` |
| capture | `?chrome=0` (hides `.mf-chrome`), `?loop=0` (no rAF loop) |

**The one naming rule.** A colour token and a copy key can want the same short name —
`label` is both a very common CSS token and a very common thing to write on screen. So:

```
--mark    the colour token, ALWAYS addressable with its dashes
mark      the same token as a shorthand, but only while no copy key claims it
label     the copy key, when a piece has one
```

Copy wins the bare name; the colour keeps its dashes. Deterministic, and `?mark=`
still works for every piece without a clash.

Programmatically, on the page:

```js
__set({label:'interfluve', '--mark':'#00ff85', scale:1.4});   // apply + repaint
__theme();     // every colour token, current — never stale (§8.5)
__params();    // [{name, group, type, default, value, doc}] — the dials
__model;       // the resolved model, plus which keys were overridden
__warnings;    // everything that looked wrong, in writing
```

---

## 4. What you get for free, and why you should not re-implement it

| Hook | Guarantee |
|---|---|
| `__seek(sec)` | **seconds**, always (§2.5). Cancels the rAF loop first (§2.4) |
| `__duration` | seconds. The same unit as `__seek` |
| `__frame` | `{w, h, fps}` |
| `__ready` | a Promise — resolved once fonts are loaded *and* frame 0 is painted |
| `__rebuild()` | re-reads config **and repaints**; identical to `__applyTheme()` |
| `__scenes()` | the resolved block layout, so a verifier reads the real timings instead of re-deriving the formula in a second place (§8.8) |
| `__stopLoop` | define it if you run a rAF loop, so `__seek` can freeze you |

Fonts are the trap worth repeating: a `ctx.font` reference does **not** trigger an
`@font-face` download, so a canvas-only piece renders in the fallback font and looks
fine (§3.10). List the faces in `fonts:` and the kit waits for them.

---

## 5. Tooling

```bash
cd "/Users/suhaas/Pictures/motion - design - assets"
bash scripts/serve.sh                      # http://127.0.0.1:8765 — everything needs it

python3 scripts/scan_models.py             # boot every piece, read its model, refresh registry.json
python3 scripts/scan_models.py --diff      # + pixel-diff against _archive/pre-models/ (proves a retrofit changed nothing)
python3 scripts/scan_models.py --only glow

python3 scripts/render.py glow             # GIF at the model's own frame/fps/duration
python3 scripts/render.py glow --text "label=interfluve" --mark '#00ff85' --w 1080 --h 1080
python3 scripts/render.py --list           # every model and its dials

python3 scripts/build_kb.py                # regenerate the Obsidian knowledge base from registry.json
```

`registry.json` is **measured, not parsed** — `scan_models.py` boots each piece in
headless Chromium and reads what it actually exposes. A doc generated from it cannot
drift from the code, which is the whole point.

---

## 6. Converting a piece (the checklist)

1. Snapshot is already taken: `_archive/pre-models/` holds every file as it was before
   any retrofit. Do not edit inside it.
2. Add the kit, **tokens.css before the piece's own `<style>`** so the piece's values
   remain the defaults:
   ```html
   <link rel="stylesheet" href="../motion-library/kit/tokens.css">
   ...
   <script src="../motion-library/kit/model.js"></script>
   <script src="../motion-library/kit/type.js"></script>
   ```
3. Hoist every string into `text`, every chromatic token into `colours`, every tunable
   number into `dials`. Declare `frame`, `duration`, `fps`, `fonts`.
4. Replace hand-rolled type with `MotionType.fit` / `MotionType.draw`.
5. Delete the piece's own `__seek` / `__duration` / `__ready` — the kit owns them.
6. Wire `MODEL.onApply(...)` and `MODEL.renderAt(...)`.
7. Verify — do not assume:
   ```bash
   python3 scripts/scan_models.py --only <id> --diff
   ```
   Expect **0 page errors**, **0 warnings**, and a pixel diff confined to the type you
   deliberately changed. A diff over the whole frame is a bug, not a rounding error.
8. Add the piece to `projects/motion-library/pieces.json`'s family list if it is new.
