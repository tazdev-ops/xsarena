# Snapshot Rulebook (Lean and Safe)

Principles
- Flat TXT for sharing, redaction ON by default.
- Verify before you share; fix fails by config (include/exclude/budgets), not code.
- Keep secrets out; treat verify as a gate.

Minimal snapshot (recommended)
1) Preflight:
   xsarena ops snapshot verify --mode author-core --max-per-file 180000 --total-max 2500000 \
     --fail-on oversize --fail-on disallowed --fail-on secrets
2) Produce:
   xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt
3) Postflight:
   xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected

Common fails → fixes
- oversize: lower max_per_file; add excludes; switch to ultra-tight.
- disallowed: add -X patterns or update policy; exclude books/**, review/**, .xsarena/** by default.
- secrets: xsarena ops health scan-secrets --path . ; fix; rebuild.