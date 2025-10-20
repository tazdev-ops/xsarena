# Snapshot Rulebook

Purpose
- Give the CLI agent a clear, repeatable way to produce minimal and maximal snapshots, verify them, and fix common issues when necessary—without bloating the codebase.

Principles
- Shareable by default: prefer a curated, flat, redacted “txt” snapshot for chatbot uploads.
- Config over code: tune includes/excludes and budgets via policy; don’t change the builder unless a bug blocks you.
- Verify before share: run a snapshot “health check” (preflight/postflight) to catch size, secrets, and path violations.
- Keep secrets safe: redaction on by default; use the verify gate to audit.

Snapshot Types
- Minimal (recommended for sharing/chatbots)
  - Use the curated txt flattener with strict size caps and a focused include set.
  - Redaction on; no repo map.
- Maximal (for deep debugging or archival)
  - Use the simple builder with a “tight” or “full” mode. Prefer .zip if very large.
  - Turn off extra context (git/jobs/manifests) unless you really need it.

Standard Policies (defaults; override via .xsarena/ops/snapshot_policy.yml)
- Disallow globs (preflight fail): books/**, review/**, .xsarena/**, tools/**, directives/** (unless you explicitly want directives)
- Required: README.md, pyproject.toml
- Budgets: max_per_file: 180000 bytes; total_max: 2500000 bytes (tune per use)
- Fail categories: oversize, disallowed, secrets

Agent SOP

A) Minimal snapshot (txt) — shareable
- Preflight:
  - xsarena ops snapshot verify --mode minimal --max-per-file 180000 --total-max 2500000 --disallow books/** --disallow review/** --disallow .xsarena/** --fail-on oversize --fail-on disallowed --fail-on secrets
  - If violations, follow “Fixes” below.
- Produce:
  - xsarena ops snapshot txt --preset ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map
- Postflight (optional):
  - xsarena ops snapshot verify --file repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on disallowed --redaction-expected

B) Maximal snapshot (zip) — debug/ops
- Preflight (dry-run is enough):
  - xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --dry-run
- Produce:
  - xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --zip
- Postflight (optional):
  - If you produced xsa_snapshot.txt instead of zip:
    - xsarena ops snapshot verify --file xsa_snapshot.txt --max-per-file 400000 --fail-on oversize --fail-on disallowed

Fixes: what to do when verify fails
- oversize (preflight)
  - Lower max_per_file and/or exclude big files; switch to txt mode; reduce preset or add excludes via policy.
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
- Minimal snapshot: repo_flat.txt exists; ≤ total_max bytes; no disallowed paths; no oversize files; no secrets; redaction markers present (if expected).
- Maximal snapshot: xsa_snapshot.zip exists; verify says OK (or at least no disallowed/oversize for your chosen thresholds).
