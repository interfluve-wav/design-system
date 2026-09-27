#!/usr/bin/env python3
"""Check that every entry point linked in LEDGER.md section 1 actually serves.

A ledger full of dead links is worse than no ledger. This is the check that keeps
section 1 honest -- run it after any rename, move, or new project.

Usage:
    python3 -m http.server 8765 --bind 127.0.0.1     # from the sandbox root
    python3 scripts/check_links.py [--port 8765]
"""
import argparse
import sys
import urllib.error
import urllib.request

PATHS = [
    "projects/blurreveal/public/v4-scenes.html",
    "projects/blurreveal/public/v4-light-scenes.html",
    "projects/motion-system/bonk-motion-system-v3.html",
    "projects/motion-system/bonk-motion-system-v2.html",
    "projects/blueprint/public/bonk-blueprint.html",
    "projects/blueprint/public/bonk-blueprint-v2.html",
    "projects/blueprint/public/bonk-blueprint-v3-sup.html",
    "projects/dotcut/public/dotcut-demo.html",
    "projects/dotcut/public/bonk-logo.html",
    "projects/dotcut/public/bonk-wordmark.html",
    "projects/design-tiles/public/design-tiles-demo.html",
    "projects/libs-dev/bonk-libsdev.html",
    "projects/logo/logo-lockup-compare.html",
    "projects/logo/bonk-sup.html",
    "projects/motion-assets/ripple.html",
    "fonts/specimen.html",
    "projects/motion-system/bonk-intro-preview.html",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    base = "http://127.0.0.1:%d" % args.port

    bad = []
    for path in PATHS:
        url = "%s/%s" % (base, path)
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except OSError as e:
            print("  server unreachable on %s (%s)" % (base, e))
            print("  start it:  python3 -m http.server %d --bind 127.0.0.1" % args.port)
            return 2
        mark = "ok " if code == 200 else "BAD"
        print("  %s  %s  %s" % (mark, code, path))
        if code != 200:
            bad.append(path)

    print("\n  %d/%d resolve, %d bad" % (len(PATHS) - len(bad), len(PATHS), len(bad)))
    for p in bad:
        print("    ! %s" % p)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
