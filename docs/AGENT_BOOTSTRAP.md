You are a command-mode operator. Rules:
- Set NO_COLOR=1 and RICH_NO_COLOR=1.
- Non-interactive only (use --resume/--overwrite, --wait false).
- Don't pass big text via argv; write to files and pass paths.

Do this:
1) xsarena settings config-check
2) xsarena ops service start-bridge-v2 &
   Poll until curl -s http://127.0.0.1:5102/v1/health shows "status":"ok".
3) Create .xsarena/ops/c2_queue.json with tasks:
   - project_map → review/reports/PROJECT_MAP.md
   - commands_index → review/reports/COMMANDS_INDEX.md
   - config_show → review/reports/SETTINGS.md
   - snapshot_preflight_verify (mode=minimal, max_per_file=180000, total_max=2500000, disallow: books/**, review/**, .xsarena/**; fail_on: oversize, disallowed, secrets)
4) python3 scripts/c2_run.py --once
5) Print: .xsarena/ops/c2_status.json and ls review/reports

If any command fails, paste stderr and propose the smallest fix (config/policy over code).
