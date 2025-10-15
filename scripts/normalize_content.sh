#!/usr/bin/env bash
set -euo pipefail
APPLY="${APPLY:-0}"  # set APPLY=1 to actually move

move() { src="$1"; dst="$2"; if [ -f "$src" ] && [ ! -e "$dst" ]; then
  echo "mv '$src' '$dst'"
  if [ "$APPLY" = "1" ]; then mkdir -p "$(dirname "$dst")"; git mv "$src" "$dst" 2>/dev/null || mv "$src" "$dst"; fi
fi }

# timestamped to archive
move "books/american-political-history-20251012-204336.md" "books/archive/american-political-history-20251012-204336.md"

# underscore normalization
move "books/international_relations.manual.en.md" "books/international-relations.manual.en.md"

# typo fix
if [ -f "books/political-sceince.outline.md" ]; then
  if [ -f "books/political-science.outline.md" ]; then
    echo "Both typo and correct exist → review manually: political-sceince vs political-science"
  else
    move "books/political-sceince.outline.md" "books/political-science.outline.md"
  fi
fi

# flashcards to subdir
move "books/ail.scripts.flashcards.md" "books/flashcards/ail.scripts.flashcards.md"

# first-chunk outline duplicates (keep singular)
if [ -f "books/history-of-america-political-first-chunk-outline.outline.md" ] && [ -f "books/history-of-america-political-first-chunk-outline.md" ]; then
  echo "Review diff of the two 'first-chunk-outline' files before removing one:"
  diff -u "books/history-of-america-political-first-chunk-outline.md" "books/history-of-america-political-first-chunk-outline.outline.md" || true
fi

echo "Dry-run by default. Re-run with: APPLY=1 bash ./scripts/normalize_content.sh"