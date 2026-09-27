#!/usr/bin/env python3
"""scan_models.py — boot every motion piece and read what it actually exposes.

The registry is MEASURED, not parsed. `build_gallery.py` regexes `:root` out of the
source, which works until it doesn't (GOTCHAS §7: a folder refactor left two
verification scripts reading stale paths, and they kept *succeeding* while measuring
nothing). This boots the piece in headless Chromium and asks it, so a model whose
block the parser cannot read is still correctly indexed — because the browser ran it.

    python3 scripts/scan_models.py                  # all pieces → registry.json
    python3 scripts/scan_models.py --only glow      # one
    python3 scripts/scan_models.py --diff           # + pixel-diff vs _archive/pre-models
    python3 scripts/scan_models.py --list           # names only, for scripting

Exit code is a real gate: non-zero if any piece throws, warns, or fails to reach
__ready. A harness that reports MISSING rows and exits 0 is worse than no harness.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "projects"
SNAP = ROOT / "_archive" / "pre-models"
LIB = PROJ / "motion-library"
BASE = "http://127.0.0.1:8765"
VIEW = {"width": 1280, "height": 720}
DIFF_TIMES = (1.0, 2.5, 4.0, 6.0, 9.0)

# not pieces: the kit, the generated gallery, font assets
SKIP_PARTS = {"kit", "fonts", "node_modules", "assets"}
SKIP_NAMES = {"index.html"}          # motion-library/index.html is generated


def discover(only: str | None = None) -> list[dict]:
    out = []
    for p in sorted(PROJ.rglob("*.html")):
        rel = p.relative_to(PROJ)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if p.name in SKIP_NAMES and rel.parts[0] == "motion-library":
            continue
        if only and only not in str(rel):
            continue
        src = p.read_text(errors="replace")
        out.append({
            "file": p.name,
            "rel": str(rel),
            "family": rel.parts[0] if len(rel.parts) > 1 else "(root)",
            "url": f"{BASE}/projects/{rel.as_posix()}",
            "snapshot": (SNAP / "projects" / rel).exists(),
            "lines": src.count("\n") + 1,
            "bytes": len(src),
        })
    return out


async def scan_one(browser, rec: dict, do_diff: bool) -> dict:
    page = await browser.new_page(viewport=VIEW)
    errors, consoles = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: consoles.append(f"{m.type}: {m.text}")
            if m.type in ("error", "warning") else None)

    rec.update({"modelled": False, "ready": False, "errors": errors, "consoles": consoles,
                "warnings": [], "duration": None, "frame": None, "theme": {},
                "params": [], "text": {}, "scenes": None, "purpose": "", "id": None,
                "title": None, "notes": "", "diff": None})

    try:
        await page.goto(rec["url"], wait_until="load", timeout=20000)
    except Exception as e:
        rec["errors"].append(f"goto failed: {e}")
        await page.close()
        return rec

    rec["modelled"] = await page.evaluate("typeof window.__params === 'function'")
    if not rec["modelled"]:
        # still record what it exposes, so the KB can say "not converted yet" honestly
        rec["theme"] = await page.evaluate(
            """() => { const cs = getComputedStyle(document.documentElement);
                       const o = {}; for (const n of cs) if (n.startsWith('--')) o[n] = cs.getPropertyValue(n).trim();
                       return o; }""")
        rec["has_seek"] = await page.evaluate("typeof window.__seek === 'function'")
        await page.close()
        return rec

    try:
        # `evaluate` has no timeout kwarg — wait for the promise to exist, then await it
        await page.wait_for_function("() => !!window.__ready", timeout=15000)
        await asyncio.wait_for(page.evaluate("() => window.__ready"), timeout=20)
    except Exception as e:
        rec["errors"].append(f"__ready never resolved: {e}")
        await page.close()
        return rec
    rec["ready"] = True

    got = await page.evaluate("""() => ({
        warnings: window.__warnings || [],
        model:    window.__model || null,
        params:   window.__params ? window.__params() : [],
        theme:    window.__theme ? window.__theme() : {},
        duration: window.__duration || null,
        frame:    window.__frame || null,
        scenes:   window.__scenes ? window.__scenes() : null,
    })""")
    rec["warnings"] = got["warnings"]
    rec["params"] = got["params"]
    rec["theme"] = got["theme"]
    rec["duration"] = got["duration"]
    rec["frame"] = got["frame"]
    rec["scenes"] = got["scenes"] or None
    m = got["model"] or {}
    rec["id"] = m.get("id")
    rec["title"] = m.get("title")
    rec["purpose"] = m.get("purpose", "")
    rec["notes"] = m.get("notes", "")
    rec["text"] = m.get("text", {})
    rec["colours"] = m.get("colours", [])
    rec["overridden"] = m.get("overrides", [])
    rec["has_seek"] = await page.evaluate("typeof window.__seek === 'function'")

    if do_diff and rec["snapshot"] and rec["has_seek"]:
        rec["diff"] = await diff_one(browser, rec)
    await page.close()
    return rec


async def diff_one(browser, rec: dict) -> dict:
    """Pixel-diff the live piece against its own pre-retrofit snapshot.

    A retrofit is only non-destructive if it can be SHOWN to be. Same viewport, same
    seek times, same screenshot path — so any difference is the edit itself."""
    import numpy as np
    from PIL import Image

    snap_url = (f"{BASE}/_archive/pre-models/projects/{rec['rel']}")
    shots = {}
    for tag, url in (("old", snap_url), ("new", rec["url"])):
        pg = await browser.new_page(viewport=VIEW)
        try:
            await pg.goto(url, wait_until="load", timeout=20000)
            try:
                await pg.wait_for_function("() => !!window.__ready", timeout=15000)
            except Exception:
                pass
            buf = []
            for t in DIFF_TIMES:
                await pg.evaluate(f"window.__seek({t})")
                await pg.wait_for_timeout(90)
                buf.append(await pg.screenshot())
            shots[tag] = buf
        except Exception as e:
            return {"error": f"{tag}: {e}"}
        finally:
            await pg.close()

    import io
    worst, frames = 0.0, []
    for i, t in enumerate(DIFF_TIMES):
        a = np.asarray(Image.open(io.BytesIO(shots["old"][i])).convert("L")).astype(int)
        b = np.asarray(Image.open(io.BytesIO(shots["new"][i])).convert("L")).astype(int)
        if a.shape != b.shape:
            return {"error": f"size mismatch at t={t}: {a.shape} vs {b.shape}"}
        pct = float(100.0 * (np.abs(a - b) > 8).mean())
        frames.append({"t": t, "pct": round(pct, 4)})
        worst = max(worst, pct)
    return {"worst_pct": round(worst, 4), "frames": frames}


def verdict(rec: dict) -> tuple[str, str]:
    if not rec["modelled"]:
        return "unmodelled", "no MotionModel.define — not converted yet"
    if rec["errors"]:
        return "THROWS", rec["errors"][0][:90]
    if rec["warnings"]:
        return "WARNS", rec["warnings"][0][:90]
    if not rec["ready"]:
        return "NO READY", "__ready never resolved"
    if not rec["params"]:
        return "BARE", "model declares no parameters"
    if rec["diff"] and rec["diff"].get("worst_pct", 0) > 5.0:
        return "MOVED", f"{rec['diff']['worst_pct']}% of pixels changed vs snapshot"
    return "ok", ""


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="substring filter on the path")
    ap.add_argument("--diff", action="store_true", help="pixel-diff vs _archive/pre-models")
    ap.add_argument("--list", action="store_true", help="one id per line")
    ap.add_argument("--no-write", action="store_true",
                    help="print the table only — do not touch registry.json / model-scan.txt "
                         "(use this when several scans run in parallel)")
    args = ap.parse_args()

    pieces = discover(args.only)
    if not pieces:
        print("no pieces matched", file=sys.stderr)
        return 2
    if args.list:
        for p in pieces:
            print(p["rel"])
        return 0

    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        results = [await scan_one(browser, p, args.diff) for p in pieces]
        await browser.close()

    LIB.mkdir(parents=True, exist_ok=True)
    if not args.no_write:
        (LIB / "registry.json").write_text(json.dumps({
            "generated": datetime.now().isoformat(timespec="seconds"),
            "generator": "scripts/scan_models.py",
            "base": BASE,
            "pieces": results,
        }, indent=2))

    lines = [f"model scan — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             f"{len(pieces)} pieces over {BASE} at {VIEW['width']}x{VIEW['height']}", ""]
    bad = 0
    print(f"{'piece':44s} {'verdict':10s} {'params':>6s} {'dur':>7s} {'diff%':>7s}  note")
    for r in results:
        v, note = verdict(r)
        if v not in ("ok", "unmodelled"):
            bad += 1
        d = r["diff"].get("worst_pct") if isinstance(r.get("diff"), dict) and "worst_pct" in r["diff"] else None
        row = (f"{r['rel']:44s} {v:10s} {len(r['params']):6d} "
               f"{(('%.2f' % r['duration']) if r['duration'] else '-'):>7s} "
               f"{(('%.3f' % d) if d is not None else '-'):>7s}  {note}")
        print(row)
        lines.append(row)
        for e in r["errors"]:
            lines.append(f"    error: {e}")
        for w in r["warnings"]:
            lines.append(f"    warn:  {w}")

    modelled = sum(1 for r in results if r["modelled"])
    summary = (f"\n{modelled}/{len(pieces)} pieces declare a model · "
               f"{len(results)-modelled} unmodelled · {bad} failing")
    print(summary)
    lines.append(summary)

    if not args.no_write:
        (ROOT / "docs" / "model-scan.txt").write_text("\n".join(lines) + "\n")
        print("wrote projects/motion-library/registry.json and docs/model-scan.txt")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
