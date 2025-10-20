# Command & Control (C2) Protocol

Purpose
- Lightweight, file-based protocol so an external AI CLI agent can execute XSArena tasks, produce reports, and keep status in sync. No services. No daemons.

Layout
- Queue: .xsarena/ops/c2_queue.json
- Status heartbeat: .xsarena/ops/c2_status.json
- Reports out: review/reports/
- Scripts: scripts/c2_run.py (runner), scripts/smoke.sh (optional), scripts/smoke.ps1 (optional)

Roles
- "Commander" (you/me): writes tasks into c2_queue.json (pending → running → done)
- "Agent" (qwen-code): runs scripts/c2_run.py to consume tasks and produce reports
- "Observer" (anyone): reads c2_status.json and review/reports/*

Task lifecycle
- pending → running → done|failed
- Each task has: id, type, params, out_file
- Runner writes stdout/stderr to out_file; updates status and per-task result

Supported tasks (initial)
- project_map: write a tree of the repo to review/reports/PROJECT_MAP.md
- commands_index: index Typer commands from "xsarena … --help" into review/reports/COMMANDS_INDEX.md
- snapshot_preflight_verify: run xsarena ops snapshot verify (preflight) with policy/budgets/globs
- snapshot_postflight_verify: verify repo_flat.txt or xsa_snapshot.txt for oversize/disallowed/redaction markers
- smoke: run scripts/smoke.sh or smoke.ps1 and save console output
- jobs_report: xsarena ops jobs ls + optional summary JOB_ID → review/reports/JOBS.md
- config_show: xsarena settings show and config-check → review/reports/SETTINGS.md
- search_files: search for a glob/regex and write hits to review/reports/SEARCH_<tag>.md

Conventions
- All commands run with NO_COLOR=1 and RICH_NO_COLOR=1 (clean output for machines)
- Long inputs are passed via files (never shove megabytes into argv)
- Outputs live under review/reports/ with timestamped filenames (runner adds ts if out_file missing)
- Snapshot policy goes in .xsarena/ops/snapshot_policy.yml (optional)

Run loop
- One-shot:
  python3 scripts/c2_run.py --once
- Continuous:
  python3 scripts/c2_run.py --watch --interval 5

Acceptance
- After a run, c2_status.json contains a concise heartbeat (last_run_ts, tasks_done, tasks_failed, last_reports)
- Reports exist where tasks declared them
- Exit codes reflect "all good" or "something failed"
