#!/bin/bash

# Script to create a snapshot of the repository with filtered files manifest and health checks

set -e

# Configuration
EXCL='(.git|.venv|venv|node_modules|__pycache__|.pytest_cache|.mypy_cache|.ruff_cache|.cache|.xsarena/jobs|review|snapshot_chunks)'
SNAP="${SNAPSHOT_OUT:-repo_flat.txt}"

# Create the snapshot file
> "$SNAP"

echo "Creating snapshot at: $SNAP"

# Add filtered tree to snapshot
echo "## Repository Tree (filtered)" >> "$SNAP"
if command -v tree >/dev/null 2>&1; then
    tree -a -I "$EXCL" -n --prune | sed 's/\x1B\[[0-9;]*[mK]//g' >> "$SNAP"
else
    find . -type d | grep -Ev "/($EXCL)(/|$)" | sed 's#^\./##' | sort >> "$SNAP"
fi

echo "" >> "$SNAP"

# Determine files to include based on git or find
if git rev-parse --show-toplevel >/dev/null 2>&1; then
    FILES=$(git ls-files | grep -Ev "^($EXCL)(/|$)")
else
    FILES=$(find . -type f | grep -Ev "/($EXCL)(/|$)" | sed 's#^\./##' | sort)
fi

# Add manifest header to snapshot
printf "\n## Included Files (filtered)\n\n" >> "$SNAP"
printf "Count: %s\n" "$(printf "%s\n" "$FILES" | wc -l)" >> "$SNAP"

# Calculate total bytes
printf "%s\n" "$FILES" > /tmp/files_list.tmp
total=0
while read -r f; do
    if [ -f "$f" ]; then
        if stat -c%s . >/dev/null 2>&1; then
            sz=$(stat -c%s "$f" 2>/dev/null)
        else
            sz=$(stat -f%z "$f" 2>/dev/null)
        fi
        if [ -n "$sz" ]; then
            total=$((total + sz))
        fi
    fi
done < /tmp/files_list.tmp
TOTAL=$total
rm /tmp/files_list.tmp
printf "Total bytes: %s\n\n" "$TOTAL" >> "$SNAP"

# Add top 20 largest files
printf "Top 20 largest:\n" >> "$SNAP"
printf "%s\n" "$FILES" | while read -r f; do
    if [ -f "$f" ]; then
        if stat -c%s . >/dev/null 2>&1; then
            sz=$(stat -c%s "$f" 2>/dev/null)
        else
            sz=$(stat -f%z "$f" 2>/dev/null)
        fi
        if [ -n "$sz" ]; then
            printf "%12s  %s\n" "$sz" "$f"
        fi
    fi
done | sort -nr | head -20 >> "$SNAP"
printf "\n" >> "$SNAP"

# Add per-extension count
printf "By extension (count):\n" >> "$SNAP"
printf "%s\n" "$FILES" | awk -F. 'NF>1{ext=tolower($NF);c[ext]++} END{for(k in c) printf "%-10s %6d\n",k,c[k]}' | sort >> "$SNAP"
printf "\n" >> "$SNAP"

# Add SHA/size manifest
printf "SHA/size manifest:\n" >> "$SNAP"
printf "%s\n" "$FILES" | while read -r f; do
    if [ -f "$f" ]; then
        if stat -c%s . >/dev/null 2>&1; then
            sz=$(stat -c%s "$f" 2>/dev/null)
        else
            sz=$(stat -f%z "$f" 2>/dev/null)
        fi
        sha=$(sha256sum "$f" 2>/dev/null | awk '{print $1}')
        [ -z "$sha" ] && sha="[no-sha256sum]"
        [ -z "$sz" ] && sz="[no-size]"
        printf "%12s  %s  %s\n" "$sz" "$sha" "$f" >> "$SNAP"
    fi
done
printf "\n" >> "$SNAP"

echo "Snapshot created successfully: $SNAP"

# Health check implementation
BASE=".xsarena/ops"
mkdir -p "$BASE"
TREE_NOW="$BASE/tree.now.txt"
TREE_BASE="$BASE/tree.base.txt"

# Create current tree (filtered)
if command -v tree >/dev/null 2>&1; then
    tree -a -I "$EXCL" -n --prune | sed 's/\x1B\[[0-9;]*[mK]//g' > "$TREE_NOW"
else
    find . -type f | grep -Ev "/($EXCL)(/|$)" | sed 's#^\./##' | sort > "$TREE_NOW"
fi

# Create baseline if it doesn't exist
if [ ! -s "$TREE_BASE" ]; then
    cp "$TREE_NOW" "$TREE_BASE"
    echo "Created baseline tree at: $TREE_BASE"
fi

# Show structural diff
echo "Tree diff:"
diff -u "$TREE_BASE" "$TREE_NOW" || true

# Check snapshot size
SZ=$( [ -f "$SNAP" ] && wc -c < "$SNAP" | tr -d ' ' || echo 0 )
echo "Snapshot size (bytes): $SZ"
if [ "$SZ" -gt 600000 ]; then
    echo "WARN: snapshot > ~600KB; consider trimming or tight-500k preset."
elif [ "$SZ" -gt 550000 ]; then
    echo "INFO: snapshot > ~550KB; approaching size limit."
fi

echo "Health check completed."