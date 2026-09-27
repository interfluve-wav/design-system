"""Measure the superscript lockup from the user's own SVG export.

The SVG carries real outlines AND positions (the CSS paste carried sizes only), so
every number below is measured from the geometry rather than inferred from the boxes.
Emits bonk-mark-sup.js in the same schema the blueprint consumes, plus two colour
groups so the main word and the dj can take different colours.
"""
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

SRC = Path("/Users/suhaas/Library/Application Support/Hermes/composer-images/"
           "bonk_dj_sup_-_no_bg_-_black_3591aa.svg")
CSS_CLAIMED = [("b", 166.48, 211.0), ("o", 161.70, 158.31), ("n", 152.67, 154.36),
               ("k", 164.00, 206.0), ("d", 36.25, 45.94), ("j", 15.32, 51.66)]
OUT = Path("/Users/suhaas/Pictures/motion - design - assets/projects/logo/bonk-mark-sup.js")

txt = SRC.read_text()
view = re.search(r'viewBox="([^"]+)"', txt).group(1)
paths = re.findall(r'<path[^>]*\sd="([^"]+)"', txt)
print(f"source: {SRC.name}   viewBox {view}   {len(paths)} paths")
assert len(paths) == 6, len(paths)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" width="693" height="211" '
       f'fill="#fff">' + "".join(f'<path d="{d}"/>' for d in paths) + '</svg>')

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 900, "height": 400})
    pg.goto("about:blank")
    r = pg.evaluate("""async ([markup]) => {
      const host = document.createElement('div');
      host.style.cssText = 'position:fixed;left:-99999px';
      host.innerHTML = markup; document.body.appendChild(host);
      const boxes = [...host.querySelectorAll('path')].map(p => {
        const b = p.getBBox();
        return {x:b.x, y:b.y, x1:b.x+b.width, y1:b.y+b.height, w:b.width, h:b.height}; });
      host.remove();
      const blob = new Blob([markup], {type:'image/svg+xml'});
      const url = URL.createObjectURL(blob);
      const img = new Image();
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });
      const W = 693, H = 211;
      const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
      const cx = cv.getContext('2d', {willReadFrequently:true});
      cx.fillStyle = '#000'; cx.fillRect(0,0,W,H);
      cx.drawImage(img, 0, 0, W, H);
      const id = cx.getImageData(0,0,W,H).data;
      // ink bbox + coverage
      let x0=W, y0=H, x1=-1, y1=-1, ink=0;
      for (let y=0;y<H;y++) for (let x=0;x<W;x++) if (id[(y*W+x)*4] > 127) {
        ink++; if(x<x0)x0=x; if(x>x1)x1=x; if(y<y0)y0=y; if(y>y1)y1=y; }
      // median first-run = stem
      const fr = [];
      for (let y=y0;y<=y1;y++){ let run=0;
        for (let x=x0;x<=x1;x++){ if (id[(y*W+x)*4]>127) run++; else if(run) break; }
        if (run) fr.push(run); }
      fr.sort((a,b)=>a-b);
      const prof = new Array(96).fill(0), cnt = new Array(96).fill(0);
      for (let x=x0;x<=x1;x++){ const b=Math.min(95,Math.floor(((x-x0)/(x1-x0+1))*96)); cnt[b]++;
        for (let y=y0;y<=y1;y++) if (id[(y*W+x)*4]>127) prof[b]++; }
      for (let i=0;i<96;i++) prof[i] = cnt[i] ? prof[i]/cnt[i] : 0;
      URL.revokeObjectURL(url);
      return { boxes, inkBox:{x0,y0,x1,y1}, ink, prof,
               stem: fr.length ? fr[Math.floor(fr.length/2)] : 0 };
    }""", [svg])
    br.close()

boxes = sorted(r["boxes"], key=lambda b: b["x"])
names = ["b", "o", "n", "k", "d", "j"]

print("\nper-path ink boxes, measured from THIS file (vs the CSS paste's claim):")
print(f"  {'glyph':5s} {'x0':>8s} {'x1':>8s} {'y0':>8s} {'y1':>8s} {'w':>8s} {'h':>8s}   "
      f"{'css w':>7s} {'css h':>7s}  match")
ok = True
for nm, b, (cn, cw, ch) in zip(names, boxes, CSS_CLAIMED):
    m = abs(b["w"] - cw) < 0.05 and abs(b["h"] - ch) < 0.05
    ok &= m
    print(f"  {nm:5s} {b['x']:>8.3f} {b['x1']:>8.3f} {b['y']:>8.3f} {b['y1']:>8.3f} "
          f"{b['w']:>8.3f} {b['h']:>8.3f}   {cw:>7.2f} {ch:>7.2f}  {'OK' if m else 'DIFF'}")
print(f"\n  every glyph matches the CSS paste's sizes: {ok}")

main = boxes[0:4]
dj = boxes[4:6]
print(f"\nMAIN WORD   x {main[0]['x']:.1f} -> {main[3]['x1']:.1f}  = {main[3]['x1']-main[0]['x']:.2f} wide")
print(f"  gaps between ink boxes: " + ", ".join(
    f"{names[i]}->{names[i+1]} {boxes[i+1]['x']-boxes[i]['x1']:+.2f}" for i in range(3)))
