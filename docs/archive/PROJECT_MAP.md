# Archived (stale).

# Project Map (from documentation)
Generated: 2025-10-14 23:20:48 UTC

## Source: README.md
# XSArena
XSArena is a command-line tool for AI-powered content generation and processing.
## Source: MODULES.md
# XSArena Module Structure
## Core Modules
### CLI Layer (`src/xsarena/cli/`)
- `main.py`: Main entry point and command router
- `context.py`: CLI context management
- Command modules (`cmds_*.py`): Individual command implementations
### Core Logic (`src/xsarena/core/`)
- `config.py`: Configuration management
- `redact.py`: Data redaction and privacy protection
- `prompt.py`: Prompt composition and management
- `jobs2_runner.py`: Job execution and management
- `recipes.py`: Recipe handling and processing
### Bridge/Backend (`src/xsarena/bridge/`)
- Integration with external AI services
- Userscript and bridge communication
## Command Modules
- `cmds_adapt.py`: Adaptive inspection and fixes
- `cmds_backend.py`: Backend configuration
- `cmds_book.py`: Book authoring commands
- `cmds_continue.py`: Continue from file tail
- `cmds_debug.py`: Debugging tools
- `cmds_fix.py`: Self-healing configuration
- `cmds_jobs.py`: Job execution
- `cmds_report.py`: Report bundle creation
- `cmds_snapshot.py`: Snapshot tools
- `cmds_modes.py`: Mode toggles
- `cmds_run.py`: Unified runner
## Documentation and Scripts
- `docs/`: User documentation
- `scripts/`: Utility scripts
- `recipes/`: Job recipe definitions
- `directives/`: AI directive files

