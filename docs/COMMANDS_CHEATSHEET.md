# Commands Cheatsheet

## Bridge + Health
- Start bridge:
  - xsarena ops service start-bridge-v2
- Health:
  - curl $(xsarena settings config-show | sed -n 's/.*Base URL: //p')/health
- Capture IDs:
  - xsarena unified-settings capture-ids

## Authoring
- Book:
  - xsarena run book "Subject" --length long --span book --follow
- Continue:
  - xsarena run continue ./books/Your_Book.final.md --follow
- Styles:
  - xsarena author style-narrative on
  - xsarena author style-nobs on
  - xsarena author style-reading on

## Interactive
- xsarena interactive start
- /prompt.show | /prompt.list | /prompt.style on|off <narrative|no_bs|compressed|bilingual>
- /out.minchars 4500 | /cont.mode anchor | /cont.anchor 360 | /repeat.warn on

## Jobs
- List/summary:
  - xsarena ops jobs ls
  - xsarena ops jobs summary JOB_ID --json
- Follow:
  - xsarena ops jobs follow JOB_ID
- Control:
  - xsarena ops jobs pause|resume|cancel JOB_ID
- Next hint:
  - xsarena ops jobs next JOB_ID "Continue with X"

## Snapshots
- Preflight:
  - xsarena ops snapshot verify --mode author-core --policy .xsarena/ops/snapshot_policy.yml --quiet
- Flat (share):
  - xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt --no-repo-map
- Postflight:
  - xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected

## Study & Analyze
- Flashcards:
  - xsarena study generate flashcards ./books/book.md --num 50
- Continuity:
  - xsarena analyze continuity ./books/book.md
- Coverage:
  - xsarena analyze coverage --outline outline.md --book ./books/book.md

## Settings
- Show / validate:
  - xsarena settings show
  - xsarena settings config-check
