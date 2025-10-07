#!/usr/bin/env bash
set -euo pipefail
FILE="${1:?file}"
mkdir -p .lint
ruff check "$FILE" --exit-zero --format=json > ".lint/$(echo "$FILE" | tr '/' '_').json"
echo "[ruff_file_json] wrote .lint/$(echo "$FILE" | tr '/' '_').json"
