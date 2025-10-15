# XSArena

## Mission
XSArena is a human writer workflow tool that bridges to LMArena for long-form content creation. It focuses on providing a structured approach to writing books, manuals, and other long-form content with AI assistance.

## Quick Start

1. Install the userscript (`xsarena_bridge.user.js`) and open LMArena in your browser
2. Start the bridge server: `xsarena service start-bridge-v2` (port 5102)
3. Run a book: `xsarena run book "Your Topic" --length standard --span medium`
4. For browser connection, set `#bridge=5102` in the URL (or use the default port 5102)

> Note: For legacy bridge v1 users, you can still run `xsarena service start-bridge-v1` (port 8080).

## Canonical Workflow
- Use `xsarena run book` as the single canonical path for all book generation
- For continued writing from existing files, use `xsarena continue start <file>`
- For project management, use `xsarena project ...` commands — AI Writing, Study, and CLI Studio

Bridge‑first, long‑form authoring with strict continuation and dense, readable chunks. Use it to generate books, outlines, pedagogy rewrites, flashcards, and structured analysis.

Highlights
- Bridge-first backend (local server + browser userscript), OpenRouter optional
- Continuation via anchors; micro-extends to hit target length per chunk
- Strong style overlays (narrative, no‑BS), repetition guard, coverage hammer
- Jobs runner with autopilot + events; recipes and mixer/fast workflows
- Deterministic snapshots; minimal snapshot tool for sharing state

Install
- Python 3.9+ recommended
- pip install -e ".[dev]"
- Start the bridge:
  - xsarena service start-bridge
  - In the browser (lmarena.ai), add #bridge=8080 to the URL

Quick start (Bridge)
- Health + self-heal:
  - xsarena backend ping
  - xsarena fix run
- UK elections/parties run (long, dense, narrative not compressed):
  xsarena fast start "Political History of the UK — Elections and Parties (c. 1832–present)" \
    --base zero2hero --no-bs --narrative --no-compressed \
    --max 30 --min 5800 --passes 3 \
    --out ./books/finals/political-history-of-the-uk.elections.final.md

Key commands
- Book mode: xsarena book zero2hero "Topic"
- Mixer (compose/edit system text then run): xsarena mix start "Subject" --edit
- Jobs (run recipe): xsarena jobs run recipes/subject.yml --apply
- Snapshot (code-only minimal snapshot): python tools/min_snapshot.py
- Cleanup (TTL-based sweeper): xsarena clean sweep --dry  (then add --apply)
- Doctor: xsarena doctor run
- Self-heal: xsarena fix run

Recipes and prompts
- Drop recipes in ./recipes/*.yml (examples in repo)
- Mixer writes prompt previews to directives/_mixer/
- Preview a recipe and generate a real sample:
  xsarena preview run recipes/clinical.en.yml --sample

File layout (content)
- books/
  - finals/       … final outputs (.final.md, .manual.en.md)
  - outlines/     … outlines (.outline.md)
  - flashcards/   … flashcards
  - archive/      … tiny/old/duplicates
- directives/
  - _rules/       … rules.merged.md (canonical); sources in _rules/sources/
  - roles/        … role.*.md
  - quickref/     … agent_quickref.*.md
  - prompts/      … prompt_*.txt
- review/         … probes (safe to delete; TTL-based cleanup)
- .xsarena/       … jobs, logs, snapshots, tmp

Housekeeping
- Mark one-off helpers with header: # XSA-EPHEMERAL ttl=3d
- Sweep periodically:
  xsarena clean sweep --dry
  xsarena clean sweep --apply
- Clean content layout (idempotent):
  APPLY=1 bash scripts/apply_content_fixes.sh
  APPLY=1 bash scripts/declutter_phase2.sh

Troubleshooting
- Bridge not responding → xsarena backend ping; xsarena doctor run
- Chunk too short → increase --min and --passes
- Too listy → narrative on; compressed off; passes 0–1
- Repeats or restarts → ensure cont.mode anchor; keep coverage hammer on
- Before sharing state → xsarena fix run; python tools/min_snapshot.py

Contributing
- Code style: Ruff/Black, type hints
- Tests: pytest -q
- Docs regen: see scripts/gen_docs.sh