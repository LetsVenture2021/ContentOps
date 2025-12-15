#!/bin/zsh
set -euo pipefail

ROOT="$HOME/ContentOps/social-listening"
LOCKDIR="$ROOT/.pipeline.lock"

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCKDIR"' EXIT

"$ROOT/.venv/bin/python3" "$ROOT/scripts/ingest_mentions.py"
"$ROOT/.venv/bin/python3" "$ROOT/scripts/classify_and_route.py"
