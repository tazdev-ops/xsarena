# XSArena Agent Manual

Purpose
Operate and maintain the repository, run jobs, keep docs and layout consistent, and prepare snapshots for higher AI review.

Golden rules
- Always self-heal first: xsarena fix run; xsarena backend ping; xsarena doctor run
- Never commit ephemeral artifacts (see TTL rules). Mark one-off scripts with header:
  # XSA-EPHEMERAL ttl=3d
- Before runs: ensure books/ finals/outlines/flashcards exist; bridge is healthy
- After runs: sweep ephemeral; update docs if CLI changed; produce a minimal snapshot on request

Directory rules
- books/
  - finals/: *.final.md, *.manual.en.md
  - outlines/: *.outline.md
  - flashcards/: *flashcards*.md
  - archive/: tiny/duplicates/old
- directives/
  - _rules/rules.merged.md is canonical; sources live in _rules/sources/
  - roles/: role.*.md
  - quickref/: agent_quickref*.md
  - prompts/: prompt_*.txt
- review/: probes (TTL 7d default, cleanable)
- .xsarena/: jobs/, logs/, snapshots/

Cleanup procedure (run after sessions)
1) Sweep (dry, then apply weekly):
   xsarena clean sweep
   xsarena clean sweep --apply
2) Declutter (content moves, idempotent):
   APPLY=1 bash scripts/declutter_phase2.sh
   APPLY=1 bash scripts/apply_content_fixes.sh
3) Dedupe outlines by hash (optional; keep newest):
   xsarena project dedupe-by-hash --apply (preferred over shell scripts)
   # Alternative: APPLY=1 bash scripts/normalize_content.sh (or the provided dedupe snippet)

Snapshot rules
- Minimal code snapshot for remote help:
  python tools/min_snapshot.py out.txt
- Use tools/min_snapshot.py only (simple, deterministic). Do not include books outputs unless asked.

Docs update procedure (when CLI changes)
1) If any CLI module under src/xsarena/cli/ changed, regenerate help:
   bash scripts/gen_docs.sh
2) If commands changed: update README “Key commands” section minimally
3) Re-merge rules if any source changed:
   bash scripts/merge_session_rules.sh
4) Commit with: docs: update help + rules

Investigation flow (when errors occur)
1) Capture environment and bridge health:
   xsarena backend ping; xsarena doctor run
2) Capture failing command and full stderr/stdout
3) Generate minimal snapshot:
   python tools/min_snapshot.py xsa_min_snapshot.txt
4) Produce a short report (what changed, expected/actual, logs)
5) If unresolved, attach snapshot and report for higher AI

Runbook examples
- Long UK elections/parties run:
  xsarena run book "Political History of the UK — Elections and Parties (c. 1832–present)" \
    --base zero2hero --no-bs --narrative --no-compressed \
    --max 30 --min 5800 --passes 3 \
    --out ./books/finals/political-history-of-the-uk.elections.final.md

- Preview + sample:
  xsarena preview run recipes/clinical.en.yml --sample
