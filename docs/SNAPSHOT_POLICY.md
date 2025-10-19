# Snapshot Policy

## Purpose
A snapshot is a text-only representation of the project for debugging and sharing with higher AI systems. It includes tree structure and relevant files while excluding generated content and sensitive data.

## Standard Snapshot Content
- Source code (src/, directives/, data/, playbooks/, recipes/)
- Configuration files (pyproject.toml, README.md, LICENSE, etc.)
- Project structure information
- Excludes: books/, .git/, __pycache__/, build artifacts, large/binary files

## Standard Snapshot Command
```
xsarena snapshot run
```

For chunked output (recommended for large projects):
```
xsarena snapshot run --chunk
```

## SNAPSHOT+JOBS Extension
When debugging specific job issues, include minimal job context:

**Include on demand**: `.xsarena/jobs/<job_id>/events.jsonl` and `job.json`
**Do not include**: Full section outputs or other large artifacts unless specifically requested

**Command**:
```
# Create standard snapshot + job context
xsarena snapshot run
# Then manually include job.json and events.jsonl if needed for debugging
```

## Quality Checklist
- Includes: src/, directives/, data/, playbooks/, recipes/, top-level config
- Excludes: books/, .git/, __pycache__/, build/dist/node_modules/, large/binary files
- Files readable; chunk sizes reasonable; no stray footer/prompts in chunks
- If snapshot is missing expected files: ensure you ran from project root

## Troubleshooting
- Empty or tiny snapshot: rerun from project root
- Strange chunk footers: use the built-in chunker with --chunk flag
- Sensitive data: if secrets appear, re-run with appropriate redaction

## JobSpec-First Integration
When debugging JobSpec-related issues, ensure your snapshot includes:
- recipes/ directory (for JobSpec files)
- .xsarena/jobs/<job_id>/job.json (for job configuration)
- .xsarena/jobs/<job_id>/events.jsonl (for execution events)
- src/xsarena/core/jobs2.py (for runner implementation)

## Pro Snapshot (Advanced)
The pro snapshot tool (`tools/snapshot_pro.py`) provides enhanced debugging capabilities:

**Features**:
- System information (Python version, platform, working directory)
- Git status and branch information
- Directory trees and listings for specified paths
- Code manifest with SHA-256 hashes for all Python files
- Canonical rules digest (first 200 lines of rules.merged.md)
- Comprehensive job summaries with events
- Redacted configuration and session state
- Recipe and book content samples
- Review artifacts inclusion
- Combined snapshot digest for integrity verification

**Usage**:
```bash
# Using the CLI command (recommended)
xsarena ops snapshot pro

# With custom options via CLI
xsarena ops snapshot pro --out /tmp/snapshot.txt --max-inline 100000

# Direct script usage
python tools/snapshot_pro.py
python tools/snapshot_pro.py --out /tmp/snapshot.txt --max-inline 100000
```

**When to use**: For complex debugging scenarios requiring comprehensive system state, especially when escalating to higher AI systems or for detailed analysis of multi-component issues.
