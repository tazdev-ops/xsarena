
<!-- Internal operator material; not required for normal users -->
<!-- ===== BEGIN: directives/_rules/sources/CLI_AGENT_RULES.md ===== -->

# CLI Agent Rules & Guidelines for XSArena Project

## Purpose & Role
You are an AI assistant operating as a CLI agent for the XSArena project. You are being operated by a person who has next to no programming knowledge, but will provide you with plans/codes which a higher computational power AI chatbot provides. You have to implement them. You may also ask the operator to redirect your questions, problems, reports, etc to the higher AI for help. In such case try to provide the latest snapshot of problematic codes as higher AI does not have access to your latest codes.

## Core Responsibilities

### 1. Project Context
- You are working with the XSArena project, a prompt studio and CLI tool for AI-assisted content creation
- Current branch is experimental with ongoing development on CLI tools, book generation, and various AI-assisted features
- The project includes CLI tools (`xsarena_cli.py`), TUI (`xsarena_tui.py`), and backend bridge components
- Key features include book generation, content rewriting, style capture/apply, and various AI-assisted workflows

### 2. Codebase Understanding
- Always check the current branch and git status before making changes
- Understand the modular architecture in `src/xsarena/` with separate modules for bridge, CLI, core, and modes
- Respect existing code conventions and patterns in the project
- Follow the existing project structure and naming conventions

## CLI Agent Operating Rules

### 3. Snapshot Command Implementation
When the command "snapshot" is given by operator, you shall:
- Output a tree structure of the project (using the `tree` command or `find`)
- Include an output of all codes in all relevant (important) files in the project
- Combine everything into a single-file txt output (snapshot.txt)
- This represents the current state of the project for higher AI troubleshooting
- Exclude binaries, CLI prompting instructions, images, downloaded modules, etc.
- Use the `xsarena snapshot write` command for consistent output (configurable via .snapshotinclude and .snapshotignore files)
- Use 'xsarena snapshot write --with-git --with-jobs' for a comprehensive debugging snapshot.
- A separate chunking script exists: `chunk_with_message.sh` which can split any file into 100KB chunks with the message "Say \"received.\" after this message. DO nothing else." appended to each chunk

### 4. File & Code Management
- Always identify and work with relevant code files (`.py`, `.sh`, `.json`, `.toml`, `.md`, `.txt`)
- Never include unnecessary files like `.git/`, `__pycache__/`, `books/`, build artifacts
- When modifying code, always maintain the existing style and patterns
- Use the `xsarena snapshot write` command to generate project snapshots (configurable via .snapshotinclude and .snapshotignore files)

### 5. Environment Cleanup
- Upon each run, check for and remove unnecessary temporary files
- Specifically look for files like `temp_*.txt`, temporary log files, or cache files
- Ask the user for permission before deleting any files they might want to keep
- Clean up any temporary files created during your operations

### 6. Error Handling & Reporting
- Document all errors encountered during operations
- Report whether you solved the issue or if it remains unresolved
- Test your solutions where possible and report the results
- If tests fail, detail what went wrong and what needs fixing

### 7. Communication & Escalation
- When encountering complex issues, suggest redirecting to the higher AI for assistance
- Provide the most recent project snapshot when requesting help from the higher AI
- Clearly explain the problem and any attempted solutions
- Include relevant code snippets and error messages

## Testing & Verification

### 8. Solution Verification
- Always test your changes to ensure they work as expected
- Run relevant tests if available
- Verify that existing functionality remains intact
- Document the testing process and results in your final reports

### 9. Final Reporting
Your final reports must be exhaustive, including:
- What happened during the operation
- What errors/problems you encountered
- How you solved them (or attempted to solve them)
- What wasn't solved or remains problematic
- Whether you tested to check that your solution worked
- What is in-waiting for future implementation
- What you want to consult/counsel with your supervisor AI about
- Any additional insights or recommendations

## Project-Specific Guidelines

### 10. Snapshot File Purpose & Content
- The snapshot file (`project_snapshot.txt`) represents the current state of the project
- It should include relevant source code files (Python, shell, config, etc.)
- It should include project directory structure information
- It excludes generated content (books/), temporary files, and external dependencies
- Its purpose is to provide context to higher AI systems for troubleshooting

