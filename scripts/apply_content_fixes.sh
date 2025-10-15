#!/usr/bin/env bash
set -euo pipefail
APPLY="${APPLY:-0}"

mv2() { src="$1"; dst="$2"; [ -f "$src" ] || return 0; [ -e "$dst" ] && { echo "SKIP (exists): $dst"; return 0; }
  echo "mv '$src' → '$dst'"; if [ "$APPLY" = "1" ]; then mkdir -p "$(dirname "$dst")"; git mv "$src" "$dst" 2>/dev/null || mv "$src" "$dst"; fi; }

rm2() { f="$1"; [ -f "$f" ] || return 0; echo "rm '$f'"; [ "$APPLY" = "1" ] && (git rm -f "$f" 2>/dev/null || rm -f "$f"); }

# 1) Finals/outlines into their subfolders (idempotent)
for f in books/*.final.md books/*.manual.en.md; do
  [ -f "$f" ] && mv2 "$f" "books/finals/$(basename "$f")"
done
for f in books/*.outline.md; do
  [ -f "$f" ] && mv2 "$f" "books/outlines/$(basename "$f")"
done

# 2) Archive tiny or placeholder files
#   From review/small_md.txt (size ≤ 2B) and clear duplicates by hash from review/dups_by_hash.txt
rm2 "books/clinical-psychology.outline.md"
rm2 "books/pre-islamic-iranian-history.outline.md"
rm2 "books/political-sceince.outline.md"  # typo; canonical exists at books/outlines/political-science.outline.md

# 3) Archive a 20-byte placeholder if still present at root
if [ -f "books/american-political-history.md" ]; then
  size=$(wc -c < "books/american-political-history.md")
  if [ "$size" -le 64 ]; then
    mv2 "books/american-political-history.md" "books/archive/american-political-history.md"
  fi
fi

# 4) Verify "first-chunk" pair is resolved (keep larger file; archive the smaller one)
A="books/history-of-america-political-first-chunk-outline.md"
B_ARCH="books/archive/history-of-america-political-first-chunk-outline.outline.md"
[ -f "$A" ] && [ -f "$B_ARCH" ] && echo "Keeping $A (larger), archived smaller $B_ARCH already."

echo "Dry-run complete. Re-run with: APPLY=1 bash scripts/apply_content_fixes.sh"