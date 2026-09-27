#!/usr/bin/env python3
"""build_gallery.py — scan the motion families and emit a library index.

Extracts each piece's REAL parameters out of its source (`:root` custom
properties + the header comment) instead of describing them by hand, so the
gallery cannot drift from the code. Re-run after editing any piece.

    python3 build_gallery.py            # writes index.html + prints a summary
    python3 build_gallery.py --check    # exits 1 if any piece is unparameterised
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent           # .../projects
OUT = Path(__file__).resolve().parent                   # .../projects/motion-library
DELIVER = Path("/Users/suhaas/Pictures/design - tiles - motion")

# family -> what it is, in plain language
FAMILIES = {
    "dotcut":        ("Circle grid that cycles B O N K",
                      "Letters built from a grid of dots; each letter morphs into the next."),
    "blueprint":     ("Logo drawn as a technical drawing",
                      "The mark is constructed on screen — dimensions, guides, then it resolves."),
    "blurreveal":    ("Scenes revealed through blur",
                      "Depth-of-field sweep; the frame resolves from soft to sharp."),
    "motion-system": ("The component sheet",
                      "A grid of the individual motion primitives, shown together."),
    "motion-assets": ("Single-idea studies",
                      "One motion idea per file: light, ripple, edge-on type, curves, timeline."),
}

CONFIG_RE = re.compile(r"const\s+(?:CFG|CONFIG|PARAMS|OPTS)\s*=\s*\{(.*?)\n\s*\};", re.S)
ROOT_RE = re.compile(r":root\s*\{(.*?)\}", re.S)
HEADER_RE = re.compile(r"^\s*/\*\s*[─\-]+\s*(.*?)\s*[─\-]+", re.S | re.M)
VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);(?:\s*/\*\s*(.*?)\s*\*/)?")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)

# stubs and one-off conversion utilities — not library pieces
EXCLUDE = {"bonk-intro-preview.html", "bonk-wordmark.html", "bonk-logo.html"}

PURPOSE = {
    "glow": "the logo as a window — a soft light drifts *through* the mark",
    "ripple": "a disc grows; satellites multiply outward from its edge",
    "typeon": "edge-on type wipes flat, then resolves to the mark",
    "curves": "tangent curves sweep and hand off to one another",
    "curves-v2": "tangent curves, second pass",
    "timeline": "a scrubber runs the frame; the mark rides the playhead",
    "dotcut-demo": "circle grid, B O N K cycle",
    "bonk-wordmark": "wordmark extraction utility",
    "bonk-logo": "logo conversion utility",
}

# what each var is FOR, so a stranger can retune it
VAR_ROLE = [
    (re.compile(r"ground|bg", re.I), "background"),
    (re.compile(r"mark|ink", re.I), "the mark's colour"),
    (re.compile(r"accent", re.I), "accent colour"),
    (re.compile(r"label|text|type", re.I), "label / type colour"),
    (re.compile(r"light", re.I), "the moving light"),
    (re.compile(r"duration|dur", re.I), "seconds the piece runs"),
    (re.compile(r"W$|width", re.I), "size as a fraction of the frame"),
]


def role_of(name: str) -> str:
    for rx, role in VAR_ROLE:
        if rx.search(name):
            return role
    return "tuning value"


def parse_piece(path: Path) -> dict:
    src = path.read_text(errors="replace")
    tm = TITLE_RE.search(src)
    title = tm.group(1).strip() if tm else path.stem

    # description = the first big comment block after <script> if present,
    # else the <style> header comment
    desc = ""
    m = HEADER_RE.search(src)
    if m:
        desc = " ".join(m.group(1).split())[:200]

    # custom properties, deduped, :root block first
    vr = ROOT_RE.search(src)
    vars_ = []
    seen = set()
    if vr:
        for name, val, note in VAR_RE.findall(vr.group(1)):
            if name in seen or name.startswith("--app-"):
                continue
            seen.add(name)
            vars_.append({"name": name, "value": val.strip(),
                          "note": (note or "").strip(), "role": role_of(name)})

    cfg = CONFIG_RE.search(src)
    has_cfg = bool(cfg)
    has_light = '[data-ground="light"]' in src
    seek = "window.__seek" in src
    ready = "__ready" in src
    font_shared = "bonk.css" in src
    mark_shared = "bonk-mark.js" in src

    return {
        "file": path.name,
        "rel": str(path.relative_to(PROJ)),
        "title": title,
        "desc": desc,
        "vars": vars_,
        "has_cfg": has_cfg,
        "has_light": has_light,
        "seek": seek,
        "ready": ready,
        "font_shared": font_shared,
        "mark_shared": mark_shared,
        "lines": src.count("\n") + 1,
        "bytes": len(src),
    }


def find_render(stem: str) -> str | None:
    """Best-effort match to a delivered render in the output folder."""
    if not DELIVER.is_dir():
        return None
    keys = [k for k in re.split(r"[-_]", stem) if len(k) > 2]
    cands = []
    for f in DELIVER.rglob("*"):
        if f.suffix.lower() not in (".gif", ".mp4", ".png") or not f.is_file():
            continue
        n = f.name.lower()
        score = sum(1 for k in keys if k in n)
        if score:
            cands.append((score, f.stat().st_size, f))
    if not cands:
        return None
    cands.sort(key=lambda t: (-t[0], -t[1]))
    return str(cands[0][2])


def render_gallery(pieces: list[dict]) -> int:
    """Emit index.html — every piece, live, with the dials it exposes."""
    SIZES = {"dotcut": "1080x1080", "blueprint": "1920x1080",
             "blurreveal": "1920x1080", "motion-system": "1920x1080",
             "motion-assets": "1920x1080"}

    rows = []
    for fam, (fam_title, fam_desc) in FAMILIES.items():
        group = [p for p in pieces if p["family"] == fam]
        if not group:
            continue
        cards = []
        for p in group:
            colours = [v for v in p["vars"] if v["role"] != "tuning value"]
            dials = [v for v in p["vars"] if v["role"] == "tuning value"]
            cvar = "".join(
                f'<div class="v"><code>{html.escape(v["name"])}</code>'
                f'<span class="val">{html.escape(v["value"])}</span>'
                f'<span class="role">{html.escape(v["note"] or v["role"])}</span></div>'
                for v in colours[:6]
            )
            dvar = "".join(
                f'<div class="v"><code>{html.escape(v["name"])}</code>'
                f'<span class="val">{html.escape(v["value"])}</span>'
                f'<span class="role">{html.escape(v["note"] or v["role"])}</span></div>'
                for v in dials[:5]
            )
            flags = " ".join(
                f'<span class="flag">{t}</span>' for t, on in (
                    ("seekable", p["seek"]), ("light register", p["has_light"]),
                    ("shared font", p["font_shared"]), ("shared mark", p["mark_shared"]),
                    ("config block", p["has_cfg"]),
                ) if on
            )
            cards.append(f"""
      <article class="card">
        <div class="shot" data-src="/{html.escape(p['rel'])}" data-size="{SIZES.get(fam,'1920x1080')}">
          <div class="ph">click to load the live piece</div>
        </div>
        <h3>{html.escape(p['title'])}</h3>
        <p class="why">{html.escape(p['purpose'] or p['desc'] or '—')}</p>
        <div class="meta">{flags}</div>
        <div class="grp"><h4>colour — change these</h4>{cvar or '<div class="v none">none exposed</div>'}</div>
        <div class="grp"><h4>dials</h4>{dvar or '<div class="v none">none exposed</div>'}</div>
        <div class="path">{html.escape(p['rel'])} · {p['lines']} lines</div>
      </article>""")
        rows.append(f"""
    <section>
      <header><h2>{html.escape(fam_title)}</h2>
        <p>{html.escape(fam_desc)} <span class="mono">{fam}/</span></p></header>
      <div class="grid">{''.join(cards)}</div>
    </section>""")

    total_dials = sum(1 for p in pieces for v in p["vars"] if v["role"] == "tuning value")
    total_col = sum(1 for p in pieces for v in p["vars"] if v["role"] != "tuning value")

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>bonk — motion library</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:var(--app-font,system-ui);color:var(--foreground);
       background:transparent;padding:4px 2px 40px;line-height:1.45}}
  .lede{{max-width:64ch;margin:0 0 34px}}
  .lede h1{{font-size:2.1rem;font-weight:600;letter-spacing:-.02em;margin-bottom:10px}}
  .lede p{{color:var(--muted-foreground);font-size:.95rem}}
  .lede b{{color:var(--foreground);font-weight:600}}
  .stat{{display:flex;gap:28px;margin-top:18px;flex-wrap:wrap}}
  .stat div{{font-size:.8rem;color:var(--muted-foreground)}}
  .stat strong{{display:block;font-size:1.5rem;color:var(--foreground);
                font-weight:600;letter-spacing:-.02em}}
  section{{margin:0 0 44px}}
  section>header{{margin-bottom:16px}}
  section>header h2{{font-size:1.15rem;font-weight:600;letter-spacing:-.01em}}
  section>header p{{color:var(--muted-foreground);font-size:.85rem;margin-top:2px}}
  .mono{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
         background:var(--accent);color:var(--foreground);
         padding:1px 5px;border-radius:3px;font-size:.78rem}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:26px}}
  .card{{display:flex;flex-direction:column;gap:9px}}
  .shot{{position:relative;aspect-ratio:16/10;background:var(--card);
         border-radius:6px;overflow:hidden;cursor:pointer}}
  .shot canvas,.shot iframe{{width:100%;height:100%;border:0;display:block}}
  .ph{{position:absolute;inset:0;display:grid;place-items:center;
       color:var(--muted-foreground);font-size:.75rem;letter-spacing:.02em}}
  .shot:hover .ph{{color:var(--foreground)}}
  .card h3{{font-size:.95rem;font-weight:600}}
  .why{{font-size:.82rem;color:var(--muted-foreground);min-height:2.4em}}
  .meta{{display:flex;flex-wrap:wrap;gap:5px}}
  .flag{{font-size:.66rem;letter-spacing:.03em;text-transform:lowercase;
         color:var(--muted-foreground);background:var(--accent);
         padding:2px 6px;border-radius:99px}}
  .grp h4{{font-size:.68rem;font-weight:600;letter-spacing:.06em;
           text-transform:uppercase;color:var(--muted-foreground);
           margin:6px 0 4px}}
  .v{{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;font-size:.74rem;
      padding:2px 0}}
  .v code{{font-family:ui-monospace,Menlo,monospace;color:var(--foreground)}}
  .v .val{{color:var(--muted-foreground);font-family:ui-monospace,Menlo,monospace}}
  .v .role{{grid-column:2;color:var(--muted-foreground);font-size:.68rem;opacity:.75}}
  .v.none{{color:var(--muted-foreground);font-style:italic}}
  .path{{font-family:ui-monospace,Menlo,monospace;font-size:.68rem;
         color:var(--muted-foreground);opacity:.7;margin-top:2px}}
</style></head><body>
<div class="lede">
  <h1>Motion library</h1>
  <p>{len(pieces)} pieces across {len(FAMILIES)} families. Everything here is
  <b>plain HTML, CSS custom properties and canvas</b> — no compiled output, no
  framework. Colours are variables, so you retune a piece by editing numbers at
  the top of the file or by overriding a property from outside.
  <b>Click any tile to run it live.</b></p>
  <div class="stat">
    <div><strong>{len(pieces)}</strong>pieces</div>
    <div><strong>{total_col}</strong>colour variables</div>
    <div><strong>{total_dials}</strong>tuning dials</div>
    <div><strong>{sum(1 for p in pieces if p['has_cfg'])}</strong>with a config block</div>
    <div><strong>{sum(1 for p in pieces if p['seek'])}</strong>frame-seekable</div>
  </div>
</div>
{''.join(rows)}
<script>
document.querySelectorAll('.shot').forEach(function(s){{
  s.addEventListener('click', function(){{
    if (s.dataset.done) return;
    var [w,h] = s.dataset.size.split('x').map(Number);
    var f = document.createElement('iframe');
    f.src = 'http://127.0.0.1:8765' + s.dataset.src;
    f.loading = 'lazy';
    f.style.transform = 'scale(' + (s.clientWidth/w) + ')';
    f.style.transformOrigin = '0 0';
    f.style.width = w + 'px'; f.style.height = h + 'px';
    s.querySelector('.ph').style.display = 'none';
    s.appendChild(f); s.dataset.done = '1';
  }});
}});
</script>
</body></html>"""
    (OUT / "index.html").write_text(doc)
    return len(pieces)


