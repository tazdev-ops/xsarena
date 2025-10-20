#!/bin/bash

# Health check (tree comparison + size budget)
# Keep a filtered tree baseline and compare structure/size between runs; warn on big drifts.

BASE=".xsarena/ops"
mkdir -p "$BASE"
TREE_NOW="$BASE/tree.now.txt"
TREE_BASE="$BASE/tree.base.txt"
SNAP="${SNAPSHOT_OUT:-repo_flat.txt}"

# Current tree (filtered)
if command -v tree >/dev/null 2>&1; then
  tree -a -I "$EXCLUDE" -n --prune | sed 's/\x1B\[[0-9;]*[mK]//g' > "$TREE_NOW"
else
  find . -type f | grep -Ev "/($EXCLUDE)(/|$)" | sed 's#^\./##' | sort > "$TREE_NOW"
fi

# First run: set baseline
[ -s "$TREE_BASE" ] || cp "$TREE_NOW" "$TREE_BASE"

echo "Tree diff (baseline vs now):"
diff -u "$TREE_BASE" "$TREE_NOW" || true

# Size estimation target (~500–550 KB ideal)
SZ=$( [ -f "$SNAP" ] && wc -c < "$SNAP" | tr -d ' ' || echo 0 )
echo "Snapshot size (bytes): $SZ"
if [ "$SZ" -gt 600000 ]; then
  echo "WARN: snapshot > 600KB; consider trimming or using tighter mode."
fi

# Update baseline if desired:
# cp "$TREE_NOW" "$TREE_BASE"