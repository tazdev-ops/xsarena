# Important Files and Directories

## Project Structure
This document describes the key files and directories in the XSArena project and their purposes.

## Top-Level Directories
- `books/` - Output files (manuals, cram guides, flashcards, glossaries, indexes)
- `sources/` - Input corpora organized by topic
- `directives/` - System directives and templates
- `data/` - Blueprints, resource maps, tag maps
- `recipes/` - YAML/JSON plans for job execution
- `legacy/` - Deprecated LMA-era shims with deprecation warnings
- `contrib/` - Optional UIs and contributed tools
- `.xsarena/` - Local state (checkpoints, macros, jobs, agent journal)

## Configuration Files
- `pyproject.toml` - Project dependencies and configuration
- `.gitignore` - Files and directories to ignore in Git
- `README.md` - Main project documentation

## Core Source Files
- `src/xsarena/cli/main.py` - Main CLI entry point
- `src/xsarena/core/jobs2.py` - Job management system
- `src/xsarena/utils/snapshot_v2.py` - Snapshot utilities
- `src/xsarena/bridge/` - Bridge server implementations

## Agent Journal
- `.xsarena/agent/journal.jsonl` - Agent session log for continuity
- `.xsarena/agent/session_*.md` - Session-specific notes

## Job Artifacts
- `.xsarena/jobs/*/job.json` - Job state and metadata
- `.xsarena/jobs/*/events.jsonl` - Job event log
- `.xsarena/jobs/*/sections/` - Job content sections
- `.xsarena/jobs/*/plan.json` - Job plan and outline

## Documentation
- `docs/` - Additional documentation files
- `docs/handoff/` - Handoff templates for communication
- `docs/_help_*.txt` - CLI help output cache
