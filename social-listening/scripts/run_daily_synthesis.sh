#!/bin/zsh
set -euo pipefail
ROOT="$HOME/ContentOps/social-listening"
"$ROOT/.venv/bin/python3" "$ROOT/scripts/daily_synthesis.py"
