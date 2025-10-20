# Snapshot Runbook

Minimal (txt) — recommended
- Preflight verify:
  xsarena ops snapshot verify --mode minimal --max-per-file 180000 --total-max 2500000 --disallow books/** --disallow review/** --disallow .xsarena/** --fail-on oversize --fail-on disallowed --fail-on secrets
- Produce:
  xsarena ops snapshot txt --preset ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map
- Postflight verify:
  xsarena ops snapshot verify --file repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on disallowed --redaction-expected

Maximal (zip) — ops/debug
- Dry-run plan:
  xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --dry-run
- Produce:
  xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --zip
- Optional postflight (text manifests only):
  xsarena ops snapshot verify --file xsa_snapshot.txt --max-per-file 400000 --fail-on oversize --fail-on disallowed

Lean mode suggestions (config-only; edit .snapshot.toml)
- Define [modes.tight] to whitelist only core orchestrator/CLI files and exclude everything else (docs/examples/tests/tools/review/books/.xsarena/**).
- Use " --mode tight" with write to keep outputs bounded.

Common pitfalls
- Passing giant directories under include (e.g., src/**) without excludes.
- Running write with git/jobs/manifest context on (outputs balloon).
- Disabling redaction for txt (secrets risk).
- Copying repo_flat.txt/xsa_snapshot.* into git (add to .gitignore).
