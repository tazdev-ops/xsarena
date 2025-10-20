# XSArena CLI Agent Command Generation Guide

## Overview
This document provides instructions for the CLI agent on how to generate and execute XSArena commands. The XSArena tool provides a comprehensive set of commands for AI-assisted content creation, job management, and system operations.

## Command Structure
XSArena commands follow the pattern: `xsarena [group] [subcommand] [options] [arguments]`

## Core Command Groups

### 1. Report Commands
Generate diagnostic reports for debugging and handoff preparation:

```bash
# Quick diagnostic report (most common)
xsarena report quick [--book <path>] [--job <id>]

# Job-specific detailed report
xsarena report job <job_id>

# Full debug report (comprehensive)
xsarena report full [--book <path>]
```

### 2. Handoff Commands
Prepare and manage handoff packages for Higher AI:

```bash
# Prepare a complete handoff package
xsarena ops handoff prepare [--book <path>] [--job <id>] [--note <text>]

# Add a note to the latest handoff
xsarena ops handoff note <text>

# Show the latest handoff package details
xsarena ops handoff show
```

### 3. Orders Commands
Manage ONE ORDER log for tracking instructions:

```bash
# Create a new order with title and body
xsarena ops orders new "Title" [--body <path>]

# List recent orders
xsarena ops orders ls
```

## Command Generation Best Practices

### 1. Before Executing Commands
- Always acquire appropriate locks if using multiple agents
- Check system health: `xsarena ops health`
- Verify bridge connectivity: `xsarena ops service start-bridge-v2`

### 2. Report Command Usage
- Use `xsarena report quick` for most debugging needs
- Include `--book <path>` when reporting book-related issues
- Include `--job <id>` when reporting job-specific issues
- Use `xsarena report job <job_id>` for detailed job analysis
- Use `xsarena report full` only when comprehensive analysis is required

### 3. Handoff Command Usage
- Use `xsarena ops handoff prepare --note "Description of issue"` to create a complete handoff package
- Include relevant book path with `--book <path>` if applicable
- Include job ID with `--job <id>` if related to a specific job
- Use `xsarena ops handoff show` to verify the handoff was created

### 4. Orders Command Usage
- Use `xsarena ops orders new "Title" --body <content>` to log important instructions
- Use `xsarena ops orders ls` to review existing orders

## Common Command Combinations

### For Issue Reporting:
```bash
# Generate a quick report for debugging
xsarena report quick --book path/to/book.md --job job_id

# Create a handoff with the report
xsarena ops handoff prepare --book path/to/book.md --note "Issue description"
```

### For Job Management:
```bash
# Check job status with report
xsarena report job job_id

# Follow job progress
xsarena ops jobs follow job_id

# Cancel problematic job
xsarena ops jobs cancel job_id
```

### For System Operations:
```bash
# Check system health
xsarena ops health

# Start bridge service
xsarena ops service start-bridge-v2

# List jobs
xsarena ops jobs list
```

## Error Handling and Recovery

### When Commands Fail:
1. Generate a quick report: `xsarena report quick`
2. Check system health: `xsarena ops health`
3. If needed, prepare a handoff: `xsarena ops handoff prepare --note "Error description"`

### For Stuck Operations:
1. Check active jobs: `xsarena ops jobs list`
2. Cancel if needed: `xsarena ops jobs cancel <job_id>`
3. Generate report: `xsarena report quick`

## Integration with Locking Protocol

When executing commands that modify state, use the locking protocol:

```bash
# Before running a snapshot operation
if tools/agent_locking_protocol.sh acquire snapshot_operation; then
    xsarena ops snapshot create --mode author-core --out ~/repo_flat.txt
    tools/agent_locking_protocol.sh release snapshot_operation
fi
```

## Quick Reference for Common Tasks

| Task | Command |
|------|---------|
| Generate diagnostic report | `xsarena report quick` |
| Create full debug report | `xsarena report full` |
| Prepare handoff | `xsarena ops handoff prepare --note "description"` |
| Add handoff note | `xsarena ops handoff note "note text"` |
| Create new order | `xsarena ops orders new "Title" --body "content"` |
| List orders | `xsarena ops orders ls` |
| Check job status | `xsarena report job job_id` |

## Safety Guidelines

1. **Always use appropriate locks** when multiple agents may be operating
2. **Generate reports** before escalating issues to Higher AI
3. **Include relevant context** (book paths, job IDs) in commands when applicable
4. **Check command help** with `--help` flag if uncertain about options
5. **Verify system health** before starting complex operations

## Command Verification

To verify any command's options and usage:
```bash
xsarena [group] [subcommand] --help
```

Example:
```bash
xsarena report quick --help
xsarena ops handoff prepare --help
xsarena ops orders new --help
```

This ensures you're using the most current command syntax and options.
