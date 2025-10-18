# Command Reference

This document provides a comprehensive reference for all XSArena commands organized by semantic groups.

## Top-Level Commands

### `run`
Run a book or recipe in authoring mode
```bash
xsarena run book "Subject" --length long --span book
xsarena run continue ./books/file.final.md --subject "New Title"
xsarena run from-recipe recipe.yml
xsarena run from-plan --subject "Project" --profile clinical-masters
xsarena run template kasravi_strip "Input text"
```

### `interactive`
Interactive authoring session
```bash
xsarena interactive
```

## Semantic Command Groups

### `author` - Core Content Creation
- `ingest`: Process and analyze input files
- `lossless`: Lossless text operations
- `style`: Style and formatting tools
- `workshop`: Workshop and editing tools
- `preview`: Preview and review tools

### `analyze` - Analysis and Reporting
- `report`: Generate various reports
- `coverage`: Analyze coverage of a book against an outline
- `continuity`: Analyze book continuity for anchor drift and re-introductions
- `style-lint`: Lint directive files for best practices
- `secrets`: Scan for secrets (API keys, passwords, etc.)
- `chad`: CHAD analysis tools

### `study` - Study Aids
- `generate`: Generate study materials
- `coach`: Coaching and tutoring tools
- `joy`: Joy and entertainment tools

### `dev` - Development Tools
- `agent`: Coding agent tools
- `pipeline`: Automation pipelines
- `simulate`: Offline simulation

### `ops` - Operations
- `service`: System services
- `jobs`: Job management
- `doctor`: Health checks and diagnostics
- `fix`: Automated fixes
- `clean`: Cleanup operations
- `snapshot`: Snapshot operations
- `config`: Configuration management
- `backend`: Backend configuration
- `metrics`: Metrics and monitoring
- `upgrade`: Upgrade operations
- `boot`: Boot operations

### `project` - Project Management
- `init`: Initialize a new project
- `lock-directives`: Generate directive lockfile

### `directives` - Directives and Profiles
- `index`: Index and manage directives
- `booster`: Interactively engineer and improve prompts
- `endpoints`: Manage endpoint configurations
- `list`: List available directives

## Job Management Commands

### `jobs` subcommands
- `ls`: List all jobs
- `log <job_id>`: Show event log for a job
- `summary <job_id>`: Show job summary
- `resume <job_id>`: Resume a paused job
- `cancel <job_id>`: Cancel a running job
- `pause <job_id>`: Pause a running job
- `next <job_id> "hint"`: Send hint to next chunk
- `watch <job_id>`: Watch job events
- `follow <job_id>`: Follow job to completion
- `tail <job_id>`: Tail job events
- `status <job_id>`: Show job status
- `gc`: Garbage collect old jobs
- `rm <job_id>`: Remove a job directory
- `boost <job_id> --priority N`: Boost job priority

## Service Management Commands

### `service` subcommands
- `start-bridge-v2`: Start the bridge server
- `start-compat-api`: Start compatibility API server
- `start-id-updater`: Start ID updater helper
- `install-bridge`: Install systemd service for bridge
- `start bridge`: Start bridge service via systemctl
- `stop bridge`: Stop bridge service via systemctl
- `status bridge`: Check bridge service status
- `enable bridge`: Enable bridge service auto-start
- `disable bridge`: Disable bridge service auto-start

## Settings Management

### `settings` subcommands
- `hammer [true|false]`: Toggle coverage hammer
- `budget [true|false]`: Toggle output budget addendum
- `push [true|false]`: Toggle output push
- `minchars <n>`: Set minimum characters per chunk
- `passes <n>`: Set max micro-extend passes
- `cont-anchor <n>`: Set continuation anchor length
- `repeat-warn [true|false]`: Toggle repetition warning
- `repeat-thresh <n>`: Set repetition threshold
- `smart-min [true|false]`: Toggle token-aware scaling
- `outline-first [true|false]`: Toggle outline-first seed
- `cont-mode <mode>`: Set continuation mode
- `persist`: Persist current settings to config
- `reset`: Reset settings from config
- `show`: Show current settings

## Utility Commands

### `tools` subcommands
- `eli5 <topic>`: Explain like I'm 5
- `story <concept>`: Explain concept as a story
- `persona <name>`: Set persona overlay
- `nobs <on|off>`: Alias for no-BS toggle
- `export-chapters <book> --out <dir>`: Export book chapters
- `extract-checklists --book <book> --out <dir>`: Extract checklists