## Source: docs/INDEX.md
# Documentation Index
## Core Documentation
- [README.md](../README.md) - Canonical user manual (exhaustive)
- [CLI_AGENT_RULES.md](../CLI_AGENT_RULES.md) - Complete operating rules and appendices
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and components overview
- [PROJECT_MAP.md](PROJECT_MAP.md) - Project structure and component overview
## Quick Reference
- [docs/SHORTCUTS.md](SHORTCUTS.md) - Agent shortcuts and modes
- [docs/RUNBOOKS.md](RUNBOOKS.md) - Copy-paste workflows
- [docs/PROFILES.md](PROFILES.md) - Style and quality profiles
## Operations
- [docs/SNAPSHOT_POLICY.md](SNAPSHOT_POLICY.md) - Canonical snapshot procedures
- [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Problem resolution
- [docs/HANDOFF.md](HANDOFF.md) - Communication template for higher AI
## Task Management
- [docs/INBOX.md](INBOX.md) - Prioritized tasks
- [docs/OUTBOX.md](OUTBOX.md) - Results tracking
- [docs/CONTEXT.md](CONTEXT.md) - Current state of the world
## Continuity
- [docs/AGENT_JOURNAL.md](AGENT_JOURNAL.md) - Session logging system
- [docs/KNOWN_ISSUES.md](KNOWN_ISSUES.md) - Known issues and workarounds
- [docs/INDEX.md](INDEX.md) - This file (documentation map)
## Sync & Maintenance
- [docs/SYNC_MATRIX.md](SYNC_MATRIX.md) - Sync whitelist and policies
- [scripts/sync_pass.sh](../scripts/sync_pass.sh) - Sync validation script

## Source: docs/QUICK_GUIDE.md
# Shortcuts & Modes (Agent One‑Pager)
## STARTUP: status + layout; propose HYGIENE/SNAPSHOT/HEALTH.
## SNAPSHOT: xsarena snapshot run; verify; path(s).
## HYGIENE: list → ask → delete safe targets → report.
## HEALTH: xsarena doctor env; optional smoke.
## MODE: LEARN_MANUAL: read, adapt, small changes; report.
## MODE: INGEST_ACT: harvest useful tips into README/docs; propose risky ones.
## RUNBOOK: MASTERY: print commands only; don't run unless asked.
## STOP_ON_LOOP: stop after 3 failed attempts or 3 minutes; snapshot; ask.
## HISTORY
- Read last 40 lines of .xsarena/agent/journal.jsonl
- Summarize last session (what changed, failures, snapshot paths)
- Offer next actions: HYGIENE, SNAPSHOT, UPDATE_MANUAL, or a specific RUNBOOK
## MODE: HANDOFF
- Fill docs/HANDOFF.md before asking higher AI
- Include recent changes, failures, commands used, artifacts, and crisp ask
- Save to docs/handoff/HANDOFF_<timestamp>.md
## SNAPSHOT+JOBS
- Create snapshot as usual, but include minimal job context for the specified <job_id> (events.jsonl, job.json). Do not include full sections.
## HYGIENE-DRYRUN
- Only list what would be removed (no deletion). Ask for "y/n" confirmation to proceed.
## ASK/DECIDE
- Check docs/INBOX.md for ASK/DECIDE tags first on STARTUP
- Surface these priorities before other tasks# Runbooks
This document contains standard operating procedures and runbooks for common XSArena tasks.
## JobSpec-First Workflow (Recommended)
### 0. JobSpec Overview
**Purpose**: Use declarative YAML/JSON specifications as the single source of truth for all runs
**Benefits**:
- Repeatable and versionable runs
- Clear separation of configuration from execution
- Better reliability and observability
- Easier debugging and sharing
**Structure**:
- JobSpec contains: subject, styles, continuation settings, budgets, backends, output paths, aids
- All UX entries (CLI, web UI) build and submit JobSpecs
- Runner executes based on the spec, not user session state
## Quick Start Runbooks
### 1. Basic Zero-to-Hero Book Generation (JobSpec-First)
**Purpose**: Create a comprehensive book on a topic using the recommended JobSpec-first approach
**Steps**:
1. Prepare environment: `xsarena doctor env`
2. Generate JobSpec: `xsarena z2h "Your Topic" --print-spec > recipes/topic.yml`
3. Review and edit spec: `cat recipes/topic.yml` (optional)
4. Run with spec: `xsarena run.recipe recipes/topic.yml`
5. Monitor progress: `xsarena serve run` (optional, for live preview)
6. Check results: `xsarena jobs summary <job_id>`
7. Export when complete: `xsarena publish run <job_id> --epub --pdf`
**Alternative**: Generate spec via wizard
- `xsarena wizard z2h` - Interactive wizard that creates the JobSpec
**Expected duration**: Varies by topic complexity and length settings

## Source: docs/STYLES.md
# Style and Quality Profiles
This document describes the different content profiles available in XSArena and how to configure them in JobSpec files.
## Overview
Profiles define the approach, density, and style characteristics for content generation. Each profile combines specific settings for continuation, length, and narrative approach.
## Profile Types
### 1. Mastery Profile (Dense, Comprehensive)
**Purpose**: Maximally comprehensive content with dense narrative prose
**Characteristics**:
- Dense narrative prose without lists/checklists/drills
- High information density (4200-5200 characters per chunk)
- 24+ chunks for depth
- Coverage hammer enabled
- Repetition guard active
**JobSpec Configuration**:
```yaml
styles: [compressed]
continuation:
  mode: anchor
  minChars: 4200
  pushPasses: 2
  repeatWarn: true
system_text: |
  English only. Dense narrative prose. Avoid lists/checklists/drills. No forced headings beyond what you naturally need.
  Definitions inline only when helpful (no bold rituals). Remove filler; keep distinctions and mechanisms crisp.
  If approaching length limits, stop cleanly and end with: NEXT: [Continue].
```
### 2. Pedagogy Profile (Teaching-Focused)
**Purpose**: Educational content with teaching-before-use approach
**Characteristics**:
- Narrative overlay with teach-before-use principle
- Include examples and quick checks
- Moderate length (3000-4000 characters per chunk)
- Balanced approach between depth and clarity
**JobSpec Configuration**:
```yaml
styles: [narrative]
continuation:
  mode: anchor
  minChars: 3000
  pushPasses: 1
  repeatWarn: true
system_text: |
  English only. Teach-before-use approach. Define terms before use, include short vignettes.
  Use pedagogical principles: include examples and quick checks.
  Maintain consistent depth throughout.
```
### 3. Reference Profile (Terse, Factual)
**Purpose**: Concise, factual reference material
**Characteristics**:
- Minimal explanation, factual presentation
- Shorter chunks (2000-2500 characters)
- Direct, no-fluff approach
- Focus on facts and mechanisms
**JobSpec Configuration**:
```yaml
styles: [nobs]
continuation:
  mode: anchor
  minChars: 2500
  pushPasses: 0
system_text: |
  English only. Concise, factual presentation. Minimal explanation.
  Direct approach without fluff. Focus on facts and mechanisms.
```
### 4. Popular Science Profile
**Purpose**: Accessible content for general audiences
**Characteristics**:
- Engaging narrative style
- Analogies and relatable examples
- Balanced technical depth
- Storytelling approach
**JobSpec Configuration**:
```yaml
styles: [pop]
continuation:
  mode: anchor
  minChars: 3500
  pushPasses: 1
system_text: |
  English only. Popular science style. Use analogies and relatable examples.
  Engaging narrative that balances technical depth with accessibility.
  Include real-world applications and context.
```
## Using Profiles in JobSpecs
### Method 1: Direct Style Application
Apply profiles directly through the `styles` field in your JobSpec:
```yaml
task: book.zero2hero
subject: "Your Topic"
styles: [compressed]  # or [narrative], [nobs], [pop]
# ... other configuration
```
### Method 2: Profile-Specific System Text
Use profile-specific system text to achieve more granular control:
```yaml
task: book.zero2hero
subject: "Your Topic"
styles: [narrative]  # base style
system_text: |
  [Include profile-specific instructions here]
  This will override or complement the base style settings.
```
### Method 3: Predefined Profile Files
Reference external profile files in your JobSpec:
```yaml
task: book.zero2hero
subject: "Your Topic"
style_file: "directives/style.compressed_en.md"  # or other profile files
# ... other configuration
```
## Profile Switching
You can switch between profiles by modifying the `styles` field and/or `system_text` in your JobSpec. For best results:
1. Generate a base JobSpec: `xsarena z2h "Topic" --print-spec > recipes/topic.yml`
2. Edit the `styles` and `system_text` fields to match your desired profile
3. Run with the modified spec: `xsarena run.recipe recipes/topic.yml`
## Best Practices
1. **Choose the right profile upfront**: Select the most appropriate profile for your content goal
2. **Test with short runs**: Use `--max 2-3` chunks to validate profile behavior
3. **Document profile decisions**: Include comments in your JobSpec explaining profile choice
4. **Version control profiles**: Track profile configurations in your recipes/ directory
5. **Combine with continuation settings**: Pair profiles with appropriate `minChars` and `pushPasses` values
## Advanced Profile Combinations
You can combine multiple style elements in a single JobSpec:
```yaml
styles: [narrative, compressed]  # Combines teaching approach with dense prose
# Note: Order may matter - first style takes precedence where they conflict
```
## Troubleshooting Profile Issues
- If content doesn't match profile expectations: Check that `system_text` doesn't conflict with style settings
- If chunks are too short/long: Adjust `minChars` in continuation settings
- If narrative elements appear when not wanted: Use `[compressed]` style with stricter system text
- If content is too dense: Switch to `[narrative]` or `[pop]` profile
Profiles provide a structured approach to content generation, ensuring consistency and predictability in your outputs.# Command Matrix
This matrix provides a quick reference for XSArena commands and their primary functions.
## Core Commands
| Command | Function | Primary Use Case |
|---------|----------|------------------|
| `xsarena z2h` | Zero-to-Hero book generation | Comprehensive content from foundations to advanced practice (use with --print-spec for JobSpec-first) |
| `xsarena jobs` | Job management | Submit, list, resume, cancel, fork jobs |
| `xsarena serve` | Local web preview | Browse books and job artifacts with live monitoring |
| `xsarena snapshot` | Project snapshotting | Create project representation for debugging |
| `xsarena doctor` | Health checks | Verify environment and run smoke tests |
| `xsarena publish` | Export formats | Convert to EPUB/PDF |
| `xsarena audio` | Audio conversion | Create audiobooks from text |
| `xsarena lossless` | Text processing | Ingest and rewrite without meaning loss |
| `xsarena style` | Style management | Toggle narrative, nobs, compressed styles |
| `xsarena book` | Book authoring | Various book generation modes |
## Job Management Commands
| Command | Function | Use Case |
|---------|----------|----------|
| `xsarena jobs ls` | List jobs | View all jobs and their status |
| `xsarena jobs log` | View job log | Monitor job events and progress |
| `xsarena jobs resume` | Resume job | Restart a paused job |
| `xsarena jobs cancel` | Cancel job | Stop a running job |
| `xsarena jobs fork` | Fork job | Clone job to different backend |
| `xsarena jobs summary` | Job summary | Detailed metrics (chunks, stalls, retries) |
| `xsarena jobs run` | Run job | Execute a job from spec (alias: run.recipe) |
| `xsarena run.recipe` | Run recipe/spec | Execute a JobSpec from YAML/JSON file (canonical JobSpec-first path) |
## Study Tools
| Command | Function | Purpose |
|---------|----------|---------|
| `xsarena exam cram` | Quick prep | High-yield outlines and pitfalls |
| `xsarena flashcards from` | Create flashcards | Q/A cards from content |
| `xsarena glossary from` | Create glossary | Definitions and explanations |
| `xsarena index from` | Create index | Grouped topic index |
## Quality & Monitoring
| Command | Function | Purpose |
|---------|----------|---------|
| `xsarena quality score` | Score content | Evaluate content quality |
| `xsarena quality uniq` | Check uniqueness | Verify content originality |
| `xsarena doctor env` | Environment check | Verify setup and dependencies |
| `xsarena doctor run` | Smoke test | Run synthetic z2h test |
## Backend & Service
| Command | Function | Purpose |
|---------|----------|---------|
| `xsarena service start-bridge` | Start bridge server | Enable browser integration |
| `xsarena backend` | Backend config | Configure bridge/OpenRouter |
| `xsarena mode` | Mode toggles | Switch between different modes |
## Advanced Features
| Command | Function | Purpose |
|---------|----------|---------|
| `xsarena coder` | Coding session | Advanced coding with tickets/patches |
| `xsarena templates` | Templates | Manage templates registry |
| `xsarena import` | Import content | Convert PDF/DOCX/MD to Markdown |
| `xsarena rp` | Roleplay | Interactive roleplay sessions |
| `xsarena joy` | Daily activities | Streaks, achievements, kudos |
| `xsarena coach` | Coaching | Drills and boss exams |
## Output Knobs
| Command | Function | Effect |
|---------|----------|---------|
| `xsarena book minchars` | Set min chars | Control chunk length |
| `xsarena book passes` | Set passes | Control micro-continuations |
| `xsarena book budget` | Toggle budget | Push for max density |
| `xsarena book hammer` | Toggle hammer | Anti-wrap continuation hint |
| `xsarena book cont-mode` | Set continuation | Change strategy (normal/anchor) |
| `xsarena book repeat-warn` | Toggle warnings | Repetition alerts |
| `xsarena book repeat-thresh` | Set threshold | Repetition sensitivity |
## Quick Reference
### Common Workflows
- **Quick book**: `xsarena z2h "Topic" --max=6 --min=3000`
- **List jobs**: `xsarena jobs ls`
- **Check health**: `xsarena doctor env`
- **Create snapshot**: `xsarena snapshot run`
- **Serve locally**: `xsarena serve run`
- **Export**: `xsarena publish run <job_id> --epub --pdf`
### Job Lifecycle
1. Submit: `xsarena z2h "Topic"` or `xsarena jobs run spec.yml`
2. Monitor: `xsarena jobs log <id>` or `xsarena serve run`
3. Manage: `xsarena jobs resume/cancel/fork <id>`
4. Review: `xsarena jobs summary <id>`
5. Export: `xsarena publish run <id>`

## Source: docs/_help_root.txt
xsarena
  A comprehensive AI-powered content generation and processing system.

USAGE:
    xsarena [OPTIONS] [SUBCOMMAND]

OPTIONS:
    -h, --help          Print help information
    -V, --version       Print version information
    --config <CONFIG>   Path to configuration file
    --verbose           Enable verbose output

SUBCOMMANDS:
    adapt        Adaptive inspection and configuration adjustment
    audio        Audio conversion tools
    backend      Backend configuration and management
    book         Book authoring commands
    boot         Startup and initialization commands
    clean        Hygiene and cleanup operations
    config       Configuration management
    continue     Continuation workflows
    debug        Debugging and diagnostic tools
    fast         Quick, opinionated workflows
    fix          Self-healing configuration commands
    jobs         Job lifecycle management
    lossless     Lossless text processing
    metrics      Metrics and analytics
    mixer        Multi-subject processing
    modes        Operational mode toggles
    people       People and persona management
    pipeline     Pipeline and workflow management
    plan         Planning and preparation workflows
    preview      Content preview and validation
    publish      Export and publishing tools
    quick        Quick diagnostic and utility commands
    report       Diagnostic reporting
    run          Unified execution interface
    serve        Local web preview server
    snapshot     Project state capture and debugging snapshots
    tools        Utility and helper commands
    z2h          Zero-to-Hero book generation

    help         Print this message or the help of the given subcommand(s)

## Source: directives/_rules/rules.merged.md
<!-- ===== BEGIN: directives/_rules/sources/CLI_AGENT_RULES.md ===== -->

# CLI Agent Rules & Guidelines for XSArena Project

## 1. Core Principles

### 1.1. Primary Directives
- **DO**: Always read and follow the canonical rules in `directives/_rules/rules.merged.md`
- **DO**: Run `xsarena doctor env` before starting major operations to verify environment health
- **DO**: Use JobSpec-first approach: `xsarena z2h "Topic" --print-spec > recipes/topic.yml` then `xsarena run.recipe recipes/topic.yml`
- **DO**: Verify system state with `xsarena jobs ls` and `xsarena snapshot run` when needed
- **DO**: Use `xsarena report quick` for diagnostic bundles when escalating to higher AI
- **DON'T**: Run operations without first checking environment with `xsarena doctor env`
- **DON'T**: Modify system state without understanding the consequences
- **DON'T**: Ignore error messages or warnings from the system

### 1.2. Safety Protocols
- **STOP** if you encounter unexpected behavior or errors
- **SNAPSHOT** with `xsarena snapshot run` before making significant changes
- **ASK** for guidance from higher AI when uncertain about next steps
- **DOCUMENT** any changes or actions taken for continuity

## 2. Operational Guidelines

### 2.1. Startup and Status Checks
- **Always** run `xsarena doctor env` to verify system health
- **Check** `xsarena jobs ls` to see current job status
- **Verify** `xsarena config show` to confirm configuration
- **Run** `xsarena snapshot run` to capture baseline state when needed

### 2.2. Job Management
- **Use** `xsarena jobs ls` to list all jobs
- **Monitor** with `xsarena jobs log <job_id>` to view job progress
- **Resume** with `xsarena jobs resume <job_id>` if a job was interrupted
- **Cancel** with `xsarena jobs cancel <job_id>` if a job needs to be stopped
- **Fork** with `xsarena jobs fork <job_id>` to clone a job to a different backend
- **Summarize** with `xsarena jobs summary <job_id>` for detailed metrics

### 2.3. Content Generation
- **Prefer** the JobSpec-first workflow: `xsarena z2h "Topic" --print-spec > recipes/topic.yml`
- **Run** with `xsarena run.recipe recipes/topic.yml` for better control and reproducibility
- **Monitor** progress with `xsarena serve run` for live preview
- **Export** with `xsarena publish run <job_id> --epub --pdf` when complete

### 2.4. Troubleshooting
- **First step**: `xsarena doctor env` to check environment
- **Job issues**: `xsarena jobs log <job_id>` to see detailed logs
- **System issues**: `xsarena debug state` to check internal state
- **Configuration**: `xsarena config show` to verify settings
- **Snapshot**: `xsarena snapshot run` to capture state for analysis

## 3. Advanced Features

### 3.1. Multi-Subject Processing
- **Use** `xsarena z2h-list "Topic A; Topic B; Topic C" --max=4 --min=2500` for multiple subjects
- **Monitor** individual jobs with `xsarena jobs ls` and `xsarena jobs log <job_id>`

### 3.2. Lossless Processing
- **Ingest** with `xsarena lossless ingest sources/topic_corpus.md books/topic.synth.md --chunk-kb 100 --synth-chars 16000`
- **Rewrite** with `xsarena lossless rewrite books/topic.synth.md books/topic.lossless.md`

### 3.3. Study Tools
- **Flashcards**: `xsarena flashcards from books/topic.source.md books/topic.flashcards.md --n 220`
- **Glossary**: `xsarena glossary from books/topic.source.md books/topic.glossary.md`
- **Index**: `xsarena index from books/topic.source.md books/topic.index.md`

## 4. Hygiene and Maintenance

### 4.1. Regular Maintenance
- **Clean** temporary files with `xsarena clean` commands
- **Check** for orphaned processes or stuck jobs
- **Verify** disk space and system resources
- **Update** recipes and directives as needed

### 4.2. Snapshot and Backup
- **Create** snapshots with `xsarena snapshot run` for debugging
- **Archive** important outputs before major changes
- **Document** any custom configurations or workflows

## 5. Communication with Higher AI

### 5.1. When to Escalate
- **Complex issues** that can't be resolved with standard troubleshooting
- **System errors** that affect core functionality
- **Configuration problems** that prevent normal operation
- **Performance issues** that impact workflow efficiency

### 5.2. Information to Include
- **Current state**: Output from `xsarena doctor env` and `xsarena jobs ls`
- **Recent actions**: Commands executed and their results
- **Error messages**: Exact text of any errors encountered
- **Snapshot**: Path to recent snapshot created with `xsarena snapshot run`
- **Goal**: Clear statement of what needs to be accomplished

## 6. Style and Quality Guidelines

### 6.1. Content Generation Styles
- **Mastery**: Use `[compressed]` style with high `minChars` (4200+) and multiple `pushPasses` (2) for dense, comprehensive content
- **Pedagogy**: Use `[narrative]` style with moderate `minChars` (3000+) and 1 `pushPasses` for teaching-focused content
- **Reference**: Use `[nobs]` style with lower `minChars` (2500+) and 0 `pushPasses` for concise, factual content

### 6.2. Quality Controls
- **Length**: Adjust `minChars` to control chunk length and content depth
- **Repetition**: Use `/book.repeat-warn on` and `/book.repeat-thresh 0.35` to detect repetition
- **Budget**: Use `/book.budget on` to push for maximum density
- **Hammer**: Use `/book.hammer on` for anti-wrap continuation

## 7. Command Reference

### 7.1. Essential Commands
- `xsarena doctor env` - Check environment health
- `xsarena z2h "Topic"` - Generate content from scratch
- `xsarena jobs ls` - List all jobs
- `xsarena jobs log <job_id>` - View job logs
- `xsarena run.recipe <recipe.yml>` - Run from JobSpec
- `xsarena snapshot run` - Create diagnostic snapshot
- `xsarena report quick` - Generate diagnostic bundle

### 7.2. Quick Start Sequence
1. `xsarena doctor env` - Verify environment
2. `xsarena z2h "Your Topic" --print-spec > recipes/topic.yml` - Generate JobSpec
3. `xsarena run.recipe recipes/topic.yml` - Run with JobSpec
4. `xsarena jobs log <job_id>` - Monitor progress
5. `xsarena publish run <job_id> --epub --pdf` - Export when complete

## 8. Error Handling

### 8.1. Common Errors
- **API Key Issues**: Verify API key is set in environment variables
- **Backend Connection**: Check internet connection and backend status
- **Disk Space**: Verify sufficient disk space for operations
- **Permissions**: Ensure proper file permissions for read/write operations

### 8.2. Recovery Steps
- **Stop job**: `xsarena jobs cancel <job_id>`
- **Check state**: `xsarena debug state`
- **Verify config**: `xsarena config show`
- **Create snapshot**: `xsarena snapshot run`
- **Resume or restart**: Based on situation

## 9. Best Practices

### 9.1. Workflow Best Practices
- **Plan first**: Always generate and review JobSpec before execution
- **Monitor actively**: Regularly check job progress with `xsarena jobs log`
- **Document changes**: Keep notes on configuration adjustments
- **Archive results**: Save important outputs for future reference

### 9.2. Quality Best Practices
- **Use JobSpec-first**: For reproducible and controllable runs
- **Apply appropriate styles**: Match content style to intended use case
- **Set proper parameters**: Adjust `minChars`, `pushPasses`, and other settings appropriately
- **Verify outputs**: Check generated content for quality and accuracy

<!-- ===== END: directives/_rules/sources/CLI_AGENT_RULES.md ===== -->

<!-- ===== BEGIN: directives/_rules/sources/ORDERS_LOG.md ===== -->
# Orders Log (append-only)
# Append "ONE ORDER" blocks here after each major instruction.

# ONE ORDER: Communication Procedures for Higher AI
- Save "Communication Rules for Higher AI" into docs/HIGHER_AI_COMM_PROTOCOL.md
- Re-merge rules so the canonical file includes CLI agent rules
- Generate a "missing-from-assistant" snapshot that lists and inlines contents of files not seen yet
- Confirm rules coverage with: fgrep -n "CLI Agent Rules" directives/_rules/rules.merged.md
- Tasks completed: 1) Created docs/HIGHER_AI_COMM_PROTOCOL.md, 2) Verified merge script includes CLI agent rules, 3) Generated missing files snapshot at review/missing_from_assistant_snapshot.txt, 4) Confirmed CLI Agent Rules in merged file
<!-- ===== END: directives/_rules/sources/ORDERS_LOG.md ===== -->

