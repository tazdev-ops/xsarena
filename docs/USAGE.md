# XSArena Usage Guide

A practical guide to common tasks with examples.

## Install and quick start
- Ensure Python ≥ 3.9 and Firefox (+ Tampermonkey userscript) available.
- Install:
  - pip install -e ".[dev]"  (or your preferred method)
- Start the bridge:
  - xsarena ops service start-bridge-v2
  - Open your model page in Firefox and add #bridge=5102 (or your configured port)
  - Look for "Userscript connected" in bridge logs

## First-run checklist (healthy defaults)
- Show current settings:
  - xsarena settings show
- Normalize config:
  - xsarena settings config-check
- Optional: capture bridge IDs (if feature enabled in your build):
  - xsarena settings config-capture-ids

## Author a book (dry-run and real)
- Dry-run (prints resolved spec and system prompt):
  - xsarena run book "Subject" --dry-run
- Real run (submit and follow to completion):
  - xsarena run book "Subject" --follow --length long --span book
- Resume / overwrite behavior:
  - If a job exists for the same output path, you can specify:
    - --resume to continue
    - --overwrite to start fresh

## Continue an existing file
- xsarena run continue ./books/Your_Book.final.md --length standard --span medium --wait false

## Interactive REPL (with /command support)
- xsarena interactive start
  - /run book "New Subject" --dry-run
  - /run --help
  - /exit

## Analyze a manuscript
- Continuity:
  - xsarena analyze continuity ./books/Your_Book.final.md
- Coverage vs. outline:
  - xsarena analyze coverage --outline outline.md --book ./books/Your_Book.final.md

## Study artifacts
- Flashcards:
  - xsarena study generate flashcards ./books/Your_Book.final.md --num 50
- Quiz:
  - xsarena study generate quiz ./books/Your_Book.final.md --num 20
- Glossary:
  - xsarena study generate glossary ./books/Your_Book.final.md

## Translation (EPUB → Markdown → translated)
- Convert:
  - pandoc "input.epub" -t markdown -o book.md --wrap=none
- Split chapters:
  - xsarena utils tools export-chapters book.md --out ./chapters
- Translate with Bilingual mode (example Python helper recommended):
  - See docs/WORKFLOWS.md (EPUB translation pipeline)

## Jobs: inspect and control
- List jobs:
  - xsarena ops jobs ls
- Show one job:
  - xsarena ops jobs summary JOB_ID
- Follow logs:
  - xsarena ops jobs follow JOB_ID
- Controls:
  - xsarena ops jobs pause|resume|cancel JOB_ID
  - Send next-hint:
    - xsarena ops jobs next JOB_ID "Continue with X"

## Snapshots (lean, upload-ready)
- Flat pack (tight):
  - xsarena ops snapshot txt --preset ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map
- Builder (custom mode you defined in .snapshot.toml):
  - xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --dry-run
