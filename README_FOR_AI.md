# Start Here (For AIs + Humans)

Who we are
- Operator (human): "Medium" — sets priorities, owns decisions.
- Higher AI advisor: "Advisor" — plans, audits, writes docs, proposes changes.
- CLI AI agent: "Operator bot" — runs commands via shell (xsarena …), generates reports, applies small patches when asked.

What this project is
- XSArena: a local-first, bridge-first authoring and analysis studio for long-form content, with reproducible runs, safe resume, and lean snapshots for sharing.
- Project philosophy: secure-by-default bridge, single source of truth (Typer CLI), declarative prompt composition, deterministic jobs.

Your first moves (fast)
1) Read docs/COLLAB_PROTOCOL.md (roles + language)
2) Read docs/ARCHITECTURE.md (structure) and docs/OPERATIONS.md (bridge)
3) Smoke test (Unix): scripts/smoke.sh (or scripts/smoke.ps1 on Windows)
4) If snapshots are needed: docs/SNAPSHOT_RULEBOOK.md + docs/SNAPSHOT_RUNBOOK.md
5) For machine control: docs/C2_PROTOCOL.md + run python3 scripts/c2_run.py --once

Non-interactive contract (for agents)
- Only run shell commands; don't import modules directly.
- Set NO_COLOR=1; RICH_NO_COLOR=1.
- Pass explicit flags to avoid prompts (e.g., --resume/--overwrite; --wait false).
- Don't pass large content via argv — write to files and pass paths.

Where to get the full picture
- docs/PROJECT_CHARTER.md — nature, goals, scope, non-goals
- docs/COLLAB_PROTOCOL.md — roles, language, decision rules, escalation
- docs/JARGON.md — shared shortcuts and terms
- docs/ONBOARDING_AI.md — step-by-step for a new AI session
- docs/ARCHITECTURE.md — structure map
- docs/OPERATIONS.md — bridge + health; troubleshooting
- docs/USAGE.md — common tasks
- docs/AGENT_RULEBOOK.md — safe operating procedures for the agent
- docs/SNAPSHOT_RULEBOOK.md — how to make minimal/maximal snapshots + verify
- docs/C2_PROTOCOL.md — task queue + status heartbeat

Pin this file in snapshots (or merge into README.md) so any new session can continue immediately.
