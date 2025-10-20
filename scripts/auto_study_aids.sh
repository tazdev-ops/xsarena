#!/bin/bash
# Automatically create study aids after book generation

BOOK="$1"

if [ -z "$BOOK" ]; then
    echo "Usage: $0 <book.md>"
    exit 1
fi

if [ ! -f "$BOOK" ]; then
    echo "Error: $BOOK not found"
    exit 1
fi

BASENAME=$(basename "$BOOK" .md)
STUDY_DIR="./study/${BASENAME}"

mkdir -p "$STUDY_DIR"

echo "Creating study materials for: $BOOK"

# Flashcards
echo "→ Generating flashcards..."
xsarena study generate flashcards "$BOOK" \
    --num 100 \
    --out "$STUDY_DIR/flashcards.md"

# Quiz
echo "→ Generating quiz..."
xsarena study generate quiz "$BOOK" \
    --num 50 \
    --out "$STUDY_DIR/quiz.md"

# Glossary
echo "→ Generating glossary..."
xsarena study generate glossary "$BOOK" \
    --out "$STUDY_DIR/glossary.md"

echo ""
echo "✓ Study materials created in: $STUDY_DIR"
ls -lh "$STUDY_DIR"
