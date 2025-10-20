# Deprecated Commands

This document tracks commands that have been removed from XSArena as part of the cleanup process.

## Removed Snapshot Commands (2025-10-20)

The following legacy snapshot commands were removed as they were no longer functional or maintained:

- `xsarena ops snapshot legacy-write` - Legacy snapshot command
- `xsarena ops snapshot legacy-txt` - Legacy flat pack command
- `xsarena ops snapshot legacy-simple` - Legacy simple command

### Migration Path

Use the current snapshot commands instead:

- `xsarena ops snapshot create` - Create a flat snapshot, ideal for chatbot uploads (recommended)
- `xsarena ops snapshot debug-report` - Generate a verbose snapshot for debugging
- `xsarena ops snapshot verify` - Verify snapshot health

### Reason for Removal

These commands were:
- No longer functional in the current codebase
- Superseded by better alternatives
- Creating confusion in documentation and user experience
