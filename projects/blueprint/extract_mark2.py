#!/usr/bin/env python3
"""
Build the v2 blueprint mark modules.

Two sources, both real geometry, no tracing:
  A. bonk-mark-v2.js    -- the canonical lowercase lockup from bonk-wordmark.svg
                           (b o n k full size + small d j), exact path data.
  B. bonk-mark-font.js  -- "bonk" outlined straight from Bonk-VF.ttf via fontTools.

Both emit the SAME schema the blueprint already consumes, so the renderer is
source-agnostic:
  { d, width, height, origin:{x,y}, letters:[{x0,x1,w}], profile:[...], metrics:{...} }

Run from the assets root.  Writes into projects/blueprint/public/.
"""
import json, re, sys
from pathlib import Path

ROOT = Path("/Users/suhaas/Pictures/motion - design - assets")
PUB  = ROOT / "projects/blueprint/public"
SVG  = ROOT / "projects/logo/bonk-wordmark.svg"
FONT = Path("/Users/suhaas/Design Assets/Bonk-VF.ttf")

PROFILE_BUCKETS = 96


# ───────────────────────────── A. canonical lockup ─────────────────────────────

def svg_paths():
    """Pull the 6 `d` attributes out of the shipped wordmark SVG, in document order."""
    txt = SVG.read_text()
    ds = re.findall(r'<path[^>]*\sd="([^"]+)"', txt)
    assert len(ds) == 6, f"expected 6 paths, got {len(ds)}"
    return ds


def measure_in_browser(paths):
    """
    Real measurement via the browser: per-path ink bboxes (getBBox is exact for
    beziers here), plus a high-res raster of the whole mark so the ink profile,
    stem width and coverage are measured rather than assumed.
    """
    from playwright.sync_api import sync_playwright
    import base64

    # fill MUST be explicit. Without it the paths render black, and a black-on-black
    # raster measures 0% ink with a negative bbox -- exactly how this first failed.
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2000 2000" '
           'width="2000" height="2000" fill="#fff">'
           + "".join(f'<path d="{d}"/>' for d in paths) + '</svg>')

    js = """async ([svgMarkup, buckets]) => {
      const blob = new Blob([svgMarkup], {type:'image/svg+xml'});
      const url  = URL.createObjectURL(blob);
      const img  = new Image();
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });

      // ---- per-path bboxes, measured from live DOM (exact bezier bounds)
      const host = document.createElement('div');
      host.style.cssText = 'position:fixed;left:-99999px';
      host.innerHTML = svgMarkup;
      document.body.appendChild(host);
      const boxes = [...host.querySelectorAll('path')].map(p => {
        const b = p.getBBox(); return {x:b.x, y:b.y, w:b.width, h:b.height};
      });
      host.remove();

      // ---- raster the whole mark to measure ink, profile and stem
      const R = 2000, cv = document.createElement('canvas');
      cv.width = R; cv.height = R;
      const cx = cv.getContext('2d', {willReadFrequently:true});
      cx.fillStyle = '#000'; cx.fillRect(0,0,R,R);
      cx.drawImage(img, 0, 0, R, R);
      const px = cx.getImageData(0,0,R,R).data;

      // union ink bbox from actual pixels (authoritative)
      let x0=R, y0=R, x1=-1, y1=-1, ink=0;
      for (let y=0;y<R;y++) for (let x=0;x<R;x++) {
        if (px[(y*R+x)*4] > 127) { ink++; if(x<x0)x0=x; if(x>x1)x1=x; if(y<y0)y0=y; if(y>y1)y1=y; }
      }
      const bw = x1-x0+1, bh = y1-y0+1;

      // column ink profile across the mark's box
      const prof = new Array(buckets).fill(0), counts = new Array(buckets).fill(0);
      for (let x=x0;x<=x1;x++){
        const b = Math.min(buckets-1, Math.floor(((x-x0)/bw)*buckets));
        counts[b]++;
        for (let y=y0;y<=y1;y++) if (px[(y*R+x)*4] > 127) prof[b]++;
      }
      for (let i=0;i<buckets;i++) prof[i] = counts[i] ? prof[i]/counts[i] : 0;

      // Stem width: the run that STARTS at the ink box's left edge, per row, then the
      // median. The leftmost glyph is b, whose left side is its stem, so the median
      // first-run over all inked rows is the stem thickness. A plain max-run across
      // the whole mark does NOT work -- where k's diagonal meets its stem the two
      // merge into a single long run (64.7 vs the true value on this very mark).
      const firstRuns = [];
      let maxRun = 0;
      for (let y=y0; y<=y1; y++){
        let run = 0;
        for (let x=x0; x<=x1; x++){
          if (px[(y*R+x)*4] > 127) { run++; if (run>maxRun) maxRun = run; }
          else if (run) break;
        }
        if (run) firstRuns.push(run);
      }
      firstRuns.sort((a,b)=>a-b);
      const stemRun = firstRuns.length ? firstRuns[Math.floor(firstRuns.length/2)] : 0;
      URL.revokeObjectURL(url);
      return { boxes, box:{x:x0,y:y0,w:bw,h:bh}, ink, inkPct: ink/(bw*bh)*100,
               profile: prof, stemRun, maxStemRun: maxRun,
               stemSamples: firstRuns.length };
    }"""

    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 1200, 'height': 1200})
        pg.goto("about:blank")
        out = pg.evaluate(js, [svg, PROFILE_BUCKETS])
        br.close()
    return out