<!-- ===== BEGIN: directives/_rules/sources/CLI_AGENT_RULES.md ===== -->

# CLI Agent Rules & Guidelines for XSArena Project

## 1. Core Principles

### 1.1. Primary Directives
- **DO**: Always read and follow the canonical rules in `directives/_rules/rules.merged.md`
- **DO**: Run `xsarena doctor env` before starting major operations to verify environment health
- **DO**: Use JobSpec-first approach: `xsarena z2h "Topic" --print-spec > recipes/topic.yml` then `xsarena run.recipe recipes/topic.yml`
- **DO**: Verify system state with `xsarena jobs ls` and `xsarena snapshot run` when needed
- **DO**: Use `xsarena report quick` for diagnostic bundles when escalating to higher AI
- **DON'T**: Run operations without first checking environment with `xsarena doctor env`
- **DON'T**: Modify system state without understanding the consequences
- **DON'T**: Ignore error messages or warnings from the system

### 1.2. Safety Protocols
- **STOP** if you encounter unexpected behavior or errors
- **SNAPSHOT** with `xsarena snapshot run` before making significant changes
- **ASK** for guidance from higher AI when uncertain about next steps
- **DOCUMENT** any changes or actions taken for continuity

## 2. Operational Guidelines

### 2.1. Startup and Status Checks
- **Always** run `xsarena doctor env` to verify system health
- **Check** `xsarena jobs ls` to see current job status
- **Verify** `xsarena config show` to confirm configuration
- **Run** `xsarena snapshot run` to capture baseline state when needed

