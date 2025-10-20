# Creative Applications

## 1. Personal Knowledge Base

Transform notes into organized knowledge:

```bash
# Synthesize notes
xsarena author ingest-synth my_notes.md synthesis.md

# Expand into reference
xsarena run book "Personal Knowledge: ${TOPIC}" \
  --extra-file synthesis.md \
  --profile reference
```

## 2. Learning Any Subject Fast

```bash
# Generate book
xsarena run book "Deep Learning" \
  --length very-long \
  --span book

# Study aids
xsarena study generate flashcards book.md --num 200
xsarena study generate quiz book.md --num 50
xsarena study generate glossary book.md
```

## 3. Content Repurposing

One source → multiple formats:

```bash
# Article from transcript
xsarena run template podcast_to_article transcript.txt

# Thread for social
xsarena run template twitter_thread transcript.txt

# Blog series
xsarena run template blog_series transcript.txt
```

## 4. Writing Assistant

Collaborative writing partner:

```bash
# Generate outline
xsarena run from-plan --subject "Book Idea"

# Write with your voice
xsarena author style-capture your_sample.md --out style.md
xsarena author style-apply style.md "Chapter 1"
```

## 5. Course Material Generator

```bash
# Textbook
xsarena run from-recipe recipes/interactive_textbook.yml

# Study aids
xsarena study generate flashcards textbook.md --num 200
xsarena study generate quiz textbook.md --num 100
```

## 6. Comparative Analysis

```bash
# Compare anything
xsarena run template comparison_guide "React vs Vue vs Angular"
```

## 7. Documentation Generator

```bash
# Getting started
xsarena run template getting_started_guide overview.md

# API reference
xsarena run template api_reference structure.md

# Troubleshooting
xsarena run template troubleshooting issues.md
```

## 8. Story Development

```bash
# World bible
xsarena run book "Fantasy World: ${NAME}" \
  --profile memoir_personal_narrative

# Character profiles
xsarena run template character_profile "Main Character"

# Timeline
xsarena run template timeline_narrative "Historical Events"
```

## 9. Personal Documentation

```bash
# Memoir
xsarena run book "My Journey: ${PERIOD}" \
  --profile memoir_personal_narrative

# Travel journal
xsarena run from-recipe recipes/travel_guide.yml

# Recipe collection
xsarena run from-recipe recipes/cookbook.yml
```

## 10. Interview Preparation

```bash
# Research
xsarena run book "Deep Dive: ${TOPIC}"

# Question bank
xsarena run template interview_questions background.md
```
