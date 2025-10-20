# XSArena Modules

## Architecture Overview
XSArena follows a local-first, bridge-first approach for AI-assisted authoring with human-in-the-loop capabilities. The system emphasizes reproducible runs with persistent artifacts and declarative prompts.

## Core Components

### CLI Layer (`src/xsarena/cli/`)
- `registry.py`: Wires command groups (run, author, analyze, study, dev, ops, utils, settings, interactive)
- `context.py`: Loads Config and SessionState, builds Engine (backend transport)
- `interactive_session.py`: Provides REPL that reuses Typer app via dispatcher

### Core Runtime (`src/xsarena/core/`)
- `v2_orchestrator/`: RunSpecV2 resolution, job submission, manifest creation
- `prompt.py`: Composes system_text from templates, overlays, and extra files
- `state.py`: Manages SessionState "knobs" (continuation mode, anchors, repetition threshold, etc.)
- `jobs/`: Job management (model, executor, scheduler, store)
- `backends/`: Transport implementations (BridgeV2, circuit breaker, NullTransport)

### Bridge Server (`src/xsarena/bridge_v2/`)
- `api_server.py`: WebSocket communication, Cloudflare handling, API endpoints
- `static/console.html`: Minimal mission control UI

### Modes (`src/xsarena/modes/`)
- Specialized front-ends (book, bilingual, policy, chad, study)

### Utilities (`src/xsarena/utils/`)
- Analysis tools (continuity, coverage, density)
- Security tools (secrets_scanner)
- Processing utilities (chapter_splitter, token_estimator)

### Directives (`directives/`)
- Prompt templates, overlays, role guides

## Documentation
For full architectural details, see `docs/ARCHITECTURE.md`.
Regenerate CLI help: `xsarena docs gen-help` (outputs `docs/_help_*`).
