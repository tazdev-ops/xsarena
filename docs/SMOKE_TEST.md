# XSArena Smoke Test (10–15 min)

Goal: verify core flows work end‑to‑end without crashes. Run in order; you can stop at the first failure and consult TROUBLESHOOTING.md.

Prereqs
- Python ≥ 3.9; Firefox + Tampermonkey + bridge userscript (installed + enabled)
- Base URL defaults to: http://127.0.0.1:5102/v1 (xsarena settings config-check should show normalized)
- If you token-gated /internal endpoints, have the token handy (X-Internal-Token)

1) CLI basics
- Commands:
  - xsarena --version
  - xsarena --help | head -n 5
  - xsarena --backend openrouter --model foo/bar --window 42 settings show
- Expect:
  - No traceback; settings show reflects overrides

2) Bridge up and healthy (choose one)
- A) If you have connect wrapper:
  - xsarena ops service connect
  - Expect: opens /console and optional launch URL; waits for ws_connected; prints "Connected"
- B) Manual:
  - xsarena ops service start-bridge-v2
  - curl -s http://127.0.0.1:5102/v1/health
  - Expect: {"status":"ok", ...}
  - Open model page in Firefox with #bridge=5102; click Retry
  - Expect (bridge logs): "✅ Userscript connected via WebSocket."
- If bridge.internal_api_token is set:
  - curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5102/internal/config → 401
  - curl -H "X-Internal-Token: YOUR_TOKEN" http://127.0.0.1:5102/internal/config → 200

3) Orchestration (offline simulate)
- Commands:
  - xsarena dev simulate "Sanity Subject" --length standard --span medium
  - xsarena ops jobs ls
- Expect:
  - "Simulation completed! Job ID: …"
  - Jobs list shows the job state DONE and an output path under ./books/

4) Run (dry-run) authoring
- Command:
  - xsarena run book "Sanity Subject" --dry-run
- Expect:
  - Prints a resolved spec and "System Text" block; ends with "[DRY RUN] Execution completed"

5) Continue an existing file
- Commands:
  - echo "# Test" > ./books/Resume_Test.final.md
  - xsarena run continue ./books/Resume_Test.final.md --length standard --span medium --wait false
  - xsarena ops jobs summary JOB_ID (from run output or jobs ls)
- Expect:
  - No crash; job completes; file appended (no duplicate header); summary shows chunks > 0

6) Interactive REPL with /command
- Command:
  - xsarena interactive start
    - /run book "Hello" --dry-run
    - /run --help
    - /exit
- Expect:
  - Typer's help prints inside REPL; no errors about event loop or dispatch

7) Bilingual translation (smoke)
- Create a tiny test.md:
  - printf "# Hello\n\nThis is a test." > test.md
- Command:
  - xsarena bilingual transform "$(cat test.md)" --source English --target Spanish > out.md
- Expect:
  - out.md contains Spanish text, preserves Markdown headings (#)

8) Analysis utilities
- Commands:
  - xsarena analyze continuity ./books/Resume_Test.final.md
  - xsarena analyze coverage --outline ./books/Resume_Test.final.md --book ./books/Resume_Test.final.md
- Expect:
  - Writes reports under review/…; no crash

9) Docs generator
- Commands:
  - xsarena docs gen-help
  - test -f docs/_help_root.txt
- Expect:
  - Help files generated; generator skips arg-required commands without aborting

10) Snapshot audit (if verify command exists)
- Preflight audit:
  - xsarena ops snapshot verify --mode minimal --max-per-file 180000 --total-max 2500000 --disallow books/** --disallow review/** --disallow .xsarena/** --fail-on oversize --fail-on disallowed
- Expect:
  - "[verify] OK" (or a list of violations with clear categories)

Pass criteria
- No tracebacks in any step; bridge health OK; REPL /command works; simulate and dry-run succeed; continue appends; docs generate; optional verify returns OK.

What to save for debugging
- .xsarena/jobs/<job_id>/events.jsonl
- curl output of /v1/health
- First 200 lines of dry-run system text
