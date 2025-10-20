# C2 Tasks Catalog

project_map
- Purpose: navigate repository structure at a glance
- Output: review/reports/PROJECT_MAP.md (or as declared)

commands_index
- Purpose: discover commands via `--help` outputs
- Output: review/reports/COMMANDS_INDEX.md

snapshot_preflight_verify
- Params:
  - mode: minimal|tight|standard|full
  - policy: optional .yml
  - disallow: [globs...]
  - require: [paths...]
  - fail_on: [oversize|disallowed|secrets|missing_required|binary]
  - max_per_file, total_max
- Output: review/reports/SNAPSHOT_PREFLIGHT*.md

snapshot_postflight_verify
- Params:
  - file: repo_flat.txt | xsa_snapshot.txt
  - disallow: [globs...]
  - fail_on: [...]
  - max_per_file: int
  - redaction_expected: bool
- Output: review/reports/SNAPSHOT_POSTFLIGHT*.md

smoke
- Runs scripts/smoke.sh (Unix) or smoke.ps1 (Windows)
- Output: review/reports/SMOKE*.md

jobs_report
- xsarena ops jobs ls (+ optional summary)
- Output: review/reports/JOBS*.md

config_show
- xsarena settings show + config-check
- Output: review/reports/SETTINGS*.md

search_files
- Params: pattern (regex), root (dir), max_hits (int)
- Output: review/reports/SEARCH_<tag>.md

Usage flow (how we "keep pace")
- I produce a task block (JSON) you append to .xsarena/ops/c2_queue.json under tasks with "status":"pending".
- Your agent runs: python3 scripts/c2_run.py --once
- It updates .xsarena/ops/c2_status.json and writes reports under review/reports/
- You paste back report snippets or attach the files (or re-run the verify to summarize)
- We iterate: I issue more tasks; your agent executes; we converge fast without manual guessing.

Examples (tasks you can paste into c2_queue.json)
- Snapshot preflight (minimal)
  {
    "id":"T-0100",
    "type":"snapshot_preflight_verify",
    "params":{"mode":"minimal","max_per_file":180000,"total_max":2500000,"disallow":["books/**",".xsarena/**"],"fail_on":["oversize","disallowed","secrets"]},
    "out_file":"review/reports/SNAPSHOT_PREFLIGHT_MINIMAL.md",
    "status":"pending"
  }

- Project map + commands index
  {
    "id":"T-0101","type":"project_map","params":{},"out_file":"review/reports/PROJECT_MAP.md","status":"pending"
  },
  {
    "id":"T-0102","type":"commands_index","params":{},"out_file":"review/reports/COMMANDS_INDEX.md","status":"pending"
  }

That's all you need. It's simple, file-based, agent-friendly, and durable. Your AI CLI can drive XSArena by running commands; this C2 protocol tells it exactly what to run, how to report, and when it's done—while I can issue precise, incremental tasks at any time.