### 2.2. Job Management
- **Use** `xsarena jobs ls` to list all jobs
- **Monitor** with `xsarena jobs log <job_id>` to view job progress
- **Resume** with `xsarena jobs resume <job_id>` if a job was interrupted
- **Cancel** with `xsarena jobs cancel <job_id>` if a job needs to be stopped
- **Fork** with `xsarena jobs fork <job_id>` to clone a job to a different backend
- **Summarize** with `xsarena jobs summary <job_id>` for detailed metrics

### 2.3. Content Generation
- **Prefer** the JobSpec-first workflow: `xsarena z2h "Topic" --print-spec > recipes/topic.yml`
- **Run** with `xsarena run.recipe recipes/topic.yml` for better control and reproducibility
- **Monitor** progress with `xsarena serve run` for live preview
- **Export** with `xsarena publish run <job_id> --epub --pdf` when complete

### 2.4. Troubleshooting
- **First step**: `xsarena doctor env` to check environment
- **Job issues**: `xsarena jobs log <job_id>` to see detailed logs
- **System issues**: `xsarena debug state` to check internal state
- **Configuration**: `xsarena config show` to verify settings
- **Snapshot**: `xsarena snapshot run` to capture state for analysis

## 3. Advanced Features

### 3.1. Multi-Subject Processing
- **Use** `xsarena z2h-list "Topic A; Topic B; Topic C" --max=4 --min=2500` for multiple subjects
- **Monitor** individual jobs with `xsarena jobs ls` and `xsarena jobs log <job_id>`

