# Content Transformation Workflows

## Workflow 1: Book → Study Package

**Input:** Completed book

```bash
BOOK="./books/roman_history.final.md"

# Flashcards
xsarena study generate flashcards "$BOOK" \
  --out study/flashcards.md

# Quiz
xsarena study generate quiz "$BOOK" \
  --num 100 \
  --out study/quiz.md

# Glossary
xsarena study generate glossary "$BOOK" \
  --out study/glossary.md

# Quick reference
xsarena run template quick_reference "$BOOK" \
  --out study/quick_ref.md
```

## Workflow 2: Topic → Multiple Formats

**One topic, many outputs:**

```bash
TOPIC="Machine Learning"

# 1. Main book
xsarena run book "$TOPIC" \
  --length very-long \
  --span book

# 2. Interactive textbook
export SUBJECT="$TOPIC"
xsarena run from-recipe recipes/interactive_textbook.yml

# 3. Quick reference
xsarena run from-recipe recipes/quick_reference.yml

# 4. Study aids
xsarena study generate flashcards "./books/${TOPIC}.md" --num 200
xsarena study generate quiz "./books/${TOPIC}.md" --num 50
```

## Workflow 3: Batch Generation

**File:** `scripts/batch_generate.sh`
```bash
#!/bin/bash
# Generate multiple books from topic list

while IFS= read -r topic; do
    echo "Generating: $topic"
    xsarena run book "$topic" \
        --length long \
        --span medium \
        --out "./books/${topic// /_}.md" \
        --follow
done < topics.txt
```

## Workflow 4: Iterative Development

```bash
# Step 1: Generate outline
xsarena run book "Topic" --plan --span medium

# Step 2: Review, then continue
xsarena run continue ./books/topic.final.md --span long

# Step 3: Add depth
xsarena run continue ./books/topic.final.md --span medium
```

## Workflow 5: Study System

**Master any subject:**

```bash
SUBJECT="Quantum Mechanics"

# 1. Overview
xsarena run book "$SUBJECT Overview" \
  --length standard \
  --span medium

# 2. Deep dive
xsarena run continue overview.md \
  --length very-long \
  --span book

# 3. Study materials
xsarena study generate flashcards deep_dive.md --num 300
xsarena study generate quiz deep_dive.md --num 100
xsarena study generate glossary deep_dive.md

# 4. Quick reference
xsarena run template quick_reference deep_dive.md
```
