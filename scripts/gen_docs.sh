#!/usr/bin/env bash
set -euo pipefail

export NO_COLOR=1
export RICH_NO_COLOR=1

OUT_DIR="docs"
mkdir -p "$OUT_DIR"

strip_ansi() {
  # Strip ANSI/VT100 codes; keep UTF-8
  sed -r 's/\x1B\[[0-9;]*[mK]//g'
}

echo "Generating CLI help..."
xsarena --help            | strip_ansi > "$OUT_DIR/_help_root.txt"       || true
xsarena run --help        | strip_ansi > "$OUT_DIR/_help_run.txt"        || true
xsarena author --help     | strip_ansi > "$OUT_DIR/_help_author.txt"     || true
xsarena ops --help        | strip_ansi > "$OUT_DIR/_help_ops.txt"        || true
xsarena settings --help   | strip_ansi > "$OUT_DIR/_help_settings.txt"   || true
xsarena utils --help      | strip_ansi > "$OUT_DIR/_help_utils.txt"      || true
xsarena docs --help       | strip_ansi > "$OUT_DIR/_help_docs.txt"       || true

echo "Help generation complete."