### 3.2. Lossless Processing
- **Ingest** with `xsarena lossless ingest sources/topic_corpus.md books/topic.synth.md --chunk-kb 100 --synth-chars 16000`
- **Rewrite** with `xsarena lossless rewrite books/topic.synth.md books/topic.lossless.md`

### 3.3. Study Tools
- **Flashcards**: `xsarena flashcards from books/topic.source.md books/topic.flashcards.md --n 220`
- **Glossary**: `xsarena glossary from books/topic.source.md books/topic.glossary.md`
- **Index**: `xsarena index from books/topic.source.md books/topic.index.md`

## 4. Hygiene and Maintenance

### 4.1. Regular Maintenance
- **Clean** temporary files with `xsarena clean` commands
- **Check** for orphaned processes or stuck jobs
- **Verify** disk space and system resources
- **Update** recipes and directives as needed

### 4.2. Snapshot and Backup
- **Create** snapshots with `xsarena snapshot run` for debugging
- **Archive** important outputs before major changes
- **Document** any custom configurations or workflows

## 5. Communication with Higher AI

### 5.1. When to Escalate
- **Complex issues** that can't be resolved with standard troubleshooting
- **System errors** that affect core functionality
- **Configuration problems** that prevent normal operation
- **Performance issues** that impact workflow efficiency

