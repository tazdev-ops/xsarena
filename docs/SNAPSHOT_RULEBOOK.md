# Snapshot Rulebook

Purpose
- Give the CLI agent a clear, repeatable way to produce minimal, normal, and maximal snapshots, verify them, and fix common issues when necessary—without bloating the codebase.

Principles
- Shareable by default: prefer a curated, flat, redacted "create" snapshot for chatbot uploads.
- Config over code: tune includes/excludes and budgets via policy; don't change the builder unless a bug blocks you.
- Verify before share: run a snapshot "health check" (preflight/postflight) to catch size, secrets, and path violations.
- Keep secrets safe: redaction on by default; use the verify gate to audit.
- Three-tier system: minimal (create), normal (write), maximal (debug-report) for different use cases.

Snapshot Types
- Minimal (flat text for chatbot uploads) - xsarena ops snapshot create
  - Use the curated txt flattener with strict size caps and a focused include set.
  - Redaction on; no repo map.
  - Output: ~/repo_flat.txt
- Normal (zip for most use) - xsarena ops snapshot write
  - Use the simple builder with a "tight" mode. Prefer .zip format.
  - Turn off extra context (git/jobs/manifests) unless you really need it.
  - Output: ~/xsa_snapshot.zip (when using --zip)
- Maximal (verbose debug report) - xsarena ops snapshot debug-report
  - Use the pro builder for comprehensive debugging information.
  - Includes system info, git status, job logs, and full file manifest.
  - Output: ~/xsa_debug_report.txt

Standard Policies (defaults; override via .xsarena/ops/snapshot_policy.yml)
- Disallow globs (preflight fail): books/**, review/**, .xsarena/**, tools/**, directives/** (unless you explicitly want directives)
- Required: README.md, pyproject.toml
- Budgets: max_per_file: 180000 bytes; total_max: 2500000 bytes (tune per use)
- Fail categories: oversize, disallowed, secrets

Agent SOP

A) Minimal (flat text for chatbot uploads)
- Preflight:
  - xsarena ops snapshot verify --mode minimal --max-per-file 180000 --total-max 2500000 --disallow books/** --disallow review/** --disallow .xsarena/** --fail-on oversize --fail-on disallowed --fail-on secrets
  - If violations, follow "Fixes" below.
- Produce:
  - xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map
  - Output: ~/repo_flat.txt
- Postflight (optional):
  - xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on disallowed --redaction-expected

B) Normal (zip for most use)
- Preflight (dry-run is enough):
  - xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --dry-run
- Produce:
  - xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --zip
  - Output: ~/xsa_snapshot.zip
- Note: Postflight verify works on flat text outputs (create). For zip/debug-report, use preflight verify before generating.

C) Maximal (verbose debug report)
- Produce:
  - xsarena ops snapshot debug-report
  - Output: ~/xsa_debug_report.txt
- Note: No postflight verify needed for debug reports; use preflight verify if needed.

Fixes: what to do when verify fails
- oversize (preflight)
  - Lower max_per_file and/or exclude big files; switch to create mode; reduce preset or add excludes via policy.
- disallowed
  - Add explicit exclude globs in the verify/run command or snapshot policy.
- secrets
  - Run xsarena ops health scan-secrets --path .
  - Remove secrets and rebuild; keep redaction on for txt.
- missing_required
  - Ensure README.md and pyproject.toml exist; include them explicitly if your mode excludes them.

When (and how) to propose code fixes (only if truly necessary)
- Prefer config/policy changes first (modes, budgets, include/exclude).
- If a bug blocks usage (e.g., TOML parsing crash), see docs/SNAPSHOT_FIX_PLAYBOOK.md for surgical patches.

Acceptance Criteria
- Minimal snapshot: ~/repo_flat.txt exists; ≤ total_max bytes; no disallowed paths; no oversize files; no secrets; redaction markers present (if expected).
- Normal snapshot: ~/xsa_snapshot.zip exists; verify says OK (or at least no disallowed/oversize for your chosen thresholds).
- Maximal snapshot: ~/xsa_debug_report.txt exists and contains comprehensive system information.
- All snapshot commands write to your home directory (~) by default. Use --out to override.
