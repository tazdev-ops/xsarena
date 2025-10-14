#!/usr/bin/env bash
set -euo pipefail
echo "[prepush] lint/format/tests..."
ruff check .    >/dev/null
black --check . >/dev/null
pytest -q       >/dev/null
if [ -x scripts/gen_docs.sh ]; then
  echo "[prepush] doc help drift..."
  bash scripts/gen_docs.sh
  git diff --exit-code docs/_help_*.txt >/dev/null || { echo "[prepush] help drift; commit docs."; exit 1; }
fi
echo "[prepush] ephemeral scan..."
git add -N . >/dev/null 2>&1 || true
GLOB=$(git ls-files -mo --exclude-standard)
echo "$GLOB" | grep -E '^(review/|snapshot_chunks/|xsa_min_snapshot|\.xsarena/tmp/)' && { echo "[prepush] ephemeral detected; clean or .gitignore"; exit 1; }
echo "[prepush] OK"