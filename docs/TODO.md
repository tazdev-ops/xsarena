# XSArena TODO (Operator Concerns)

Snapshot Utility Issues
- Frustration: snapshot utility was malfunctioning and overly complex.
- Goal: Make it simpler and more reliable.
- Symptoms: Current snapshot utility creates large files (~966KB) with complex structure. Output goes to snapshot.txt file rather than stdout, which can be confusing. May be overly complex with multiple exclusions and inclusions.
- Desired: Easy, working snapshot that captures relevant code/state without bloat or errors.
- Status: RESOLVED - Simplified with 'create' command as primary option, 'debug-report' for verbose output, and legacy commands marked as deprecated.
- Priority: High - affects debugging and higher AI handoffs.

General
- [Add other todos here as needed]
