# XSArena Command Reference
<!-- This file is the source of truth for CLI usage; regenerate via scripts/gen_docs.sh -->

This document provides a comprehensive reference for all XSArena commands, organized by their semantic groups.

## Command Groups

### Author
Core content creation workflows.

- `xsarena run` - Run a book or recipe in authoring mode (alias for `xsarena author run`)
  - `xsarena run book "Subject"` - Generate a book with specified subject
  - `xsarena run continue <file>` - Continue writing from an existing file
  - `xsarena run from-recipe <file>` - Run a job from a recipe file
  - `xsarena run from-plan` - Plan from rough seeds and run a book
  - `xsarena run template <template> <subject>` - Run a structured directive
  - `xsarena run replay <manifest>` - Replay a job from a run manifest
- `xsarena author interactive` - Start an interactive authoring session

### Interactive Session Commands (REPL)

Commands available within the interactive session (use /command format):

- `/run.inline` - Paste and run a multi-line YAML recipe (end with EOF)
- `/quickpaste` - Paste multiple /commands (end with EOF)
- `/checkpoint.save [name]` - Save current session state to checkpoint
- `/checkpoint.load [name]` - Load session state from checkpoint
- `xsarena author ingest-ack` - Ingest a large document in 'acknowledge' mode with 'OK i/N' handshake loop
- `xsarena author ingest-synth` - Ingest a large document in 'synthesis' mode with rolling update loop
- `xsarena author ingest-style` - Ingest a large document in 'style' mode with rolling style profile update loop
- `xsarena author ingest-run` - Ingest a large document and create a dense synthesis (alias for synth mode)
- `xsarena author lossless-ingest` - Ingest and synthesize information from text
- `xsarena author lossless-rewrite` - Rewrite text while preserving all meaning
- `xsarena author lossless-run` - Perform a comprehensive lossless processing run
- `xsarena author lossless-improve-flow` - Improve the flow and transitions in text
- `xsarena author lossless-break-paragraphs` - Break dense paragraphs into more readable chunks
- `xsarena author lossless-enhance-structure` - Enhance text structure with appropriate headings and formatting
- `xsarena author style-narrative` - Enable or disable the narrative/pedagogy overlay for the session
- `xsarena author style-nobs` - Enable or disable the no-bullshit (no-bs) language overlay
- `xsarena author style-reading` - Enable or disable the further reading overlay for the session
- `xsarena author style-show` - Show currently active overlays
- `xsarena author style-apply` - Generate content on a new subject using a captured style profile file
- `xsarena author workshop` - Workshop tools
- `xsarena author preview` - Preview tools
- `xsarena author post-process` - Post-processing tools (aliases to utils tools)
  - `xsarena author post-process export-chapters <book>` - Export a book into chapters with navigation links (alias to xsarena utils tools export-chapters)
  - `xsarena author post-process extract-checklists --book <book>` - Extract checklist items from a book (alias to xsarena utils tools extract-checklists)

### Analyze
Analysis and evidence-based tools.

- `xsarena analyze coverage --outline <file> --book <file>` - Analyze coverage of a book against an outline
- `xsarena analyze continuity` - Analyze book continuity for anchor drift and re-introductions
- `xsarena analyze style-lint <path>` - Lint directive files for best practices
- `xsarena analyze secrets [path]` - Scan for secrets (API keys, passwords, etc.)
- `xsarena analyze chad` - CHAD analysis tools

### Study
Study aids, learning tools, and practice drills.

- `xsarena study generate` - Generate study materials
  - `xsarena study generate flashcards <content_file>` - Generate flashcards from a content file
  - `xsarena study generate quiz <content_file>` - Generate a quiz from a content file
  - `xsarena study generate glossary <content_file>` - Create a glossary from a content file with frequency filtering
  - `xsarena study generate index <content_file>` - Generate an index from a content file with depth control
  - `xsarena study generate cloze <content_file>` - Create cloze deletions from a content file
  - `xsarena study generate drill <content_file>` - Generate active recall drills from a content file
- `xsarena study coach` - Coaching tools
- `xsarena study joy` - Joy-related tools (hidden)

### Dev
Coding agent, git integration, automation pipelines, and simulation.

- `xsarena dev agent` - Coding agent tools
- `xsarena dev pipeline` - Pipeline management
- `xsarena dev simulate <subject>` - Run a fast offline simulation

### Project
Project management and initialization.

- `xsarena project project` - Project-related commands
- `xsarena project init` - Initialize a new project

### Ops
System health, jobs, services, and configuration.

- `xsarena ops service` - Service management
- `xsarena ops jobs` - Job management
- `xsarena ops health` - System health, maintenance, and self-healing operations
- `xsarena ops handoff` - Prepare higher-AI handoffs
  - `xsarena ops handoff prepare` - Build snapshot and brief for higher AI handoff
  - `xsarena ops handoff note` - Add notes to the latest handoff request
  - `xsarena ops handoff show` - Show the latest handoff package details
- `xsarena ops orders` - Manage ONE ORDER log
  - `xsarena ops orders new` - Create a new order with title and body
  - `xsarena ops orders ls` - List recent orders
  - `xsarena ops health fix-run` - Self-heal common configuration/state issues
  - `xsarena ops health sweep` - Purge ephemeral artifacts by TTL
  - `xsarena ops health scan-secrets` - Scan for secrets (API keys, passwords, etc.) in working tree
  - `xsarena ops health mark` - Add an XSA-EPHEMERAL header to a helper script so the sweeper can purge it later
  - `xsarena ops health read` - Read startup plan; attempt merge; print sources found
  - `xsarena ops health init` - One-time helper: create a minimal rules baseline if merged rules and sources are missing