def build_lockup_module():
    paths = svg_paths()
    m = measure_in_browser(paths)
    box = m["box"]

    # classify glyphs: full-size run vs the small dj pair
    full = sorted([b for b in m["boxes"] if b["w"] > 100], key=lambda b: b["x"])
    small = sorted([b for b in m["boxes"] if b["w"] <= 100], key=lambda b: b["x"])
    assert len(full) == 4 and len(small) == 2, (len(full), len(small))

    # x-height = height of the round x-height glyph (o); ascender = top of b
    baseline = max(b["y"] + b["h"] for b in full if b["w"] < 145 and b["h"] < 150)
    x_height = max(b["h"] for b in full if b["h"] < 150)
    asc_top  = min(b["y"] for b in full)

    # stem = median first-run (see the JS note); no cap needed now that a merged
    # k-diagonal junction can't inflate it
    stem = float(m["stemRun"])

    letters = [{"x0": round(b["x"] - box["x"], 1),
                "x1": round(b["x"] + b["w"] - box["x"], 1),
                "w":  round(b["w"], 1)} for b in full + small]

    mod = {
        "d": " ".join(paths),
        "width": box["w"], "height": box["h"],
        "origin": {"x": box["x"], "y": box["y"]},
        "letters": letters,
        "profile": [round(v, 4) for v in m["profile"]],
        "metrics": {
            "xHeight": round(x_height, 1),
            "ascender": round(baseline - asc_top, 1),
            "stemWidth": round(stem, 1),
            "inkCoveragePct": round(m["inkPct"], 1),
            "letterCount": 6,
            "baseline": round(baseline - box["y"], 1),
        },
        "source": "bonk-wordmark.svg (canonical lowercase lockup: bonk + small dj)",
    }
    return mod


# ─────────────────────────────── B. from the typeface ───────────────────────────

