# XSArena Agent Manual (v0.2.x)

Purpose
- Single, precise guide for operating XSArena locally with bridge-first flows, resumable jobs, modularized components, and safe snapshots.
- Non-code SOP. If a config/policy can fix it, do not patch code.

Philosophy
- Local-first, bridge-first; deterministic runs (resume > redo).
- Config over code; redaction on by default; verify before share.
- Keep modules small and boundaries clear.

Quickstart (daily)
- Start bridge: xsarena ops service start-bridge-v2
- Capture IDs: xsarena unified-settings capture-ids
- Run a book: xsarena run book "Subject" --length long --span book --follow
- Follow job: xsarena ops jobs follow JOB_ID
- Create flat snapshot: xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt --no-repo-map
- Verify snapshot: xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected

Operating Orders (condensed)
- Preflight always:
  - xsarena ops health fix-run
  - xsarena settings config-check
  - xsarena ops health scan-secrets --path .
- Bridge ops:
  - Health: GET $(base)/v1/health (base_url ends with /v1)
  - Models: GET /v1/models; update via POST /internal/update_available_models
  - Per-model mapping (optional): model_endpoint_map.json (session_id/message_id/mode)
- Authoring:
  - Book: xsarena run book "Subject" --follow
  - Continue: xsarena run continue ./books/name.final.md --follow [--until-end]
  - Styles: xsarena author style-narrative on; xsarena author style-nobs on; xsarena author style-reading on
- Interactive cockpit:
  - xsarena interactive start
  - /prompt.show | /prompt.list | /prompt.style on|off <narrative|no_bs|compressed|bilingual> | /prompt.profile <name>
  - /out.minchars 4500 | /out.passes 1 | /cont.mode anchor | /cont.anchor 360 | /repeat.warn on | /repeat.thresh 0.35
  - /run.book "Subject" | /continue ./books/file.final.md --until-end
- Jobs:
  - ls / summary: xsarena ops jobs ls; xsarena ops jobs summary JOB_ID --json
  - control: xsarena ops jobs pause|resume|cancel JOB_ID
  - hint: xsarena ops jobs next JOB_ID "Continue with X"
  - boost queued: xsarena ops jobs boost JOB_ID --priority 2
  - GC old: xsarena ops jobs gc --days 30 --yes
- Snapshots (two flows):
  - Preflight verify (policy): xsarena ops snapshot verify --mode author-core --policy .xsarena/ops/snapshot_policy.yml --quiet
  - Flat txt (share): xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt --no-repo-map
  - Postflight verify: xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected --quiet
  - Pro bundle: xsarena ops snapshot debug-report --out ~/xsa_debug_report.txt
- Reports / handoff:
  - Quick: xsarena report quick --book <path>
  - Job: xsarena report job <job_id>
  - Full: xsarena report full --book <path>
  - Handoff: xsarena ops handoff prepare --book ./books/name.final.md --note "Issue…"; note/show as needed

Maintainability (modularization)
- Size caps: modules ≤ 500 LOC; functions ≤ 80 LOC.
- Boundaries:
  - bridge_v2/* must not import cli/*
  - cli/interactive controllers call Engine/Orchestrator, not transports
  - jobs/errors mapping isolated; manager loads/saves; executor does run loop
- Controller split (interactive):
  - interactive_session.py (thin command map)
  - interactive/prompt_ctrl.py, jobs_ctrl.py, config_ctrl.py, checkpoint_ctrl.py
- Bridge split:
  - config_loaders.py, guards.py, streams.py; handlers.py routes only
- Snapshot helpers:
  - Prefer utilities under utils/snapshot/*; dedupe helpers used by flatpack_txt

Snapshot discipline (SOP)
- Policy file: .xsarena/ops/snapshot_policy.yml (disallow globs, budgets, required, fail_on)
- Keep outputs in $HOME; never commit repo_flat.txt or xsa_*snapshot*.*
- Hygiene before run/report:
  - Remove repo root snapshots; purge snapshot_chunks/; sweep TTLs (xsarena ops health sweep)

Troubleshooting (fast)
- 401/403: set OPENROUTER_API_KEY or bridge api_key
- 429: backoff, reduce concurrency, retry
- transport_unavailable: start bridge, verify ws_connected
- transport_timeout: increase stream_response_timeout_seconds; retry once
- Loops: lower repetition_threshold (~0.32), increase anchor_length (360–420), set /out.passes 0 for that chunk
- Short chunks: raise /out.minchars; enable smart_min

Acceptance checklist (must tick)
- Bridge healthy; IDs persisted under bridge: {session_id, message_id}
- Book run completed or resumed; manifest saved; final file updated
- Queue respects caps/quiet hours; priority boosts persisted
- Snapshot verified OK (no secrets/disallowed/oversize; redaction present)
- Reports/handoff saved
- Tests green; docs help updated if CLI changed

Version and model
- Orchestrator: RunSpecV2 (length/span presets; overlays; extra_files; generate_plan)
- Jobs: resumable via JobManager + Executor; micro-extend with repetition guards; lossless compression optional
- Bridge v2: FastAPI + WS; per-request Cloudflare refresh; per-peer rate limit; image markdown passthrough
