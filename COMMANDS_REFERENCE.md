# XSArena Command Reference

This document provides a comprehensive reference for all XSArena commands, organized by their semantic groups.

## Command Groups

### Author
Core content creation workflows.

- `xsarena author run` - Run a book or recipe in authoring mode
  - `xsarena author run book "Subject"` - Generate a book with specified subject
  - `xsarena author run continue <file>` - Continue writing from an existing file
  - `xsarena author run from-recipe <file>` - Run a job from a recipe file
  - `xsarena author run from-plan` - Plan from rough seeds and run a book
  - `xsarena author run template <template> <subject>` - Run a structured directive
  - `xsarena author run replay <manifest>` - Replay a job from a run manifest
- `xsarena author interactive` - Start an interactive authoring session
- `xsarena author ingest` - Ingest and process content
- `xsarena author lossless` - Lossless operations
- `xsarena author style` - Apply style and pedagogy overlays

### Analyze
Analysis, reporting, and evidence-based tools.

- `xsarena analyze report` - Generate reports
- `xsarena analyze coverage --outline <file> --book <file>` - Analyze coverage of a book against an outline
- `xsarena analyze continuity` - Analyze book continuity for anchor drift and re-introductions
- `xsarena analyze style-lint <path>` - Lint directive files for best practices
- `xsarena analyze secrets [path]` - Scan for secrets (API keys, passwords, etc.)
- `xsarena analyze chad` - CHAD analysis tools

### Study
Study aids, learning tools, and practice drills.

- `xsarena study generate` - Generate study materials
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
- `xsarena ops doctor` - System health checks
- `xsarena ops fix` - Fix common issues
- `xsarena ops clean` - Clean operations
- `xsarena ops snapshot` - Snapshot management
- `xsarena ops settings` - Fine-tune output, continuation and repetition behavior
- `xsarena ops config` - Configuration management commands
- `xsarena ops debug` - Debugging commands
- `xsarena ops directives` - Directive tools (index)
- `xsarena ops booster` - Interactively engineer and improve prompts

### Top-Level Commands
Essential commands available at the top level.

- `xsarena run` - Run a book or recipe in authoring mode (alias for `xsarena author run`)
- `xsarena interactive` - Interactive authoring session (alias for `xsarena author interactive`)

## Settings Commands

The `xsarena ops settings` group provides fine-grained control over output and continuation behavior:

- `xsarena ops settings hammer [enable]` - Toggle the coverage hammer (prevents premature summarization)
- `xsarena ops settings budget [enable]` - Toggle the output budget addendum (pushes for longer chunks)
- `xsarena ops settings push [enable]` - Toggle output push (micro-extends to meet min_chars)
- `xsarena ops settings minchars <n>` - Set the target minimum characters per chunk
- `xsarena ops settings passes <n>` - Set the max number of micro-extend passes per chunk
- `xsarena ops settings cont-anchor <n>` - Set the continuation anchor length
- `xsarena ops settings repeat-warn [enable]` - Toggle the repetition detection warning
- `xsarena ops settings repeat-thresh <threshold>` - Set the repetition detection threshold (0.0-1.0)
- `xsarena ops settings smart-min [enable]` - Toggle token-aware minimum length scaling
- `xsarena ops settings outline-first [enable]` - Toggle outline-first seed for the first chunk only
- `xsarena ops settings cont-mode <mode>` - Set the continuation strategy ('anchor', 'normal', or 'semantic-anchor')
- `xsarena ops settings persist` - Persist current CLI knobs to .xsarena/config.yml under settings: key
- `xsarena ops settings reset` - Reset CLI knobs from persisted settings in .xsarena/config.yml
- `xsarena ops settings show` - Show current continuation/output/repetition knobs

## Jobs Commands

The `xsarena ops jobs` group provides job management:

- `xsarena ops jobs list` - List all jobs
- `xsarena ops jobs show <job_id>` - Show details of a specific job
- `xsarena ops jobs follow <job_id>` - Follow a job to completion
- `xsarena ops jobs cancel <job_id>` - Cancel a running job
- `xsarena ops jobs pause <job_id>` - Pause a running job
- `xsarena ops jobs resume <job_id>` - Resume a paused job
- `xsarena ops jobs next <job_id> <hint>` - Send a hint to the next chunk of a job

## Run Commands

The `xsarena author run` group provides various ways to run content generation:

- `xsarena author run book <subject>` - Generate a book with specified subject
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

Various utility commands are available through different groups:

- `xsarena tools eli5 <topic>` - Explain like I'm five
- `xsarena tools story <concept>` - Explain the concept with a short story
- `xsarena tools persona <name>` - Set persona overlay (chad|prof|coach)
- `xsarena tools nobs <on|off>` - Toggle no-BS setting
- `xsarena tools export-chapters <book>` - Export a book into chapters with navigation links
- `xsarena tools extract-checklists --book <book>` - Extract checklist items from a book