def build_font_module(weight=700):
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.misc.transform import Transform

    f = TTFont(FONT, fontNumber=0)
    f = instantiateVariableFont(f, {"wght": weight}, inplace=True)
    upem = f["head"].unitsPerEm
    cmap = f.getBestCmap()
    gs   = f.getGlyphSet()
    hmtx = f["hmtx"]

    word = "bonk"
    parts, pen_x, boxes = [], 0.0, []
    for ch in word:
        gname = cmap[ord(ch)]
        pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}")
        # font space is y-up with origin at the baseline; flip to SVG y-down
        tp = TransformPen(pen, Transform(1, 0, 0, -1, pen_x, 0))
        gs[gname].draw(tp)
        d = pen.getCommands()
        adv = hmtx[gname][0]
        gw, lsb = hmtx[gname]
        parts.append(d)
        boxes.append({"x": pen_x, "adv": adv, "lsb": lsb})
        pen_x += adv

    # Measure real ink by rasterising the word. viewBox == font units, and the SVG's
    # width/height EQUAL the viewBox size, so a canvas of that size maps 1:1 and a
    # raster pixel (x,y) is simply font-unit (vbX+x, vbY+y). No scaling arithmetic.
    # fill is explicit: without it the paths are black and the raster reads 0% ink.
    from playwright.sync_api import sync_playwright
    vbX, vbY = -200, -900
    vbW, vbH = int(pen_x) + 400, 1500
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vbX} {vbY} {vbW} {vbH}" '
           f'width="{vbW}" height="{vbH}" fill="#fff">'
           + "".join(f'<path d="{d}"/>' for d in parts) + '</svg>')
    js = """async ([markup, buckets, vbX, vbY, vbW, vbH]) => {
      const host=document.createElement('div'); host.style.cssText='position:fixed;left:-99999px';
      host.innerHTML=markup; document.body.appendChild(host);
      const boxes=[...host.querySelectorAll('path')].map(p=>{const b=p.getBBox();
        return {x:b.x,y:b.y,w:b.width,h:b.height};});
      host.remove();
      const blob=new Blob([markup],{type:'image/svg+xml'}); const url=URL.createObjectURL(blob);
      const img=new Image(); await new Promise((r,j)=>{img.onload=r;img.onerror=j;img.src=url;});
      const cv=document.createElement('canvas'); cv.width=vbW; cv.height=vbH;
      const cx=cv.getContext('2d',{willReadFrequently:true});
      cx.fillStyle='#000'; cx.fillRect(0,0,vbW,vbH);
      cx.drawImage(img, 0, 0, vbW, vbH);
      const id=cx.getImageData(0,0,vbW,vbH).data;
      let x0=vbW,y0=vbH,x1=-1,y1=-1,ink=0;
      for(let y=0;y<vbH;y++) for(let x=0;x<vbW;x++) if(id[(y*vbW+x)*4]>127){
        ink++; if(x<x0)x0=x; if(x>x1)x1=x; if(y<y0)y0=y; if(y>y1)y1=y; }
      const bw=x1-x0+1, bh=y1-y0+1;
      const prof=new Array(buckets).fill(0), cnt=new Array(buckets).fill(0);
      for(let x=x0;x<=x1;x++){ const b=Math.min(buckets-1,Math.floor(((x-x0)/bw)*buckets)); cnt[b]++;
        for(let y=y0;y<=y1;y++) if(id[(y*vbW+x)*4]>127) prof[b]++; }
      for(let i=0;i<buckets;i++) prof[i]=cnt[i]?prof[i]/cnt[i]:0;
      // median first-run = stem thickness (same reasoning as the lockup path above):
      // b is leftmost, so the row's first ink run is its stem
      const fr=[];
      for(let y=y0;y<=y1;y++){ let run=0;
        for(let x=x0;x<=x1;x++){ if(id[(y*vbW+x)*4]>127) run++; else if(run) break; }
        if(run) fr.push(run); }
      fr.sort((a,b)=>a-b);
      const stemRun = fr.length ? fr[Math.floor(fr.length/2)] : 0;
      URL.revokeObjectURL(url);
      return {boxes, rasterPx:{x0,y0,x1,y1}, ink, inkPct:ink/(bw*bh)*100,
              profile:prof, stemRun};
    }"""
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 1200, 'height': 1200})
        pg.goto("about:blank")
        r = pg.evaluate(js, [svg, PROFILE_BUCKETS, vbX, vbY, vbW, vbH])
        br.close()

    # raster px -> font units (1:1; only the viewBox origin has to be added back)
    bx0 = vbX + r["rasterPx"]["x0"]; bx1 = vbX + r["rasterPx"]["x1"] + 1
    by0 = vbY + r["rasterPx"]["y0"]; by1 = vbY + r["rasterPx"]["y1"] + 1
    bw, bh = bx1 - bx0, by1 - by0
    assert bw > 0 and bh > 0, f"font raster failed: {r['rasterPx']}"

    # per-glyph windows come from the DOM boxes (already in viewBox units)
    letters = [{"x0": round(b["x"] - bx0, 1),
                "x1": round(b["x"] + b["w"] - bx0, 1),
                "w":  round(b["w"], 1)} for b in r["boxes"]]

    # vertical metrics in font units, relative to the baseline at y=0 (flipped space)
    o = r["boxes"][1]                                    # 'o'
    b0 = r["boxes"][0]                                   # 'b'
    x_height = o["h"]
    ascender = -b0["y"]                                  # top of b above baseline

    stem = r["stemRun"]

    mod = {
        "d": " ".join(parts),
        "width": round(bw, 1), "height": round(bh, 1),
        "origin": {"x": round(bx0, 1), "y": round(by0, 1)},
        "letters": letters,
        "profile": [round(v, 4) for v in r["profile"]],
        "metrics": {
            "xHeight": round(x_height, 1),
            "ascender": round(ascender, 1),
            "stemWidth": round(stem, 1),
            "inkCoveragePct": round(r["inkPct"], 1),
            "letterCount": 4,
            # box-relative, matching the lockup module's convention. Storing the raw
            # font-space 0 here made any consumer sample row -276 on a raster whose
            # y=0 is the box top: out of range, silently zero ink.
            "baseline": round(0 - by0, 1),
        },
        "source": f"outlined from Bonk-VF.ttf (Bonk Variable, wght {weight})",
        "upem": upem,
    }
    return mod


def emit(mod, path, varname):
    body = json.dumps(mod, separators=(",", ":"))
    head = (f"// generated by extract_mark2.py — do not hand-edit\n"
            f"// {mod['source']}\n")
    path.write_text(f"{head}window.{varname} = {body};\n")
    return path.stat().st_size


if __name__ == "__main__":
    a = build_lockup_module()
    sa = emit(a, PUB / "bonk-mark-v2.js", "BONK_MARK_V2")
    print(f"A) canonical lockup -> bonk-mark-v2.js  {sa:,} bytes")
    print(f"   {a['width']} x {a['height']}   origin {a['origin']}   letters {len(a['letters'])}")
    print(f"   xHeight {a['metrics']['xHeight']}  ascender {a['metrics']['ascender']}  "
          f"stem {a['metrics']['stemWidth']}  ink {a['metrics']['inkCoveragePct']}%")

    b = build_font_module(700)
    sb = emit(b, PUB / "bonk-mark-font.js", "BONK_MARK_FONT")
    print(f"\nB) from Bonk-VF.ttf  -> bonk-mark-font.js  {sb:,} bytes")
    print(f"   {b['width']} x {b['height']}   origin {b['origin']}   letters {len(b['letters'])}")
    print(f"   xHeight {b['metrics']['xHeight']}  ascender {b['metrics']['ascender']}  "
          f"stem {b['metrics']['stemWidth']}  ink {b['metrics']['inkCoveragePct']}%")