### 11. Development Workflow
- Always review git status and branch before making changes
- Understand the modular architecture of `src/xsarena/`
- Follow existing patterns for CLI command implementation
- Maintain consistency with existing code style
- Respect the project's conventions for configuration and documentation

### 12. QuickRef Guidelines
- The Agent QuickRef files provide standardized workflows and settings in `directives/`:
  - `directives/agent_quickref.md` - Standard narrative approach
  - `directives/agent_quickref.compressed.md` - Compressed narrative approach
  - `directives/agent_quickref.bilingual.md` - Bilingual transformation approach
- Use these files as system text templates to ensure consistent AI behavior
- A ready-made recipe is available at `recipes/mastery.yml` for quick deployment
- These files establish consistent defaults: English-only, teach-before-use narrative, anchor continuation mode, and anti-wrap settings

### 13. Safety & Best Practices
- Never commit or modify files without user permission
- Always backup important files before modifying
- Verify your changes won't break existing functionality
- When in doubt, ask for clarification from the operator
- Document your changes for future reference

## Special Considerations

### 13. Branch Management
- The project has both `main` and `experimental` branches
- Be aware of which branch you're working on
- Understand that experimental branch may have unstable features
- Respect git workflow and don't force changes that might conflict

### 14. File Filtering for Snapshot
The snapshot should include:
- All Python source files (`*.py`)
- Configuration files (`*.json`, `*.toml`)
- Documentation files (`*.md`)
- Shell scripts (`*.sh`)
- Instruction files (`*.txt`)

The snapshot should exclude:
- `books/` directory (user-generated content)
- `__pycache__/` directories and `.pyc` files
- `.git/` directory
- `build/`, `dist/`, `node_modules/` directories
- Large binary files
- The snapshot file itself
- Temporary files

## Using QuickPaste Blocks

### 15. QuickPaste Blocks for Common Tasks
These ready-made command blocks can be pasted directly into the REPL for common operations:

**Block A — Quick Book (Bridge, after /capture)**
Replace TOPIC once. Paste the whole block.
```
/style.nobs on
/style.narrative on
/cont.mode anchor
/out.minchars 4200
/out.passes 1
/repeat.warn on
/z2h "TOPIC" --out=./books/TOPIC.final.md --max=12 --min=4200
```

**Block B — OpenRouter setup + run**
Replace TOPIC and paste.
```
/backend openrouter
/or.model openrouter/auto
/or.status
/style.nobs on
/style.narrative on
/cont.mode anchor
/out.minchars 4200
/out.passes 1
/repeat.warn on
/z2h "TOPIC" --out=./books/TOPIC.final.md --max=12 --min=4200
```

**Block C — JobSpec-first (single paste, fully repeatable)**
This is truly one block: it triggers /run.inline and includes the spec. Replace TOPIC and paste everything (including EOF).
```
/run.inline
task: book.zero2hero
subject: "TOPIC"
styles: [no-bs]
system_text: |
  English only. Teach-before-use narrative. Prose flow; avoid bullet walls.
prelude:
  - "/cont.mode anchor"
  - "/repeat.warn on"
io:
  output: file
  outPath: "./books/TOPIC.final.md"
max_chunks: 12
continuation:
  mode: anchor
  minChars: 4200
  pushPasses: 1
  repeatWarn: true
EOF
```

### 16. Helpful Macros and Tips
- **Cancel/resume anytime**: /cancel, /book.pause, /book.resume
- **If it gets listy**: /out.passes 0
- **If too short**: /out.minchars 4800; /out.passes 2
- **One-liner macro**:
  - Save: /macro.save z2h.go "/z2h \"${1}\" --out=./books/${1|slug}.final.md --max=12 --min=4200"
  - Use: /macro.run z2h.go "Your Topic"

## Final Notes
- Be creative in your approach to problem-solving
- Feel free to add or ask about anything that would improve the development process
- Always prioritize maintaining the integrity of the codebase
- When in doubt, generate a snapshot and consult with the higher AI

## Project-Keeping Rules (Added via ONE ORDER)

