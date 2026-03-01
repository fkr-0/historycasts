#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8088}"
SERVE_DIR="${SERVE_DIR:-frontend/dist}"

WATCH_PATHS=(
  "src"
  "scripts"
  "tests"
  "frontend/src"
  "frontend/index.html"
  "frontend/tailwind.config.js"
  "frontend/postcss.config.js"
  "frontend/vite.config.ts"
  "frontend/package.json"
  "README.md"
  "CHANGELOG.md"
  "ARCHITECTURE.md"
  "Makefile"
  "pyproject.toml"
)

EXCLUDE_REGEX='(^|/)(\.git|\.venv|node_modules|dist|__pycache__|legacy|pages|pages_local)(/|$)'

sync_dataset_into_dist() {
  if [[ -f "static_site/dataset.json" && -d "$SERVE_DIR" ]]; then
    cp "static_site/dataset.json" "$SERVE_DIR/dataset.json"
  fi
}

rebuild_static() {
  echo "[watch-static] rebuilding at $(date -Iseconds)"
  if make static; then
    sync_dataset_into_dist
    echo "[watch-static] rebuild complete"
  else
    echo "[watch-static] rebuild failed (waiting for next change)"
  fi
}

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" || true
  fi
}
trap cleanup EXIT INT TERM

rebuild_static

echo "[watch-static] serving $SERVE_DIR on http://$HOST:$PORT"
python -m http.server "$PORT" --bind "$HOST" --directory "$SERVE_DIR" >/dev/null 2>&1 &
SERVER_PID=$!

if command -v inotifywait >/dev/null 2>&1; then
  echo "[watch-static] using inotifywait watcher"
  while inotifywait -qq -r -e close_write,create,delete,move --exclude "$EXCLUDE_REGEX" "${WATCH_PATHS[@]}"; do
    rebuild_static
  done
else
  echo "[watch-static] inotifywait not found; using polling fallback"
  last_sig=""
  while true; do
    sig="$(
      find "${WATCH_PATHS[@]}" -type f 2>/dev/null \
        | grep -Ev "$EXCLUDE_REGEX" \
        | sort \
        | xargs -r stat -c '%n:%Y' \
        | sha256sum \
        | awk '{print $1}'
    )"
    if [[ "$sig" != "$last_sig" ]]; then
      last_sig="$sig"
      rebuild_static
    fi
    sleep 1
  done
fi