- `xsarena ops snapshot` - Snapshot management
  - `xsarena ops snapshot create` - Create a flat snapshot, ideal for chatbot uploads (recommended)
    - `xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000` - Ultra-tight preset (recommended)
    - `xsarena ops snapshot create --mode author-core --total-max 4000000 --max-per-file 200000` - Author core preset (alternative)
    - `xsarena ops snapshot create --mode custom -I README.md -I src/xsarena/core/prompt.py --out repo_flat.txt` - Custom includes
  - `xsarena ops snapshot debug-report` - Generate a verbose snapshot for debugging (formerly 'pro')
  - `xsarena ops snapshot verify` - Verify snapshot health: preflight or postflight
- `xsarena ops debug` - Debugging commands
- `xsarena ops directives` - Directive tools (index)
- `xsarena ops booster` - Interactively engineer and improve prompts
- `xsarena ops adapt` - Adaptive inspection and safe fixes
  - `xsarena ops adapt inspect` - Analyze repo state and write a plan (no changes)
  - `xsarena ops adapt fix` - Apply safe, targeted fixes (no refactors)
  - `xsarena ops adapt plan` - Alias to inspect (compat)
  - `xsarena ops adapt suppress-add` - Add suppression patterns to avoid false positives
  - `xsarena ops adapt suppress-ls` - List current suppression patterns
  - `xsarena ops adapt suppress-clear` - Clear suppression patterns

### Top-Level Commands
Essential commands available at the top level.

- `xsarena run` - Run a book or recipe in authoring mode (alias for `xsarena author run`)
- `xsarena interactive` - Interactive authoring session (alias for `xsarena author interactive`)
- `xsarena settings` - Unified settings interface (configuration + controls)
- `xsarena report` - Create diagnostic reports
  - `xsarena report quick` - Generate quick diagnostic report
  - `xsarena report job` - Generate detailed job-specific report
  - `xsarena report full` - Generate full debug report with pro snapshot

### Deprecated Commands

- `xsarena ops doctor` - System health checks (DEPRECATED → use xsarena ops health ...)

## Settings Commands

The `xsarena settings` group provides unified access to both configuration and controls settings:

- `xsarena settings show` - Show both configuration and controls settings
- `xsarena settings set` - Set configuration or controls settings with various options:
  - `--backend` - Set backend (ops settings)
  - `--model` - Set default model (ops settings)
  - `--base-url` - Set base URL for bridge backend (ops settings)
  - `--api-key` - Set API key (ops settings)
  - `--output-min-chars` - Set minimal chars per chunk (utils settings)
  - `--output-push-max-passes` - Set max extension steps per chunk (utils settings)
  - `--continuation-mode` - Set continuation mode (utils settings)
  - `--anchor-length-config` - Set config anchor length (ops settings)
  - `--anchor-length-control` - Set control anchor length (utils settings)
  - `--repetition-threshold` - Set repetition detection threshold (utils settings)
  - `--repetition-warn/--no-repetition-warn` - Enable or disable repetition warning (utils settings)
  - `--coverage-hammer/--no-coverage-hammer` - Enable or disable coverage hammer (utils settings)
  - `--output-budget/--no-output-budget` - Enable or disable output budget addendum (utils settings)
  - `--output-push/--no-output-push` - Enable or disable output pushing (utils settings)
- `xsarena settings persist` - Persist current CLI knobs to .xsarena/config.yml (controls layer) and save config (config layer)
- `xsarena settings reset` - Reset settings from persisted configuration (controls layer) and reload config (config layer)

## Jobs Commands

The `xsarena ops jobs` group provides job management:

- `xsarena ops jobs list` - List all jobs
- `xsarena ops jobs show <job_id>` - Show details of a specific job
- `xsarena ops jobs follow <job_id>` - Follow a job to completion
- `xsarena ops jobs cancel <job_id>` - Cancel a running job
- `xsarena ops jobs pause <job_id>` - Pause a running job
- `xsarena ops jobs resume <job_id>` - Resume a paused job
- `xsarena ops jobs next <job_id> <hint>` - Send a hint to the next chunk of a job
- `xsarena ops jobs clone <job_id>` - Clone a job directory into a new job with a fresh id

## Run Commands

The `xsarena run` group provides various ways to run content generation:

- `xsarena run book <subject>` - Generate a book with specified subject
  - `--profile <profile>` - Use a specific profile
  - `--length <length>` - Set length preset (standard|long|very-long|max)
  - `--span <span>` - Set span preset (medium|long|book)
  - `--extra-file <file>` - Append file(s) to system prompt
  - `--out <path>` - Set output path
  - `--wait` - Wait for browser capture before starting
  - `--plan` - Generate an outline first
  - `--follow` - Submit job and follow to completion
- `xsarena author run continue <file>` - Continue writing from an existing file
- `xsarena author run from-recipe <file>` - Run a job from a recipe file
- `xsarena author run from-plan` - Plan from rough seeds and run a book
- `xsarena author run template <template> <subject>` - Run a structured directive from the library
- `xsarena author run replay <manifest>` - Replay a job from a run manifest

## Tools Commands

Various utility commands are available through the utils group:

- `xsarena utils tools eli5 <topic>` - Explain like I'm five
- `xsarena utils tools story <concept>` - Explain the concept with a short story
- `xsarena utils tools persona <name>` - Set persona overlay (chad|prof|coach)
- `xsarena utils tools nobs <on|off>` - Toggle no-BS setting
- `xsarena utils tools export-chapters <book>` - Export a book into chapters with navigation links
- `xsarena utils tools extract-checklists --book <book>` - Extract checklist items from a book
