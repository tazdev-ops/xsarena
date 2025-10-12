# Agent Shortcuts and Modes

This document contains quick reference shortcuts and command modes for the CLI agent.

## Text Shortcuts & Modes
See CLI_AGENT_RULES.md Appendix — Text Shortcuts & Modes for the complete list of available shortcuts.

## Common Commands Reference

### Startup & Context
- `STARTUP` - Initialize context and show project overview
- `SNAPSHOT` - Create project snapshot
- `HYGIENE` - Safe cleanup of temporary files
- `HEALTH` - Run health checks

### Modes
- `MODE: SAFE` - Conservative changes only
- `MODE: LEARN_MANUAL` - Process manual instructions
- `MODE: INGEST_ACT` - Process arbitrary text input
- `STOP_ON_LOOP` - Enforce anti-loop behavior

### Runbooks
- `RUNBOOK: MASTERY` - Long comprehensive book generation settings
- `RUNBOOK: LOSSLESS-FIRST` - Corpus to synthesis to book pipeline

## Suggestion-Reviewing Process (New Addition)
When giving suggestions that may be reusable in the future:
1. First add the suggestion to this shortcuts ecosystem (as appropriate)
2. Then implement the suggestion with proper verification
3. Follow the 5-step verification process:
   - Verify suggestions against actual codebase
   - Validate fixes are appropriate for current structure
   - Test fixes if possible before recommending
   - Document problem and solution clearly
   - Prioritize by impact and feasibility

## Quick Reference Commands
- `REPORT: SUCCESS` - Success report format
- `REPORT: BLOCKED` - Blocked report format
- `REPORT: RISK` - Risk assessment report format
