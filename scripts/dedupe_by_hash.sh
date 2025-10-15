#!/usr/bin/env bash
set -euo pipefail
APPLY="${APPLY:-0}"
while read -r hash; do
  # list files for this hash
  files=$(grep "^$hash " review/books_sha256.txt | awk '{print $2}')
  keep=""
  newest_mtime=0
  for f in $files; do
    mt=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0)
    if [ "$mt" -gt "$newest_mtime" ]; then newest_mtime="$mt"; keep="$f"; fi
  done
  for f in $files; do
    [ "$f" = "$keep" ] && continue
    echo "archive dup: $f (keep: $keep)"
    if [ "$APPLY" = "1" ]; then
      mkdir -p books/archive
      git mv "$f" "books/archive/$(basename "$f")" 2>/dev/null || mv "$f" "books/archive/$(basename "$f")"
    fi
  done
done < review/dup_hashes.txt
echo "Dry-run. Re-run with APPLY=1 to apply."