### 5.2. Information to Include
- **Current state**: Output from `xsarena doctor env` and `xsarena jobs ls`
- **Recent actions**: Commands executed and their results
- **Error messages**: Exact text of any errors encountered
- **Snapshot**: Path to recent snapshot created with `xsarena snapshot run`
- **Goal**: Clear statement of what needs to be accomplished

## 6. Style and Quality Guidelines

### 6.1. Content Generation Styles
- **Mastery**: Use `[compressed]` style with high `minChars` (4200+) and multiple `pushPasses` (2) for dense, comprehensive content
- **Pedagogy**: Use `[narrative]` style with moderate `minChars` (3000+) and 1 `pushPasses` for teaching-focused content
- **Reference**: Use `[nobs]` style with lower `minChars` (2500+) and 0 `pushPasses` for concise, factual content

### 6.2. Quality Controls
- **Length**: Adjust `minChars` to control chunk length and content depth
- **Repetition**: Use `/book.repeat-warn on` and `/book.repeat-thresh 0.35` to detect repetition
- **Budget**: Use `/book.budget on` to push for maximum density
- **Hammer**: Use `/book.hammer on` for anti-wrap continuation

## 7. Command Reference

### 7.1. Essential Commands
- `xsarena doctor env` - Check environment health
- `xsarena z2h "Topic"` - Generate content from scratch
- `xsarena jobs ls` - List all jobs
- `xsarena jobs log <job_id>` - View job logs
- `xsarena run.recipe <recipe.yml>` - Run from JobSpec
- `xsarena snapshot run` - Create diagnostic snapshot
- `xsarena report quick` - Generate diagnostic bundle

### 7.2. Quick Start Sequence
1. `xsarena doctor env` - Verify environment
2. `xsarena z2h "Your Topic" --print-spec > recipes/topic.yml` - Generate JobSpec
3. `xsarena run.recipe recipes/topic.yml` - Run with JobSpec
4. `xsarena jobs log <job_id>` - Monitor progress
5. `xsarena publish run <job_id> --epub --pdf` - Export when complete

