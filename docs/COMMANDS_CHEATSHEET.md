# XSArena Commands Cheatsheet

## Bridge + Health
- Start bridge: xsarena ops service start-bridge-v2
- Health: curl $(xsarena settings config-show | sed -n 's/.*Base URL: //p')/health
- Capture IDs (modern): xsarena unified-settings capture-ids
  - or: xsarena settings config-capture-ids

## Authoring
- Book (follow to completion):
  - xsarena run book "Subject" --length long --span book --follow
- Continue:
  - xsarena run continue ./books/Your_Book.final.md --follow
- Styles (session toggles):
  - xsarena author style-narrative on
  - xsarena author style-nobs on
  - xsarena author style-reading on

## Interactive
- Start cockpit: xsarena interactive start
- Handy /commands: /prompt.show, /prompt.list, /out.minchars 4500, /cont.mode anchor, /repeat.warn on

## Jobs
- List: xsarena ops jobs ls
- Follow: xsarena ops jobs follow JOB_ID
- Controls: xsarena ops jobs pause|resume|cancel JOB_ID
- Hint: xsarena ops jobs next JOB_ID "Continue with X"

## Snapshots (flat, lean)
- Create: xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt
- Verify: xsarena ops snapshot verify --file ~/repo_flat.txt --fail-on oversize --fail-on secrets --redaction-expected

## Study + Analyze
- Flashcards: xsarena study generate flashcards ./books/book.md --num 50
- Continuity: xsarena analyze continuity ./books/book.md
- Coverage: xsarena analyze coverage --outline outline.md --book ./books/book.md

## Settings
- Show: xsarena settings show
- Validate: xsarena settings config-check