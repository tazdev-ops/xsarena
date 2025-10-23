# Snapshot Policy

## Purpose
A snapshot is a text-only representation of the project for debugging and sharing with higher AI systems. It includes tree structure and relevant files while excluding generated content and sensitive data.

## Standard Snapshot Content
- Source code (src/, directives/, data/, playbooks/, recipes/)
- Configuration files (pyproject.toml, README.md, LICENSE, etc.)
- Project structure information
- Excludes: books/, .git/, __pycache__/, build artifacts, large/binary files

## Standard Snapshot Command
```
xsarena snapshot run
```

For chunked output (recommended for large projects):
```
xsarena snapshot run --chunk
```

## SNAPSHOT+JOBS Extension
When debugging specific job issues, include minimal job context:

**Include on demand**: `.xsarena/jobs/<job_id>/events.jsonl` and `job.json`
**Do not include**: Full section outputs or other large artifacts unless specifically requested

**Command**:
```
# Create standard snapshot + job context
xsarena snapshot run
# Then manually include job.json and events.jsonl if needed for debugging
```

## Quality Checklist
- Includes: src/, directives/, data/, playbooks/, recipes/, top-level config
- Excludes: books/, .git/, __pycache__/, build/dist/node_modules/, large/binary files
- Files readable; chunk sizes reasonable; no stray footer/prompts in chunks
- If snapshot is missing expected files: ensure you ran from project root

## Troubleshooting
- Empty or tiny snapshot: rerun from project root
- Strange chunk footers: use the built-in chunker with --chunk flag
- Sensitive data: if secrets appear, re-run with appropriate redaction

## JobSpec-First Integration
When debugging JobSpec-related issues, ensure your snapshot includes:
- recipes/ directory (for JobSpec files)
- .xsarena/jobs/<job_id>/job.json (for job configuration)
- .xsarena/jobs/<job_id>/events.jsonl (for execution events)
- src/xsarena/core/jobs2.py (for runner implementation)# Hygiene Protocol (Safe Cleanup)

## Dry run (list only):
- `find . -name "__pycache__" -type d`
- `find . -name "*.pyc"`
- `find . -name ".DS_Store"`

## Delete (ask first):
- `timeout 15s find . -name "__pycache__" -type d -exec rm -rf {} +`
- `timeout 15s find . -name "*.pyc" -delete`
- `rm -rf .ruff_cache .pytest_cache`
- `find . -name ".DS_Store" -delete`

## Never delete:
- books/, .xsarena/jobs/, snapshot.txt, snapshot_chunks/

## After cleanup:
- `xsarena snapshot run` (quick)
- `xsarena doctor env` (quick)

## Modularization Decisions (RunSpecV2 Era)

Why
- Improve testability, reduce file sizes, and prevent cross-layer coupling.

Decisions
- Bridge handlers split into config_loaders/guards/streams; handlers are routes only.
- Interactive cockpit split into controllers (prompt/jobs/config/checkpoint); interactive_session.py is a thin router.
- Jobs error taxonomy isolated in jobs/errors.py; JobManager/JobV3 split for clarity.
- Snapshot helpers deduped under utils/snapshot; flatpack_txt consumes shared helpers.

Guardrails
- Modules ≤ 500 LOC; functions ≤ 80 LOC.
- No cross-layer imports (bridge_v2 → cli; cli → transports).
- After CLI changes, run: xsarena docs gen-help and commit help files.

Back-out Plan
- Keep each refactor in a small PR; behavior unchanged by tests.
- Revert a PR cleanly if regressions appear; add a test that would have caught it.
