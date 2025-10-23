# Snapshot Rulebook (Flat, Safe, Verifiable)

Principles
- One-command flows; verify gates before/after; redaction on by default.
- Outputs in $HOME only; never commit snapshots; avoid recursion.

Policy (preflight)
- Create .xsarena/ops/snapshot_policy.yml:
  - disallow_globs: .git/**, venv/**, .venv/**, __pycache__/**, *.pyc, .pytest_cache/**, .mypy_cache/**, .ruff_cache/**, .cache/**, .xsarena/**, books/**, review/**, tests/**, examples/**, tools/**, scripts/**, pipelines/**, packaging/**, xsa_*snapshot*.*, repo_flat.txt, snapshot_chunks/**
  - require: ["README.md","pyproject.toml"]
  - max_per_file: 180000
  - total_max: 2500000
  - fail_on: ["secrets","oversize","disallowed","binary","missing_required"]

Flows

A) Flat (shareable, ultra-tight)
1) Preflight:
   xsarena ops snapshot verify --mode author-core --policy .xsarena/ops/snapshot_policy.yml --quiet
2) Produce:
   xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt --no-repo-map
3) Postflight:
   xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected --quiet

B) Pro debug bundle
- Produce:
  xsarena ops snapshot debug-report --out ~/xsa_debug_report.txt

Fixes (verify fail)
- oversize: lower max_per_file/total_max; add excludes; use ultra-tight.
- disallowed: add -X excludes or update the policy; re-run preflight.
- secrets: xsarena ops health scan-secrets --path . ; remove/rotate; rebuild.
- missing_required: ensure README.md/pyproject.toml present; re-run preflight.

Hygiene
- Clean old files (root + $HOME):
  - rm -f repo_flat.txt xsa_*snapshot*.txt situation_report.*.txt ; rm -rf snapshot_chunks/
  - rm -f ~/xsa_min_snapshot*.txt ~/xsa_snapshot_pro*.txt ~/situation_report.*.txt
- TTL sweeps: xsarena ops health sweep --dry | --apply

Exit codes
- 0 OK | 1 fail categories | 2 missing/invalid snapshot file
