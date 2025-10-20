#!/bin/bash

# Snapshot defaults
SNAP="${SNAPSHOT_OUT:-repo_flat.txt}"
EXCLUDE='(.git|.venv|venv|node_modules|__pycache__|.pytest_cache|.mypy_cache|.ruff_cache|.cache|.xsarena/jobs|review|snapshot_chunks)'

# Header + tree map
: > "$SNAP"
printf "# Repo Flat Pack\n\nInstructions:\n- Boundaries mark files.\n- Ask for next files if needed.\n\n" >> "$SNAP"
printf "## Repo Tree (filtered)\n\n" >> "$SNAP"
if command -v tree >/dev/null 2>&1; then
  tree -a -I "$EXCLUDE" -n --prune | sed 's/\x1B\[[0-9;]*[mK]//g' >> "$SNAP"
else
  # Fallback tree
  find . -type d | grep -Ev "/$EXCLUDE($|/)" | sed 's#^\./##' | sort >> "$SNAP"
fi
printf "\n" >> "$SNAP"

# File list (stable, filtered)
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  FILES=$(git ls-files | grep -Ev "^($EXCLUDE)(/|$)")
else
  FILES=$(find . -type f | grep -Ev "/($EXCLUDE)(/|$)" | sed 's#^\./##' | sort)
fi

# Concatenate text/code files with boundaries (skip binaries)
for f in $FILES; do
  mime=$(file -bi "$f" 2>/dev/null || echo text/plain)
  case "$mime" in
    *charset=binary*|application/octet-stream*) continue;;
  esac
  printf "=== START FILE: %s ===\n" "$f" >> "$SNAP"
  # Normalize line endings; avoid huge files implicitly by relying on your budget tooling if needed
  sed 's/\r$//' "$f" >> "$SNAP"
  printf "\n=== END FILE: %s ===\n\n" "$f" >> "$SNAP"
done

# Size summary
printf "## Snapshot Size\n\n" >> "$SNAP"
bytes=$(wc -c < "$SNAP" | tr -d ' ')
printf "Total bytes: %s\n" "$bytes" >> "$SNAP"
echo "Snapshot written → $SNAP"