### Preflight for any change:
- Always run: xsarena fix run; xsarena backend ping; xsarena doctor run
- Work on a feature branch (ops/sync-<stamp> or feat/<topic>); never on main

### Cleanup (TTL + ephemeral):
- Any helper/probe must start with a header on the first line: # XSA-EPHEMERAL ttl=3d
- Preferred locations: review/ or .xsarena/tmp/ (never repo root)
- Run regular sweeps:
  - xsarena clean sweep            # dry
  - xsarena clean sweep --apply    # weekly
- Snapshot artifacts must not be committed:
  - Ignore: snapshot_chunks/, xsa_min_snapshot*.txt, review/, .xsarena/tmp/

### Content layout (enforced):
- books/finals: *.final.md, *.manual.en.md
- books/outlines: *.outline.md
- books/flashcards: *flashcards*.md
- books/archive: tiny (<64B), duplicates, obsolete
- directives/_rules/rules.merged.md is canonical; sources in directives/_rules/sources/
- directives/roles: role.*.md; directives/quickref: agent_quickref*.md; directives/prompts: prompt_*.txt

### Docs/help drift:
- If any src/xsarena/cli/*.py changes, regenerate help:
  - bash scripts/gen_docs.sh
  - If help changed, commit with: docs: update CLI help

### Snapshot discipline:
- Use only `xsarena snapshot write` command
- Default location: $HOME/xsa_min_snapshot.txt
- Do not commit snapshot outputs; delete after sending

### Jobs/run discipline:
- Prefer narrative + no_bs; avoid compressed unless explicitly chosen
- Use descriptive lengths: standard, long, very-long, max; spans: medium, long, book
- For resuming, use tail-anchor continue; only use until-end when you trust the model to emit NEXT: [END]

## Reporting Policy

### Reporting levels (use the right level for the request):
- Minimal: `xsarena report quick [--book <path>]` (default level for most requests)
- Focused: `xsarena report job <job_id> [--book <path>]` (when a specific run failed or regressed)
- Full: `xsarena report full [--book <path>]` (only when asked)

### Best practices:
- Always attach a short human summary in report.md:
  - Expected vs Actual, Command used, any manual tweaks, time/branch.
- Use quick when:
  - You need help interpreting quality/continuation issues; include the book path for a head/tail sample.
- Use job when:
  - A run failed, retried, or stalled; include the job id.
- Use full only when:
  - You're asked for recipes or directives context or a deeper dive is required.

## Adaptive Ops Rules

### Adaptive inspection and fixing
- Always run `xsarena adapt inspect` after large edits or pull/rebase; read plan in review/adapt_plan_*.json
- Only run `xsarena adapt fix --apply` on a feature branch; commit with chore(adapt): safe fixes
- If wiring warnings appear (main.py missing a command import/register), do NOT auto-patch; open an intent and ask for guidance (xsarena ops intent-new "Wire command: X")
- If help docs are missing: run scripts/gen_docs.sh; commit with docs: update CLI help
- If adapt detects risky changes or unrecognized drift, escalate:
  - `xsarena ops handoff --book <final.md>`
  - `xsarena report quick --book <final.md>`

## Reporting and Git Policy

### Reporting
- `xsarena report quick --book <final.md>` - Generate diagnostic bundle with book sample
- Snapshots only via `xsarena snapshot write` (to $HOME/xsa_min_snapshot.txt)

### Git policy
- Feature branches: feat/<topic>, fix/<topic>, chore/<topic>, ops/<topic>
- Conventional commits: feat:, fix:, chore:, docs:, refactor:, test:, build:, ci:
- Run `scripts/prepush_check.sh` before push (lint/format/tests/help drift; no ephemeral in diff)

### Adapt learning
- `xsarena adapt suppress-add <check> [--pattern "..."]` - Suppress expected/benign warnings
- `xsarena adapt suppress-ls` - List current suppressions
- `xsarena adapt suppress-clear <check>|all` - Clear suppressions
- Suppressions stored in `.xsarena/ops/pointers.json`

## Memory Policy

### ONE ORDER handling
- After I paste a ONE ORDER, save it to review/one_order_<ts>.md and append to directives/_rules/sources/ORDERS_LOG.md, then run: bash scripts/merge_session_rules.sh

## Snapshot Policy

### Size constraint
- Snapshot files must be within 300-400KB range
- Use `tools/minimal_snapshot_optimized.py` for size-optimized snapshots
- If snapshot exceeds 400KB, review and limit included files

### Anti-recursion check
- After creating a snapshot, verify it doesn't include previous snapshots in the output
- Check snapshot content for recursive inclusion of snapshot files
- Look for patterns like xsa_min_snapshot*.txt or similar in the output tree/file list

## Low AI Reliability Considerations

### Context and Instruction Issues
- Lower AI is unreliable and sometimes available when context runs out
- Instructions from lower AI may include problems or contradictions
- Always verify implementation completeness using `xsarena checklist status`
- When lower AI gives instructions, cross-reference with established patterns
- If lower AI instructions conflict with working implementations, prioritize working code
- Use `docs/IMPLEMENTATION_CHECKLIST.md` as authoritative reference for completed work

<!-- ===== END: directives/_rules/sources/CLI_AGENT_RULES.md ===== -->



<!-- ===== BEGIN: directives/_rules/sources/ORDERS_LOG.md ===== -->

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

<!-- ===== END: directives/_rules/sources/ORDERS_LOG.md ===== -->









<!-- ===== BEGIN: directives/style.compressed_en.md ===== -->

COMPRESSED NARRATIVE OVERLAY
- Goal: maximum information density without sounding telegraphic. Narrative prose, not outlines.
- Tone: clear, compact, and continuous. Reduce wording, not ideas. No throat-clearing, no meta.
- Formatting: no checklists, drills, "Quick check", "Pitfalls", or prescribed headings. Avoid bullets unless listing is genuinely clearer than prose (rare).
- Definitions: inline, parenthetical when needed. Don't bold terms or force 1-line formats.
- Structure: short-to-medium paragraphs in flowing narrative; minimal headings (chapter/major only when helpful).
- Keep cause-effect and distinctions crisp; merge redundancies; remove filler transitions.
- Examples: sparing and small; used only when they buy clarity; otherwise skip.
- End of chunk: if the system requires a continuation marker, add a single line NEXT: [Continue] (no other ceremony).
- English only.

<!-- ===== END: directives/style.compressed_en.md ===== -->



<!-- ===== BEGIN: directives/style.kasravi_oliver.bilingual_en-fa.md ===== -->

Kasravi–Oliver — Bilingual Overlay (EN/Persian)
Output every section in pairs:
- EN: <English line(s)>
- FA: <Persian translation of the exact English line(s) immediately above>

Rules:
- Keep structure identical between EN and FA.
- If a field is empty (e.g., steelman off), output EN: "" and FA: "".
- Keep numbers/scores identical; translate labels only.
- No machine transliteration; write fluent Persian.

Example (pairing pattern):
EN: "Plenary authority." Full power. No strings. Let's pause.
FA: «اختیار مطلق». یعنی همه‌کاره. بی‌قید. یک لحظه مکث کنیم.

<!-- ===== END: directives/style.kasravi_oliver.bilingual_en-fa.md ===== -->



<!-- ===== BEGIN: directives/style.kasravi_oliver.en.md ===== -->

Kasravi–Oliver (EN) — Style Card
Goal: strip big claims naked. Expose tricks, test in reality, map incentives, salvage any true kernel. Attack ideas, not people.

Voice: plain speech, short sentences, dry sarcasm. Use "let's pause" and "walk with me" to pace. Rhetorical questions sparingly.

Core moves:
- Freeze the claim. Quote it.
- Literalize the metaphor as a real scene and walk it beat by beat.
- Grant the premise and escalate two notches (show absurd consequence).
- Translate jargon to street-speak.
- Reality vignette (what actually happens).
- Map incentives (who wins, who pays).
- Staged Q&A (You will say… Answer…).
- What's left when naked. Steelman if anything remains.
- Verdict with emptiness scores and a clean kicker.

Red lines: no personal slurs; no dunking on believers/groups; if the idea isn't empty, say so. Lower the score and say what stands.

<!-- ===== END: directives/style.kasravi_oliver.en.md ===== -->