## 8. Error Handling

### 8.1. Common Errors
- **API Key Issues**: Verify API key is set in environment variables
- **Backend Connection**: Check internet connection and backend status
- **Disk Space**: Verify sufficient disk space for operations
- **Permissions**: Ensure proper file permissions for read/write operations

### 8.2. Recovery Steps
- **Stop job**: `xsarena jobs cancel <job_id>`
- **Check state**: `xsarena debug state`
- **Verify config**: `xsarena config show`
- **Create snapshot**: `xsarena snapshot run`
- **Resume or restart**: Based on situation

## 9. Best Practices

### 9.1. Workflow Best Practices
- **Plan first**: Always generate and review JobSpec before execution
- **Monitor actively**: Regularly check job progress with `xsarena jobs log`
- **Document changes**: Keep notes on configuration adjustments
- **Archive results**: Save important outputs for future reference

### 9.2. Quality Best Practices
- **Use JobSpec-first**: For reproducible and controllable runs
- **Apply appropriate styles**: Match content style to intended use case
- **Set proper parameters**: Adjust `minChars`, `pushPasses`, and other settings appropriately
- **Verify outputs**: Check generated content for quality and accuracy

<!-- ===== END: directives/_rules/sources/CLI_AGENT_RULES.md ===== -->

<!-- ===== BEGIN: directives/_rules/sources/CLI_AGENT_RULES.md ===== -->

# CLI Agent Rules & Guidelines for XSArena Project

## 1. Core Principles

### 1.1. Primary Directives
- **DO**: Always read and follow the canonical rules in `directives/_rules/rules.merged.md`
- **DO**: Run `xsarena doctor env` before starting major operations to verify environment health
- **DO**: Use JobSpec-first approach: `xsarena z2h "Topic" --print-spec > recipes/topic.yml` then `xsarena run.recipe recipes/topic.yml`
- **DO**: Verify system state with `xsarena jobs ls` and `xsarena snapshot run` when needed
- **DO**: Use `xsarena report quick` for diagnostic bundles when escalating to higher AI
- **DON'T**: Run operations without first checking environment with `xsarena doctor env`
- **DON'T**: Modify system state without understanding the consequences
- **DON'T**: Ignore error messages or warnings from the system

### 1.2. Safety Protocols
- **STOP** if you encounter unexpected behavior or errors
- **SNAPSHOT** with `xsarena snapshot run` before making significant changes
- **ASK** for guidance from higher AI when uncertain about next steps
- **DOCUMENT** any changes or actions taken for continuity

## 2. Operational Guidelines

### 2.1. Startup and Status Checks
- **Always** run `xsarena doctor env` to verify system health
- **Check** `xsarena jobs ls` to see current job status
- **Verify** `xsarena config show` to confirm configuration
- **Run** `xsarena snapshot run` to capture baseline state when needed

### 2.2. Job Management
- **Use** `xsarena jobs ls` to list all jobs
- **Monitor** with `xsarena jobs log <job_id>` to view job progress
- **Resume** with `xsarena jobs resume <job_id>` if a job was interrupted
- **Cancel** with `xsarena jobs cancel <job_id>` if a job needs to be stopped
- **Fork** with `xsarena jobs fork <job_id>` to clone a job to a different backend
- **Summarize** with `xsarena jobs summary <job_id>` for detailed metrics

### 2.3. Content Generation
- **Prefer** the JobSpec-first workflow: `xsarena z2h "Topic" --print-spec > recipes/topic.yml`
- **Run** with `xsarena run.recipe recipes/topic.yml` for better control and reproducibility
- **Monitor** progress with `xsarena serve run` for live preview
- **Export** with `xsarena publish run <job_id> --epub --pdf` when complete

### 2.4. Troubleshooting
- **First step**: `xsarena doctor env` to check environment
- **Job issues**: `xsarena jobs log <job_id>` to see detailed logs
- **System issues**: `xsarena debug state` to check internal state
- **Configuration**: `xsarena config show` to verify settings
- **Snapshot**: `xsarena snapshot run` to capture state for analysis

## 3. Advanced Features

### 3.1. Multi-Subject Processing
- **Use** `xsarena z2h-list "Topic A; Topic B; Topic C" --max=4 --min=2500` for multiple subjects
- **Monitor** individual jobs with `xsarena jobs ls` and `xsarena jobs log <job_id>`

### 3.2. Lossless Processing
- **Ingest** with `xsarena lossless ingest sources/topic_corpus.md books/topic.synth.md --chunk-kb 100 --synth-chars 16000`
- **Rewrite** with `xsarena lossless rewrite books/topic.synth.md books/topic.lossless.md`

### 3.3. Study Tools
- **Flashcards**: `xsarena flashcards from books/topic.source.md books/topic.flashcards.md --n 220`
- **Glossary**: `xsarena glossary from books/topic.source.md books/topic.glossary.md`
- **Index**: `xsarena index from books/topic.source.md books/topic.index.md`

## 4. Hygiene and Maintenance

### 4.1. Regular Maintenance
- **Clean** temporary files with `xsarena clean` commands
- **Check** for orphaned processes or stuck jobs
- **Verify** disk space and system resources
- **Update** recipes and directives as needed

