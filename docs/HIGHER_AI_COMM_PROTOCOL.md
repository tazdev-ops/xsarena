# Communication Rules for Higher AI

1) Use the Canonical Rules File
- Reference directives/_rules/rules.merged.md — the canonical, merged source that includes:
  - CLI agent rules and guidelines
  - Orders log
  - Style directives
  - Role definitions

2) Communication Protocol
1. xsarena boot read        # Read current startup plan
2. xsarena adapt inspect    # Check for any system drift
3. xsarena report quick --book <relevant_file>  # Generate a diagnostic bundle when needed

3) For Complex Instructions
- Use the "ONE ORDER" format (see canonical rules)
- Append major instructions to directives/_rules/sources/ORDERS_LOG.md
- Run bash scripts/merge_session_rules.sh to update the merged rules
- Use xsarena checklist status to verify implementation completeness

4) Verification Commands
- xsarena checklist status
- xsarena boot read
- xsarena snapshot write
- xsarena report quick

5) Low AI Reliability Note
- The lower AI (CLI agent) can be unreliable and may lose context. Always:
  - Cross‑reference with docs/IMPLEMENTATION_CHECKLIST.md
  - Verify with xsarena checklist status
  - Treat directives/_rules/rules.merged.md as authoritative

6) Emergency Procedures
- If instructions conflict:
  - xsarena checklist status
  - Re‑read canonical rules (directives/_rules/rules.merged.md)
  - xsarena snapshot write to capture state before changes