#!/usr/bin/env bash
set -euo pipefail
echo "[guard] scanning staged paths..."
STAGED=$(git diff --cached --name-only || true)
bad=0
for pat in "snapshot_chunks/" "xsa_min_snapshot" "^review/" ".xsarena/tmp/"; do
    if echo "$STAGED" | grep -E "$pat" >/dev/null; then
      echo "[guard] refuse: staged matches $pat"
      bad=1
    fi
done
if [ $bad -ne 0 ]; then
    echo "[guard] remove or .gitignore ephemeral files before commit."
    exit 1
fi
echo "[guard] OK"