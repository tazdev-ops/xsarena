# Agent Integration

This guide explains how to operate XSArena in a fully automated, agent-friendly manner using only shell commands. No GUI or manual reading required.

## Overview

XSArena is fully operable in command mode. Your agent should only call shell commands (`xsarena ...`). No import usage is required.

## Environment defaults for agents

- Set `NO_COLOR=1` and `RICH_NO_COLOR=1` to suppress ANSI color escape codes in outputs.
- Prefer non-interactive flags:
  - `--wait false` on continue
  - `--resume` or `--overwrite` when running book to avoid prompts
- Base URL should be `http://127.0.0.1:5102/v1`. If not reachable, start: `xsarena ops service start-bridge-v2`

## Connect sequence (bridge → userscript)

### Minimal sequence (recommended):
- `xsarena ops service start-bridge-v2`
- Poll: `curl -s http://127.0.0.1:5102/v1/health | jq .status`
- In Firefox, open the model tab with `#bridge=5102`; userscript connects (logs "Userscript connected")

### Optional wrapper (if implemented): `xsarena ops service connect`
- Starts bridge, opens `/console` and your `launch_url#bridge=PORT`, waits for `ws_connected`, prints "Connected"

## Preflight before any run

- `xsarena settings config-check`
  - Expect: "✓ Configuration is valid" and normalized "Base URL .../v1"
- If bridge needed: ensure `/v1/health` is ok and `ws_connected` true if your flow requires the userscript
- Optional: verify snapshot plan (see verify)

## Task recipes (intents → commands)

### Author book (dry-run):
- `xsarena run book "Subject" --dry-run`

### Author book (real, non-interactive):
- `xsarena run book "Subject" --length long --span book --follow --resume`
  or `--overwrite` to start fresh

### Continue:
- `xsarena run continue ./books/Title.final.md --length standard --span medium --wait false`

### Translate a file (small):
- `xsarena bilingual transform "$(cat input.md)" --source English --target Spanish > out.md`
- For large files: write a Python helper as in docs/USAGE.md to avoid shell arg length limits

### Analysis gate:
- `xsarena analyze continuity ./books/Title.final.md`
- `xsarena analyze coverage --outline outline.md --book ./books/Title.final.md`

### Docs/help refresh:
- `xsarena docs gen-help`

### Snapshot audit (if verify exists):
- `xsarena ops snapshot verify --mode minimal --max-per-file 180000 --total-max 2500000 --disallow books/** --disallow review/** --fail-on oversize --fail-on disallowed`

## Non-interactive contract (guidelines)

- Avoid prompts: always pass explicit flags (`--resume`/`--overwrite`, `--wait false`).
- Never pass huge content via argv; write to a file and pass a path.
- If a command can be long-running (jobs), poll with `xsarena ops jobs ls/summary/follow`.

## Errors and exit codes (expectations)

- 0: success
- 1: error (Typer/command raised)
- 2: usage or not-found (file paths missing, wrong flags)
- "Bridge not reachable": retry `start-bridge-v2` then re-run
- "Cloudflare challenge": the bridge retries once; if it fails, instruct the user to solve in Firefox then retry

## Suggested env toggles (optional)

- `XSA_BRIDGE_HOST=127.0.0.1` (default)
- `XSA_INTERNAL_TOKEN` for `/internal` endpoints (if you gated them)
- `XSARENA_PROJECT_ROOT` to help directive discovery in unusual CWDs