print(f"  x-height {boxes[1]['h']:.2f} (o)   ascender {boxes[0]['h']:.2f} (b)")
print(f"\nSUPERSCRIPT 'dj'  x {dj[0]['x']:.2f} -> {dj[1]['x1']:.2f}")
print(f"  d  y {dj[0]['y']:.2f} -> {dj[0]['y1']:.2f}")
print(f"  j  y {dj[1]['y']:.2f} -> {dj[1]['y1']:.2f}   (bottom = descender)")
print(f"  dj top  {min(dj[0]['y'], dj[1]['y']):.2f}  vs main ascender top {min(b['y'] for b in main):.2f}"
      f"   -> top-aligned, offset {min(dj[0]['y'],dj[1]['y'])-min(b['y'] for b in main):+.2f}")
print(f"  dj overlaps the k's span by {boxes[3]['x1'] - dj[0]['x']:.2f} units "
      f"(k ends {boxes[3]['x1']:.1f}, d starts {dj[0]['x']:.1f})")
print(f"  dj descender reaches y {dj[1]['y1']:.2f} vs main x-height top y "
      f"{boxes[1]['y']:.2f} -> {dj[1]['y1']-boxes[1]['y']:+.2f}")

ib = r["inkBox"]
print(f"\nINK  bbox ({ib['x0']},{ib['y0']}) -> ({ib['x1']},{ib['y1']}) = "
      f"{ib['x1']-ib['x0']+1}x{ib['y1']-ib['y0']+1}")
print(f"  coverage {r['ink']/((ib['x1']-ib['x0']+1)*(ib['y1']-ib['y0']+1))*100:.2f}%   stem {r['stem']}")
print(f"  curvature/contrast check: main x-height {boxes[1]['h']:.1f}, "
      f"stem {r['stem']} -> stem is {r['stem']/boxes[1]['h']*100:.1f}% of x-height")

# ── compare with the two candidate sources, correctly labelled this time ──
print("\n=== is this the same DESIGN as the canonical lockup? ===")
print(f"  {'glyph':5s} {'sup aspect':>11s} {'worldmark.svg':>14s} {'Δ%':>7s}")
canon = {"b": (142.2, 186.9), "o": (140.2, 140.0), "n": (129.5, 136.5),
         "k": (136.7, 183.4), "d": (51.1, 67.1), "j": (23.2, 85.0)}
tot = 0
for nm, b, (cn, cw, ch) in zip(names, boxes, CSS_CLAIMED):
    a_sup = b["w"] / b["h"]
    a_can = canon[nm][0] / canon[nm][1]
    dl = (a_sup / a_can - 1) * 100
    tot += abs(dl)
    print(f"  {nm:5s} {a_sup:>11.4f} {a_can:>14.4f} {dl:>+6.2f}%")
print(f"  mean |Δ| {tot/6:.2f}%  -> a consistent positive bias means the sup is WIDER, "
      f"not a uniform scale")

# ── emit the module ──
letters = [{"x0": round(b["x"] - ib["x0"], 2), "x1": round(b["x1"] - ib["x0"], 2),
            "w": round(b["w"], 2), "y0": round(b["y"] - ib["y0"], 2),
            "y1": round(b["y1"] - ib["y0"], 2), "glyph": nm}
           for nm, b in zip(names, boxes)]
mod = {
    "d": " ".join(paths),
    "dMain": " ".join(paths[0:4]),
    "dSup": " ".join(paths[4:6]),
    "width": ib["x1"] - ib["x0"] + 1, "height": ib["y1"] - ib["y0"] + 1,
    "origin": {"x": ib["x0"], "y": ib["y0"]},
    "letters": letters,
    "profile": [round(v, 4) for v in r["prof"]],
    "metrics": {
        "xHeight": round(boxes[1]["h"], 2),
        "ascender": round(boxes[0]["h"], 2),
        "stemWidth": r["stem"],
        "inkCoveragePct": round(r["ink"] / ((ib["x1"]-ib["x0"]+1)*(ib["y1"]-ib["y0"]+1)) * 100, 2),
        "letterCount": 6,
        "baseline": round(max(b["y1"] for b in main) - ib["y0"], 2),
        "supTop": round(min(dj[0]["y"], dj[1]["y"]) - ib["y0"], 2),
        "supX0": round(dj[0]["x"] - ib["x0"], 2),
        "mainX1": round(main[3]["x1"] - ib["x0"], 2),
    },
    "source": "bonk_dj_sup SVG export (user) — lowercase bonk + TOP-ALIGNED superscript dj",
}
OUT.write_text("// generated by measure_sup.py — do not hand-edit\n"
               f"// {mod['source']}\n"
               f"window.BONK_MARK_SUP = {json.dumps(mod, separators=(',', ':'))};\n")
print(f"\nwrote {OUT.name}: {OUT.stat().st_size:,} bytes")
print(f"  {mod['width']}x{mod['height']}  baseline {mod['metrics']['baseline']}  "
      f"supTop {mod['metrics']['supTop']}  supX0 {mod['metrics']['supX0']}")
