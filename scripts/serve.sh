#!/usr/bin/env bash
# Serve the sandbox so the LEDGER.md links resolve.
#
#   bash scripts/serve.sh            # foreground on 8765
#   bash scripts/serve.sh 9000       # different port
#
# Every entry point in LEDGER.md §1 is http://127.0.0.1:<port>/<project path>. A plain
# static server is correct for all of them -- the four pages that imported ./src/*.ts are
# gone (moved to _archive/), and .ts pages are dead over http.server because it maps .ts
# to video/mp2t (docs/GOTCHAS.md §8.17).
set -euo pipefail
PORT="${1:-8765}"
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "serving $(pwd)"
echo "  http://127.0.0.1:${PORT}/projects/blurreveal/public/v4-scenes.html"
echo "  http://127.0.0.1:${PORT}/projects/motion-system/bonk-motion-system-v3.html"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
