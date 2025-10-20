# ONE ORDER — Snapshot Reform (clear, safe, repeatable)

Goal
- Make snapshots one-command, predictable, and safe to share.
- Enforce verify gates (size, disallowed paths, secrets, redaction).
- Keep outputs out of the repo; no churn, no recursion.

What to adopt now (no code changes required)
- Use the built-in snapshot commands only.
- Standardize on two modes: ultra-tight (share) and author-core (dev).
- Always preflight with verify before producing; postflight-verify the built file.
- Keep outputs in $HOME; never commit snapshots.
- Use a single policy file to avoid per-invocation flag sprawl.

## A) Presets and budgets (canonical)
- ultra-tight
  - total_max: 2,500,000 bytes
  - max_per_file: 180,000 bytes
  - redaction: on
  - repo map: off
  - purpose: upload to chatbots
- author-core
  - total_max: 4,000,000 bytes
  - max_per_file: 200,000 bytes
  - redaction: on
  - repo map: on/off (optional)
  - purpose: dev/handoff

## B) Disallowed paths (always)
- .git/**, venv/**, .venv/**, __pycache__/**, *.pyc, .pytest_cache/**, .mypy_cache/**, .ruff_cache/**, .cache/**
- .xsarena/**, books/**, review/**, tests/**, examples/**
- tools/**, scripts/**, pipelines/**, packaging/**
- xsa_*snapshot*.*, repo_flat.txt, snapshot_chunks/**

## C) Required files (preflight must assert)
- README.md
- pyproject.toml

## D) Preflight policy file (drop-in)
Create .xsarena/ops/snapshot_policy.yml with:
- disallow_globs: the list in (B)
- require: ["README.md","pyproject.toml"]
- max_per_file: 180000
- total_max: 2500000
- fail_on: ["secrets","oversize","disallowed","binary","missing_required"]

Example:
- disallow_globs:
  - ".git/**"
  - "venv/**"
  - ".venv/**"
  - "__pycache__/**"
  - ".pytest_cache/**"
  - ".mypy_cache/**"
  - ".ruff_cache/**"
  - ".cache/**"
  - "*.pyc"
  - ".xsarena/**"
  - "books/**"
  - "review/**"
  - "tests/**"
  - "examples/**"
  - "tools/**"
  - "scripts/**"
  - "pipelines/**"
  - "packaging/**"
  - "xsa_*snapshot*.*"
  - "repo_flat.txt"
  - "snapshot_chunks/**"
- require: ["README.md", "pyproject.toml"]
- max_per_file: 180000
- total_max: 2500000
- fail_on: ["secrets","oversize","disallowed","binary","missing_required"]

## E) Preflight-before-produce (always run)
- Minimal surface (ultra-tight policy):
  - xsarena ops snapshot verify --mode author-core --policy .xsarena/ops/snapshot_policy.yml --quiet
- If FAIL, fix per section G; if OK, proceed to production.

## F) Produce + Postflight (two standard flows)

1) Shareable (ultra-tight, txt)
- Create:
  - xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt --no-repo-map
- Verify the file (postflight):
  - xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected --quiet
- Deliverable: ~/repo_flat.txt

2) Debug bundle (pro)
- Create:
  - xsarena ops snapshot debug-report --out ~/xsa_debug_report.txt
- Optional verify (if you export a flat file):
  - xsarena ops snapshot verify --file ~/xsa_debug_report.txt --max-per-file 400000 --fail-on oversize --fail-on secrets --quiet
- Deliverable: ~/xsa_debug_report.txt

## G) If verify fails (playbook)
- oversize:
  - Lower max_per_file or total_max; switch to ultra-tight; add -X excludes temporarily.
- disallowed:
  - Add explicit excludes to policy, or pass -X on the verify prefight; re-run preflight.
- secrets:
  - xsarena ops health scan-secrets --path . ; remove/rotate; keep redaction on; rebuild.
- missing_required:
  - Add README.md/pyproject.toml; re-run preflight.
- binary:
  - Exclude offending binaries (policy); or let debug-report handle as metadata.

## H) Cleanup discipline (prevent recursion and drift)
- Before any snapshot/report:
  - Remove stale files:
    - Project root: repo_flat.txt, xsa_*snapshot*.txt(.tar.gz), situation_report*.txt/part*
    - snapshot_chunks/ contents (remove dir if empty)
    - $HOME: xsa_min_snapshot*.txt, xsa_snapshot_pro*.txt(.tar.gz), situation_report.*.txt/part*
- Ephemeral TTL sweeps:
  - xsarena ops health sweep --dry (audit)
  - xsarena ops health sweep --apply (scheduled)
- Never commit snapshots or job artifacts:
  - Ensure .gitignore covers: snapshot_chunks/, xsa_min_snapshot*.txt, review/, .xsarena/tmp/

## I) CI (optional but recommended)
- Add a preflight verify job (no secrets, no oversize, required present) on PRs:
  - xsarena ops snapshot verify --mode author-core --policy .xsarena/ops/snapshot_policy.yml --quiet
- Fail CI if verify fails (exit code 1/2).

## J) Operator macros (fast paths)
- Ultra-tight quick:
  - xsarena ops snapshot verify --mode author-core --policy .xsarena/ops/snapshot_policy.yml --quiet && \
    xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt --no-repo-map && \
    xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected --quiet
- Pro debug:
  - xsarena ops snapshot debug-report --out ~/xsa_debug_report.txt

## K) Acceptance checklist (must tick)
- Preflight verify OK (exit 0) with policy
- No secrets, no disallowed paths, no oversize
- Postflight verify OK (for the produced flat pack)
- Outputs reside in HOME (not the repo)
- Redaction markers present when expected
- No snapshot artifacts committed; .gitignore clean
