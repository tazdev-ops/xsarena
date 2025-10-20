# Higher AI Communication Protocols v1

This document describes the three-agent communication protocols for the User ↔ CLI Agent ↔ Higher AI flow.

## Overview

The communication protocols provide structured ways to:
- Generate diagnostic reports (`report`)
- Prepare clean handoff packages for higher AI (`handoff`)
- Manage orders and directives (`orders`)

## Commands

### Report Commands

Generate diagnostic reports for analysis or handoff:

```bash
# Quick diagnostic report with optional book and job info
xsarena report quick [--book <path>] [--job <id>]

# Detailed job-specific report
xsarena report job <job_id>

# Full debug report with pro snapshot
xsarena report full [--book <path>]
```

### Handoff Commands

Prepare packages for higher AI with clean context:

```bash
# Prepare a handoff package with snapshot and brief
xsarena ops handoff prepare [--book <path>] [--job <id>] [--note <text>]

# Add notes to the latest handoff request
xsarena ops handoff note <text>

# Show the latest handoff package details
xsarena ops handoff show
```

### Orders Commands

Manage ONE ORDER directives:

```bash
# Create a new order with title and optional body
xsarena ops orders new "Title" [--body <path>]

# List recent orders
xsarena ops orders ls
```

## Examples

Quick report with book:
```bash
xsarena report quick --book books/my_book.md
```

Prepare handoff for debugging:
```bash
xsarena ops handoff prepare --note "Job stuck in retry loop" --job abc123
```

Create a new order:
```bash
xsarena ops orders new "Fix authentication flow"
```

## File Locations

- Reports: `review/report_*.md`
- Handoffs: `review/handoff/handoff_*/`
- Orders: `directives/_rules/sources/ORDERS_LOG.md`
