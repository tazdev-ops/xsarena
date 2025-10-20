# Commands Cheatsheet

## Bridge and health
- Start bridge:
  - xsarena ops service start-bridge-v2
- Health:
  - curl http://127.0.0.1:5102/v1/health
- Quick smoke:
  - xsarena dev simulate "Sanity" --length standard --span medium

## Authoring (book)
- Dry-run:
  - xsarena run book "Subject" --dry-run
- Real run:
  - xsarena run book "Subject" --follow --length long --span book
- Continue:
  - xsarena run continue ./books/Your_Book.final.md --wait false

## Jobs
- List:
  - xsarena ops jobs ls
- Follow:
  - xsarena ops jobs follow JOB_ID
- Control:
  - xsarena ops jobs pause|resume|cancel JOB_ID
  - Hint:
    - xsarena ops jobs next JOB_ID "Continue with X"

## Study / Analysis
- xsarena study generate flashcards book.md --num 50
- xsarena analyze continuity book.md
- xsarena analyze coverage --outline outline.md --book book.md

## Snapshots (lean)
- Flat pack:
  - xsarena ops snapshot txt --preset ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map

## Settings
- Show:
  - xsarena settings show
- Normalize config:
  - xsarena settings config-check
