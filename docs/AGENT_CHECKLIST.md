# Agent Checklist (Do-this list)

Before (preflight)
- xsarena settings config-check → normalized base URL "…/v1"
- If run needs bridge: xsarena ops service start-bridge-v2 and /v1/health is ok
- Ensure inputs exist (book.md, chapters/, recipe.json, etc.)

Do it
- Authoring: xsarena run book "Subject" --follow [--resume|--overwrite]
- Continue: xsarena run continue ./books/Your_Book.final.md --wait false
- Translate: use the Python helper for chunked Markdown
- Analysis: xsarena analyze continuity / coverage
- Rules merge: Python-only concat of sources/*.md
- Docs: xsarena docs gen-help

After (postflight)
- Jobs: xsarena ops jobs ls; job state DONE
- Optional smoke: scripts/smoke.sh (Unix) / scripts/smoke.ps1 (Windows)
- (If sharing) Verify snapshot plan or file:
  - Preflight: xsarena ops snapshot verify --mode minimal … (budgets, disallow)
  - Postflight: xsarena ops snapshot verify --file repo_flat.txt …

If failure
- Save .xsarena/jobs/<id>/events.jsonl
- Open ticket: review/agent_ticket_<ts>.md with repro, expected, observed, environment, and minimal patch idea
- Prefer small, reversible fixes

Notes
- Use macros to speed up common flows (see docs/SHORTCUTS.md)
- Never commit secrets or snapshot artifacts; scan with xsarena ops health scan-secrets

Why this is professional
- It keeps the agent consistent, safe, and predictable.
- It encodes defaults and guardrails without adding new runtime complexity.
- It enables quick verification (smoke + verify) and clean escalation when something fails.
