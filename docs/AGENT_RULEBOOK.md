# XSArena Agent Rulebook

Purpose
- A lean operating playbook for the CLI agent (and humans) that keeps changes safe, reversible, and verifiable. It defines: what to check before/after, default procedures, and guardrails.

Core principles
- Single source of truth: reuse the Typer CLI. Don't build side routers or ad-hoc wrappers.
- Safe-by-default: local bridge, constant-time token checks, no secrets in logs, redaction on.
- Small and reversible: minimal patches, clear rollback, prefer branches for risky changes.
- Idempotent ops: re-running shouldn't break the project (e.g., no duplicate merges).
- Verify outcomes: preflight before doing; postflight after doing; run a minimal smoke.

Preflight (before any change)
- Git/workspace
  - Working tree clean or on a topic branch
  - No uncommitted critical files (code/docs)
- Config & bridge
  - xsarena settings config-check → base URL normalized to http://127.0.0.1:5102/v1
  - If the task needs the bridge: ensure it's running and userscript is connected
- Inputs availability
  - Required files exist (recipes, chapters, directives, etc.)
  - For snapshot tasks: consider running preflight verify (see Verify section)

Standard operating procedures (SOP)

SOP A: Author a book (real run)
- Preflight
  - xsarena run book "Subject" --dry-run (sanity)
  - If an out file already exists, decide resume/overwrite; be explicit
- Execute
  - xsarena run book "Subject" --length long --span book --follow
- Postflight
  - Confirm .xsarena/jobs/<id>/events.jsonl exists; state DONE (or actionable error)
  - If intended to share a snapshot later, run "Verify" (below)

SOP B: Continue an existing book
- Preflight
  - Ensure file exists; optionally run analyze continuity on last chapter
- Execute
  - xsarena run continue ./books/Your_Book.final.md --length standard --span medium --wait false
- Postflight
  - Confirm no duplication at the top; check events show one or more chunk_done

SOP C: Translate EPUB (EN → XX)
- Preflight
  - Convert to Markdown and split: pandoc input.epub -t markdown -o book.md --wrap=none; xsarena utils tools export-chapters book.md --out ./chapters
- Execute
  - Use the Python helper (docs/USAGE.md) to translate chunks per chapter, preserving Markdown
- Postflight
  - Spot-check 1–2 chapters for heading/list/code formatting
  - Optional: rebuild small EPUB sample and preview

SOP D: Analysis gate before release
- Execute
  - xsarena analyze continuity ./books/Your_Book.final.md
  - xsarena analyze coverage --outline outline.md --book ./books/Your_Book.final.md
- Postflight
  - If drift/coverage fail thresholds (team policy), fix and re-run

SOP E: Rules merge (Python-only)
- Execute
  - Concatenate directives/_rules/sources/*.md → directives/_rules/rules.merged.md
- Postflight
  - If file changed, mark in commit; treat as build artifact (consider .gitignore)

SOP F: Docs refresh
- Execute
  - xsarena docs gen-help
- Postflight
  - Ensure docs/_help_root.txt exists; commit updated help files

Verify (use before sharing—or after changes that affect build content)
- Preflight verify a would-be snapshot
  - xsarena ops snapshot verify --mode minimal --max-per-file 180000 --total-max 2500000 --disallow books/** --disallow review/** --disallow .xsarena/** --fail-on oversize --fail-on disallowed
  - Fail if any violations hit team policy (.snapshot.policy.yml or agent_policy.yml)
- Postflight verify a flat pack
  - xsarena ops snapshot verify --file repo_flat.txt --max-per-file 180000 --fail-on oversize,disallowed --redaction-expected

Postflight smoke (fast, 3–5 min)
- Optional: scripts/smoke.sh (Unix) or scripts/smoke.ps1 (Windows)
  - Simulate + dry-run + docs gen-help + optional snapshot verify
  - OK status = no tracebacks; bridge health OK; expected files present

Guardrails (do / don't)
- Do
  - Work off Typer CLI; reuse /command dispatcher for REPL
  - Keep redaction on for snapshots; run verify before sharing
  - Use constant-time token checks; bind bridge to 127.0.0.1 by default
  - Add "XSA-EPHEMERAL ttl=Xd" headers for short-lived scripts (e.g., in review/)
- Don't
  - No shell=True in subprocess calls
  - Don't change snapshot utility code casually (use verify gate instead)
  - Don't commit secrets or snapshot artifacts; scan with ops health scan-secrets

Escalation & rollback
- If a command fails repeatedly:
  - Capture .xsarena/jobs/<id>/events.jsonl and the error chunk (user_message + error_code)
  - Open a ticket (review/agent_ticket_<ts>.md): steps to reproduce, observed/expected, environment, minimal patch idea
- Risky changes:
  - Use a topic branch; small patches; single-responsibility commits; fall back by reverting commit or switching branch

Shortcuts (macros)
- Consider adding these:
  - xsarena utils macros add bridge-up 'xsarena ops service start-bridge-v2'
  - xsarena utils macros add connect 'xsarena ops service connect'
  - xsarena utils macros add run-dry 'xsarena run book "{SUBJECT}" --dry-run'
  - xsarena utils macros add snap-txt 'xsarena ops snapshot txt --preset ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map'

Machine mode (external agent)
- Always set NO_COLOR=1, RICH_NO_COLOR=1.
- Always choose non-interactive flags: --resume/--overwrite, --wait false.
- Don't pass big content via argv; write to file and pass a path.
- Preflight: xsarena settings config-check; if bridge needed, ensure /v1/health ok.
- Postflight: scripts/smoke.sh on Unix (or smoke.ps1 on Windows) if time allows.
- For snapshot sharing: use ops snapshot verify preflight to enforce budgets.
- If a command fails: capture .xsarena/jobs/<id>/events.jsonl; open a ticket (review/agent_ticket_<ts>.md).

Reference docs
- See docs/USAGE.md (tasks), docs/OPERATIONS.md (bridge & health), docs/TROUBLESHOOTING.md (common failures), docs/SMOKE_TEST.md (quick check).

Keep it lean
- This rulebook is short by design. It defines the "what and when," not a new layer of logic. The Typer CLI remains the source of truth for "how."
