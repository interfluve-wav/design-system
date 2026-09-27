"""Render the 5 carousel cards at 1080x1350 and verify nothing is clipped.

The card is fixed at 1080x1350 with overflow:hidden, so an overlong body would be
silently cut off rather than reported. slides 2 and 4 have the longest copy, so
this checks scrollHeight against the card height and fails loudly if content does
not fit.
"""
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/projects/instagram/carousel.html"
OUT = "/Users/suhaas/Pictures/design - tiles - motion"
W, H = 1080, 1350

CHECK = """
() => {
  const c = document.getElementById('card');
  const t = document.querySelector('.teaser');
  const b = document.querySelector('.body');
  const link = document.querySelector('.link');
  const bottom = link ? link.getBoundingClientRect().bottom
                      : (b ? b.getBoundingClientRect().bottom : 0);
  const dots = document.querySelector('.dots').getBoundingClientRect();
  return {
    cardH: c.getBoundingClientRect().height,
    contentH: Math.round(Math.max(c.scrollHeight, bottom, dots.bottom)),
    teaserLines: t ? Math.round(t.getBoundingClientRect().height / (104 * 1.06)) : 0,
    bodyH: b ? Math.round(b.getBoundingClientRect().height) : 0,
    marks: window.__markReady,
    font: document.fonts.check("600 100px 'Bonk'"),
    italic: document.fonts.check("italic 500 100px 'Bonk'"),
  };
}
"""

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    print(f"  rendering 5 cards at {W}x{H}\n")
    print("  slide  ink%   contentH  teaser  bodyH  mark  font  ital  mark%  file")
    bad = 0
    for n in range(1, 6):
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{URL}?n={n}", wait_until="load")
        pg.evaluate("() => window.__ready")
        pg.wait_for_function("() => window.__markReady !== undefined", timeout=10000)
        r = pg.evaluate(CHECK)
        path = f"{OUT}/bonk-carousel-{n}.png"
        pg.screenshot(path=path)
        a = np.asarray(Image.open(path).convert("L"), dtype=float)
        ink = 100 * (a > 40).mean()
        # the mark slot: if the glyphs lost their fill they vanish into the black
        # card and every other check still passes. Assert it explicitly.
        mark_ink = 100 * (a[90:180, 88:280] > 40).mean()
        clip = "" if r["contentH"] <= H else "  CLIPPED"
        if clip or r["marks"] != 6 or not r["font"] or mark_ink < 0.5:
            bad += 1
        print(f"  {n}      {ink:5.2f}  {r['contentH']:>8}{clip:<9} {r['teaserLines']:>4}   "
              f"{r['bodyH']:>4}  {str(r['marks']):>4}  {str(r['font'])[0]}     "
              f"{str(r['italic'])[0]}    {mark_ink:5.2f}  bonk-carousel-{n}.png")
        if errs:
            print(f"         PAGE ERRORS: {errs[:2]}")
    br.close()
print()
print(f"  cards with problems: {bad}")
