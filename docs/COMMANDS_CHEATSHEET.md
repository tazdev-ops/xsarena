# Commands Cheatsheet

<!-- This file is the source of truth for CLI usage; regenerate via scripts/gen_docs.sh -->

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
- Cleanup:
  - xsarena ops jobs gc --days 14 --yes

## Study / Analysis
- xsarena study generate flashcards book.md --num 50
- xsarena analyze continuity book.md
- xsarena analyze coverage --outline outline.md --book book.md

## Snapshots (three-tier system)
- Minimal (flat text for chatbot uploads):
  - xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map
  - Output: ~/repo_flat.txt
- Normal (zip for most use):
  - xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --zip
  - Output: ~/xsa_snapshot.zip
- Maximal (verbose debug report):
  - xsarena ops snapshot debug-report
  - Output: ~/xsa_debug_report.txt
- Note: All snapshot commands write to your home directory (~) by default. Use --out to override.

## Settings
- Show:
  - xsarena settings show
- Normalize config:
  - xsarena settings config-check
