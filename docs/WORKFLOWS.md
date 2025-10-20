# Practical Workflows

## A) Author a long-form manual (book)
- Dry-run to inspect the composed prompt:
  - xsarena run book "Subject" --dry-run
- Run:
  - xsarena run book "Subject" --length long --span book --follow
- Resume options:
  - --resume  continue where you left off
  - --overwrite  start fresh even if a resumable job exists

## B) Translate an EPUB
- Convert EPUB → Markdown:
  - pandoc input.epub -t markdown -o book.md --wrap=none
- Split chapters:
  - xsarena utils tools export-chapters book.md --out ./chapters
- Translate chapters (use a small Python helper for chunking and Markdown preservation)
  - See "EPUB translation pipeline" in docs/USAGE.md for a ready-made snippet
- Rebuild EPUB:
  - pandoc translated/*.md -o output-translated.epub --metadata title="Title (Translated)"

## C) Study pack from a manuscript
- Flashcards:
  - xsarena study generate flashcards ./book.md --num 50
- Quiz:
  - xsarena study generate quiz ./book.md --num 20
- Glossary:
  - xsarena study generate glossary ./book.md

## D) Analysis gate before release
- Coverage vs outline:
  - xsarena analyze coverage --outline outline.md --book ./book.md
- Continuity:
  - xsarena analyze continuity ./book.md
- Optional density checks:
  - xsarena analyze readtime ./book.md --wpm 200

## E) Interactive cockpit
- xsarena interactive start
  - /run book "Title" --dry-run
  - /help  /exit
