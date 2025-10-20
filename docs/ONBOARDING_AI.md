# Onboarding for a New AI Session

Purpose
- Assume no context: quickly learn this repo and produce a usable baseline.

Rules
- Command-only; no imports. NO_COLOR=1; RICH_NO_COLOR=1. Non-interactive; explicit flags.

Steps (15 minutes)
1) Read README_FOR_AI.md and docs/ARCHITECTURE.md
2) Bridge health (optional for simulate):
   - xsarena ops service start-bridge-v2 &
   - curl -s http://127.0.0.1:5102/v1/health
3) Produce baseline reports:
   - Create .xsarena/ops/c2_queue.json with tasks: project_map, commands_index, config_show
   - python3 scripts/c2_run.py --once
   - Read reports under review/reports/
4) Smoke:
   - scripts/smoke.sh (or scripts/smoke.ps1)
5) If a snapshot is needed:
   - docs/SNAPSHOT_RULEBOOK.md and xsarena ops snapshot verify … (preflight), then txt ultra-tight

If blocked, open review/agent_ticket_<ts>.md with repro/observations and propose a minimal fix.
