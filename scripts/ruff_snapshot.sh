#!/usr/bin/env bash
set -euo pipefail
mkdir -p .lint
# Exit zero so we always get a JSON snapshot even with many errors.
ruff check . --exit-zero --output-format=json > .lint/ruff.json
echo "[ruff_snapshot] wrote .lint/ruff.json"
