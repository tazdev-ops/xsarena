# XSArena Complete Documentation (Simplified)

## Overview
XSArena is a human writer workflow tool that bridges to LMArena for long-form content creation. It focuses on providing a structured approach to writing books, manuals, and other long-form content with AI assistance.

## Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager
- Git (for cloning the repository)

### Installation Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/xsarena.git
   cd xsarena
   ```

2. Set up virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Verify installation:
   ```bash
   xsarena --help
   ```

## Essential Workflows

### Book Authoring
Generate comprehensive books from zero to hero level with structured prompts:

```bash
# Create a book with default settings
xsarena run book "Machine Learning Fundamentals"

# Create a longer book with custom length and span
xsarena run book "Advanced Python Programming" --length long --span book

# Plan first, then write
xsarena run from-plan --subject "History of Rome"
```

### Interactive Mode
Start an interactive session for real-time collaboration:
```bash
xsarena interactive start
```

### Study Aids
Generate educational materials from your content:
```bash
# Create flashcards from a text file
xsarena study generate flashcards path/to/content.txt

# Generate a quiz
xsarena study generate quiz path/to/content.txt --num 20

# Create a glossary
xsarena study generate glossary path/to/content.txt
```

### Content Processing
Process and refine content with lossless operations:
```bash
# Rewrite text while preserving meaning
xsarena author lossless-rewrite "Your text here..."

# Improve flow and transitions
xsarena author lossless-improve-flow "Your text here..."

# Enhance structure with headings
xsarena author lossless-enhance-structure "Your text here..."
```

## Command Structure

XSArena is organized into semantic command groups:

- **`run`** - Book generation and long-form content creation
- **`study`** - Educational tools (flashcards, quizzes, glossaries)
- **`author`** - Content creation, ingestion, and style tools
- **`interactive`** - Interactive sessions and real-time collaboration
- **`ops`** - Operations, jobs, settings, and service management
- **`dev`** - Development tools and agent functionality
- **`analyze`** - Content analysis and insights

## Bridge and Health Commands

### Starting the Bridge
```bash
# Start bridge
xsarena ops service start-bridge-v2

# Verify health
curl http://127.0.0.1:5102/v1/health

# Quick smoke test
xsarena dev simulate "Sanity" --length standard --span medium
```

## Jobs Management

### Job Operations
```bash
# List jobs
xsarena ops jobs ls

# Follow job logs
xsarena ops jobs follow JOB_ID

# Control jobs
xsarena ops jobs pause|resume|cancel JOB_ID

# Send next-hint to job
xsarena ops jobs next JOB_ID "Continue with X"

# Cleanup old jobs
xsarena ops jobs gc --days 14 --yes
```

## Snapshots

### Three-Tier Snapshot System

#### 1. Minimal (Flat Text - Recommended for AI)
- **Command**: `xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map`
- **Output**: `~/repo_flat.txt`
- **Purpose**: For sharing with AI assistants
- **Features**: Redaction on by default, strict size limits

#### 2. Normal (Zip Archive - For General Use)
- **Command**: `xsarena ops snapshot write --mode tight --with-git=false --with-jobs=false --with-manifest=false --zip`
- **Output**: `~/xsa_snapshot.zip`
- **Purpose**: For most other sharing needs
- **Features**: Compressed format, includes source files

#### 3. Maximal (Debug Report - For Troubleshooting)
- **Command**: `xsarena ops snapshot debug-report`
- **Output**: `~/xsa_debug_report.txt`
- **Purpose**: For comprehensive debugging
- **Features**: Includes system info, logs, and project state

### Verification
Always verify snapshots before sharing:
```bash
xsarena ops snapshot verify --file ~/repo_flat.txt
```

## Analysis Tools

### Continuity and Coverage Analysis
```bash
# Check continuity in a manuscript
xsarena analyze continuity ./books/Your_Book.final.md

# Check coverage vs. outline
xsarena analyze coverage --outline outline.md --book ./books/Your_Book.final.md
```

## Settings Management

### Configuration Commands
```bash
# Show current settings
xsarena settings show

# Normalize config
xsarena settings config-check

# Capture bridge IDs (if feature enabled)
xsarena settings config-capture-ids
```

## Translation Pipeline

### EPUB to Markdown Translation
1. Convert EPUB to Markdown:
   ```bash
   pandoc "input.epub" -t markdown -o book.md --wrap=none
   ```

2. Split chapters:
   ```bash
   xsarena utils tools export-chapters book.md --out ./chapters
   ```

3. Translate with Bilingual mode (see docs/WORKFLOWS.md for details)

## First-Run Checklist

1. Show current settings: `xsarena settings show`
2. Normalize config: `xsarena settings config-check`
3. Start bridge: `xsarena ops service start-bridge-v2`
4. Open your model page in Firefox and add #bridge=5102 (or your configured port)
5. Look for "Userscript connected" in bridge logs

## Architecture

### High-level layout
- CLI (Typer) surface: src/xsarena/cli/*
- Core runtime: src/xsarena/core/*
  - Orchestrator + Prompt layer + Jobs (manager/executor/scheduler/store) + State + Backends
- Bridge server: src/xsarena/bridge_v2/*
- Modes (specialized front-ends): src/xsarena/modes/*
- Utilities: src/xsarena/utils/*
- Directives (prompt templates, overlays): directives/

### Key Components
- **CLI (Typer)**: Single source of truth for commands
- **Orchestration**: Manages run specs, prompt composition, and job execution
- **Jobs**: Handles job lifecycle (submit, execute, manage, store)
- **Backends**: Manages transport to AI models (bridge-first default)
- **Bridge**: FastAPI server for local bridge communication
- **Modes**: Specialized UI layers over the engine
- **Utilities**: Analysis, processing, and helper tools

## Operating Model

- Single source of truth: Typer CLI (also reused in /command REPL)
- Orchestrator composes system_text from templates + overlays; JobManager submits; JobExecutor loops (anchors + hints + micro-extends)
- Backends via transport factory; bridge-first default
- Artifacts: .xsarena/jobs/<id> (job.json + events.jsonl + outputs); run manifests saved
- Snapshots via txt (share) or write (ops/debug); verify gate ensures health

## Project Philosophy

### Goals
- Produce high-quality, long-form output reliably with deterministic flows
- Keep users in control (local bridge + browser userscript)
- Make operations agent-friendly and non-interactive
- Enable lean, redacted snapshots for sharing

### Non-goals
- Heavy GUIs; everything should be operable via CLI (and optional /command REPL)
- Cloud-only operation (bridge-first is the default, not SaaS-first)

### Principles
- Secure-by-default bridge (loopback bind, constant-time token checks, /internal gated if configured)
- Single source of truth: Typer CLI (also reused by interactive /command)
- Declarative prompt composition (bases + overlays + extra files)
- Deterministic jobs (resume = last_done+1; prefer hints over anchors)
- Verify before share (snapshot preflight/postflight audit)
