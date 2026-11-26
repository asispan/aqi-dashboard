#!/usr/bin/env bash
# Render the 3D product shots into docs/renders/ with headless Chrome.
# Usage: tools/render/render.sh [scene ...]   (default: all scenes)
set -euo pipefail
cd "$(dirname "$0")/../.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
PORT="${PORT:-8812}"
W="${W:-2400}"; H="${H:-1350}"
mkdir -p docs/renders
python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SRV=$!; trap 'kill $SRV' EXIT; sleep 1
for s in "${@:-hero lineup ipad mipad pair}"; do
  for scene in $s; do
    prof="$(mktemp -d)"; w=$W; h=$H; [ "$scene" = lineup ] && h=$((W*10/24))
    "$CHROME" --headless=new --hide-scrollbars --enable-unsafe-swiftshader --use-angle=swiftshader \
      --window-size="$w,$h" --virtual-time-budget=60000 --run-all-compositor-stages-before-draw \
      --user-data-dir="$prof" --screenshot="$PWD/docs/renders/$scene.png" \
      "http://127.0.0.1:$PORT/tools/render/render.html?scene=$scene&w=$w&h=$h" 2>/dev/null
    rm -rf "$prof"; echo "rendered docs/renders/$scene.png"
  done
done
