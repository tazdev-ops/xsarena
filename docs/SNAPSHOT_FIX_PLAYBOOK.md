# Snapshot Fix Playbook & Deprecation Notes

## Legacy Snapshot Scripts (DEPRECATED as of Snapshot Reform 2025-10-21)

The following legacy snapshot scripts are now deprecated in favor of the new standardized `xsarena ops snapshot` commands:

- `create_snapshot.sh` - Shell script for creating snapshots
- `simple_snapshot.py` - Python script for basic snapshots  
- `tools/flatpack_txt.py` - Python utility for flat pack creation
- `scripts/repo_snapshot.sh` - Repository snapshot script

### Migration Path
All functionality from these scripts is now available through the new standardized commands:

1. **Shareable (ultra-tight, txt)**
   - Preflight: `xsarena ops snapshot verify --mode author-core --policy .xsarena/ops/snapshot_policy.yml --quiet`
   - Produce: `xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt --no-repo-map`
   - Postflight: `xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected --quiet`

2. **Debug bundle (pro)**
   - Produce: `xsarena ops snapshot debug-report --out ~/xsa_debug_report.txt`

### TTL Status
- These legacy scripts are marked as **XSA-EPHEMERAL ttl=7d**
- They will be removed from the repository in a future release
- All new snapshot workflows should use the `xsarena ops snapshot` commands exclusively

### If verify fails (playbook)
- **oversize**: Lower max_per_file or total_max; switch to ultra-tight; add -X excludes temporarily.
- **disallowed**: Add explicit excludes to policy, or pass -X on the verify prefight; re-run preflight.
- **secrets**: `xsarena ops health scan-secrets --path .` ; remove/rotate; keep redaction on; rebuild.
- **missing_required**: Add README.md/pyproject.toml; re-run preflight.
- **binary**: Exclude offending binaries (policy); or let debug-report handle as metadata.

## Cleanup discipline (prevent recursion and drift)
- Before any snapshot/report:
  - Remove stale files:
    - Project root: repo_flat.txt, xsa_*snapshot*.txt(.tar.gz), situation_report*.txt/part*
    - snapshot_chunks/ contents (remove dir if empty)
    - $HOME: xsa_min_snapshot*.txt, xsa_snapshot_pro*.txt(.tar.gz), situation_report.*.txt/part*
- Ephemeral TTL sweeps:
  - `xsarena ops health sweep --dry` (audit)
  - `xsarena ops health sweep --apply` (scheduled)
- Never commit snapshots or job artifacts:
  - Ensure .gitignore covers: snapshot_chunks/, xsa_min_snapshot*.txt, review/, .xsarena/tmp/