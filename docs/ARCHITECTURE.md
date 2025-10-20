# XSArena Architecture

This document explains how XSArena is put together and how the major parts relate.

## Goals and philosophy
- Local-first, bridge-first authoring: route model traffic through a local bridge and a browser tab.
- Human-in-the-loop, reproducible runs: plan → chunk → extend → resume; persist artifacts and manifests.
- Single source of truth for commands: one Typer CLI (also reused by the interactive REPL).
- Declarative prompts: typed specs + base templates + overlays instead of ad-hoc strings.

## High-level layout
- CLI (Typer) surface: src/xsarena/cli/*
- Core runtime: src/xsarena/core/*
  - Orchestrator + Prompt layer + Jobs (manager/executor/scheduler/store) + State + Backends
- Bridge server: src/xsarena/bridge_v2/*
- Modes (specialized front-ends): src/xsarena/modes/*
- Utilities: src/xsarena/utils/*
- Directives (prompt templates, overlays): directives/

## Component map

- CLI (Typer)
  - registry.py wires groups: run, author, analyze, study, dev, ops, utils, settings, interactive
  - context.py loads Config + SessionState and builds Engine (backend transport)
  - interactive_session.py provides a REPL that reuses the Typer app via a small dispatcher

- Orchestration (core)
  - v2_orchestrator/orchestrator.py
    - Resolves a RunSpecV2, composes the system prompt, picks transport, submits a job
    - Saves a run manifest (system_text + directive digests + config snapshot)
  - v2_orchestrator/specs.py
    - RunSpecV2 (typed): subject, length/span presets, overlays, extra files, out path, backend/model hints
  - prompt.py
    - Composes system_text from base templates + overlays (+ reading overlay) + extra files
  - state.py
    - SessionState "knobs": continuation mode, anchor length, repetition threshold, min chars, overlays, reading overlay, etc.

- Jobs
  - jobs/model.py — JobManager: submit/resume/list, delegates to JobExecutor
  - jobs/executor.py — JobExecutor: chunk loop: build user prompt (anchors + hints), send, micro-extend, repetition guard, metrics, append file, write events
  - jobs/scheduler.py — Scheduler: concurrency limits, queued jobs, quiet hours
  - jobs/store.py — JobStore: job.json + events.jsonl + artifacts on disk under .xsarena/jobs/<id>

- Backends
  - backends/bridge_v2.py — BridgeV2Transport (OpenAI-style chat completion via local bridge)
  - backends/circuit_breaker.py — wraps a transport with breaker (CLOSED/OPEN/HALF_OPEN)
  - backends/__init__.py — create_backend factory; NullTransport (offline script responses)

- Bridge (FastAPI)
  - bridge_v2/api_server.py — WebSocket to userscript; SSE-like streaming back; Cloudflare refresh guard; /internal helpers; /v1/health
  - bridge_v2/static/console.html — minimal mission control UI

- Modes (optional UI layers over engine)
  - modes/book.py, modes/bilingual.py, modes/policy.py, modes/chad.py, modes/study.py

- Utilities (selected)
  - utils/continuity.py, utils/coverage.py, utils/density.py — analysis
  - utils/secrets_scanner.py — secret scanning
  - utils/chapter_splitter.py — split Markdown into chapters
  - utils/token_estimator.py — rough tokens/char conversion

## Data and artifacts
- .xsarena/config.yml — config (bridge + settings)
- .xsarena/session_state.json — persisted session knobs
- .xsarena/jobs/<job_id> — job.json + events.jsonl + outputs
- directives/ — base templates, overlays, role guides

## Typical flow: "run book"
1) CLI → registry.run_book → Orchestrator.run_spec
2) Compose system_text (base + overlays + files)
3) Submit job via JobManager
4) JobExecutor:
   - For each chunk: build prompt (anchor from previous output + optional "next" hint)
   - Send to backend; strip trailing NEXT hint; micro-extend to min chars; detect repetition; log; append to file
   - Resume: start at last_done + 1; compute anchor from file tail for chunk>1
5) Scheduler manages concurrency; Store writes artifacts; manifest saved

## Async invariants to keep healthy
- Circuit breaker counters and transitions updated under a lock
- Always await draining "next" hints; prefer hint over anchor
- Don't idle-restart bridge while response channels are active
- Only one Cloudflare refresh attempt per request_id
