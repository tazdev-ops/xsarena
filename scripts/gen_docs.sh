#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs

xsarena --help > docs/_help_root.txt || true
xsarena service --help > docs/_help_serve.txt || true
xsarena snapshot --help > docs/_help_snapshot.txt || true
xsarena jobs --help > docs/_help_jobs.txt || true
xsarena fix --help > docs/_help_fix.txt || true
xsarena book --help > docs/_help_z2h.txt || true
xsarena clean --help > docs/_help_clean.txt || true
xsarena continue --help > docs/_help_continue.txt || true
xsarena debug --help > docs/_help_debug.txt || true

echo "Help docs regenerated under docs/_help_*.txt"