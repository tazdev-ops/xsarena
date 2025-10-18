# Orders Log (append-only)
# Append "ONE ORDER" blocks here after each major instruction.

# ONE ORDER: Communication Procedures for Higher AI
- Save "Communication Rules for Higher AI" into docs/HIGHER_AI_COMM_PROTOCOL.md
- Re-merge rules so the canonical file includes CLI agent rules
- Generate a "missing-from-assistant" snapshot that lists and inlines contents of files not seen yet
- Confirm rules coverage with: fgrep -n "CLI Agent Rules" directives/_rules/rules.merged.md
- Tasks completed: 1) Created docs/HIGHER_AI_COMM_PROTOCOL.md, 2) Verified merge script includes CLI agent rules, 3) Generated missing files snapshot at review/missing_from_assistant_snapshot.txt, 4) Confirmed CLI Agent Rules in merged file
# ONE ORDER — Pre‑Snapshot Cleanup Policy (project root + chunks dir + home)
Date (UTC): 2025-10-14 23:43:11
Intent:
- Before any snapshot or situation report, remove stale snapshot outputs to avoid drift or duplication.
- Clean only:
  - Project root (top-level files): situation_report.*.txt/health/part*, xsa_snapshot_pro*.txt(.tar.gz), xsa_min_snapshot*.txt, xsa_final_snapshot*.txt, xsa_final_cleanup_snapshot*.txt
  - Chunks dir: snapshot_chunks/ (files inside; remove dir if empty)
  - Home (~, top-level files only): xsa_min_snapshot*.txt, xsa_snapshot_pro*.txt(.tar.gz), situation_report.*.txt/part*
- Do not touch subdirectories of ~ or other project subdirectories (review/, docs/, .xsarena/).

Notes:
- This order is additive and must run first in any snapshot/situation-report workflow.
- Redaction/snapshotting code remains unchanged by this order.


# ONE ORDER — Snapshot Healthcheck and Cleanup Policy
Date (UTC): 2025-10-15 20:52:00
Intent:
- Before running any snapshot utility, clean existing snapshot outputs to prevent stale/included data
- Include project source, configuration, and documentation; exclude generated content like books/finals
- Verify snapshot contains required sections and has reasonable size
- Maintain snapshot hygiene through automated healthchecks

Specific Requirements:
1. Clean existing snapshots: remove all snapshot_*.txt files from .xsarena/snapshots/ and project root
2. Include: src/, directives/, recipes/, scripts/, docs/, config files, rules, tools/
3. Exclude: books/finals/, books/outlines/, other generated output content
4. Verify: directory trees, health checks, and footer are present
5. Check: size should be between 50KB-500KB (not too small, not including massive outputs)

Implementation:
- Run cleanup before each snapshot operation
- Use `xsarena snapshot write --dry-run` for automated verification
- Follow inclusion/exclusion patterns in tools/snapshot_txt.py
- Maintain reasonable chunk sizes (default 120KB, max ~400KB per chunk)

Rationale:
- Prevents inclusion of stale snapshot outputs in new snapshots
- Keeps snapshots focused on project state rather than generated content
- Ensures snapshot utility reliability and consistency
- Maintains appropriate snapshot sizes for processing and sharing

# ONE ORDER — Cockpit Prompt Commands
- Add /prompt.show, /prompt.style <on|off> <name>, /prompt.profile <name>, /prompt.list, /prompt.preview <recipe>.
- Runs must honor selected overlays and profile (compose overlays + extra into system_text).
- Persist overlays_active and active_profile in .xsarena/session_state.json settings.
- Default overlays: narrative + no_bs when none are set.