def main() -> int:
    pieces = []
    for fam, files in sorted(
        ((f, sorted((PROJ / f).glob("*.html"))) for f in FAMILIES)
    ):
        for p in files:
            if p.name in EXCLUDE:
                continue
            d = parse_piece(p)
            d["family"] = fam
            d["purpose"] = PURPOSE.get(p.stem, "")
            d["render"] = find_render(p.stem)
            pieces.append(d)

    bare = [p for p in pieces if not p["vars"] and not p["has_cfg"]]
    print(f"═══ scanned {len(pieces)} pieces across {len(FAMILIES)} families")
    print(f"  parameterised (css vars or config): {len(pieces) - len(bare)}")
    print(f"  colour-only (vars, no dials):       "
          f"{sum(1 for p in pieces if p['vars'] and not p['has_cfg'])}")
    print(f"  bare (nothing exposed):             {len(bare)}")
    for p in bare:
        print(f"      ! {p['rel']}")
    print(f"  with a light register:  {sum(1 for p in pieces if p['has_light'])}")
    print(f"  seekable (window.__seek): {sum(1 for p in pieces if p['seek'])}")
    print(f"  use the shared Bonk font: {sum(1 for p in pieces if p['font_shared'])}")
    print(f"  use the shared mark:      {sum(1 for p in pieces if p['mark_shared'])}")

    (OUT / "pieces.json").write_text(json.dumps(pieces, indent=2))
    n = render_gallery(pieces)
    print(f"  wrote index.html ({n} pieces) and pieces.json")

    if "--check" in sys.argv:
        return 1 if bare else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