### 4.2. Snapshot and Backup
- **Create** snapshots with `xsarena snapshot run` for debugging
- **Archive** important outputs before major changes
- **Document** any custom configurations or workflows

## 5. Communication with Higher AI

### 5.1. When to Escalate
- **Complex issues** that can't be resolved with standard troubleshooting
- **System errors** that affect core functionality
- **Configuration problems** that prevent normal operation
- **Performance issues** that impact workflow efficiency

### 5.2. Information to Include
- **Current state**: Output from `xsarena doctor env` and `xsarena jobs ls`
- **Recent actions**: Commands executed and their results
- **Error messages**: Exact text of any errors encountered
- **Snapshot**: Path to recent snapshot created with `xsarena snapshot run`
- **Goal**: Clear statement of what needs to be accomplished

## 6. Style and Quality Guidelines

### 6.1. Content Generation Styles
- **Mastery**: Use `[compressed]` style with high `minChars` (4200+) and multiple `pushPasses` (2) for dense, comprehensive content
- **Pedagogy**: Use `[narrative]` style with moderate `minChars` (3000+) and 1 `pushPasses` for teaching-focused content
- **Reference**: Use `[nobs]` style with lower `minChars` (2500+) and 0 `pushPasses` for concise, factual content

### 6.2. Quality Controls
- **Length**: Adjust `minChars` to control chunk length and content depth
- **Repetition**: Use `/book.repeat-warn on` and `/book.repeat-thresh 0.35` to detect repetition
- **Budget**: Use `/book.budget on` to push for maximum density
- **Hammer**: Use `/book.hammer on` for anti-wrap continuation

## 7. Command Reference

### 7.1. Essential Commands
- `xsarena doctor env` - Check environment health
- `xsarena z2h "Topic"` - Generate content from scratch
- `xsarena jobs ls` - List all jobs
- `xsarena jobs log <job_id>` - View job logs
- `xsarena run.recipe <recipe.yml>` - Run from JobSpec
- `xsarena snapshot run` - Create diagnostic snapshot
- `xsarena report quick` - Generate diagnostic bundle

### 7.2. Quick Start Sequence
1. `xsarena doctor env` - Verify environment
2. `xsarena z2h "Your Topic" --print-spec > recipes/topic.yml` - Generate JobSpec
3. `xsarena run.recipe recipes/topic.yml` - Run with JobSpec
4. `xsarena jobs log <job_id>` - Monitor progress
5. `xsarena publish run <job_id> --epub --pdf` - Export when complete

## 8. Error Handling

### 8.1. Common Errors
- **API Key Issues**: Verify API key is set in environment variables
- **Backend Connection**: Check internet connection and backend status
- **Disk Space**: Verify sufficient disk space for operations
- **Permissions**: Ensure proper file permissions for read/write operations

### 8.2. Recovery Steps
- **Stop job**: `xsarena jobs cancel <job_id>`
- **Check state**: `xsarena debug state`
- **Verify config**: `xsarena config show`
- **Create snapshot**: `xsarena snapshot run`
- **Resume or restart**: Based on situation

## 9. Best Practices

### 9.1. Workflow Best Practices
- **Plan first**: Always generate and review JobSpec before execution
- **Monitor actively**: Regularly check job progress with `xsarena jobs log`
- **Document changes**: Keep notes on configuration adjustments
- **Archive results**: Save important outputs for future reference

### 9.2. Quality Best Practices
- **Use JobSpec-first**: For reproducible and controllable runs
- **Apply appropriate styles**: Match content style to intended use case
- **Set proper parameters**: Adjust `minChars`, `pushPasses`, and other settings appropriately
- **Verify outputs**: Check generated content for quality and accuracy

<!-- ===== END: directives/_rules/sources/CLI_AGENT_RULES.md ===== -->

<!-- ===== BEGIN: directives/_rules/sources/ORDERS_LOG.md ===== -->
# Orders Log (append-only)
# Append "ONE ORDER" blocks here after each major instruction.

# ONE ORDER: Communication Procedures for Higher AI
- Save "Communication Rules for Higher AI" into docs/HIGHER_AI_COMM_PROTOCOL.md
- Re-merge rules so the canonical file includes CLI agent rules
- Generate a "missing-from-assistant" snapshot that lists and inlines contents of files not seen yet
- Confirm rules coverage with: fgrep -n "CLI Agent Rules" directives/_rules/rules.merged.md
- Tasks completed: 1) Created docs/HIGHER_AI_COMM_PROTOCOL.md, 2) Verified merge script includes CLI agent rules, 3) Generated missing files snapshot at review/missing_from_assistant_snapshot.txt, 4) Confirmed CLI Agent Rules in merged file

# ONE ORDER: Communication Procedures for Higher AI
- Save "Communication Rules for Higher AI" into docs/HIGHER_AI_COMM_PROTOCOL.md
- Re-merge rules so the canonical file includes CLI agent rules
- Generate a "missing-from-assistant" snapshot that lists and inlines contents of files not seen yet
- Confirm rules coverage with: fgrep -n "CLI Agent Rules" directives/_rules/rules.merged.md
- Tasks completed: 1) Created docs/HIGHER_AI_COMM_PROTOCOL.md, 2) Verified merge script includes CLI agent rules, 3) Generated missing files snapshot at review/missing_from_assistant_snapshot.txt, 4) Confirmed CLI Agent Rules in merged file
<!-- ===== END: directives/_rules/sources/ORDERS_LOG.md ===== -->
