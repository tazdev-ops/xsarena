# Shortcuts & Modes (Agent One‑Pager)

## STARTUP: status + layout; propose HYGIENE/SNAPSHOT/HEALTH.

## SNAPSHOT: xsarena snapshot run; verify; path(s).

## HYGIENE: list → ask → delete safe targets → report.

## HEALTH: xsarena doctor env; optional smoke.

## MODE: LEARN_MANUAL: read, adapt, small changes; report.

## MODE: INGEST_ACT: harvest useful tips into README/docs; propose risky ones.

## RUNBOOK: MASTERY: print commands only; don't run unless asked.

## STOP_ON_LOOP: stop after 3 failed attempts or 3 minutes; snapshot; ask.

## HISTORY
- Read last 40 lines of .xsarena/agent/journal.jsonl
- Summarize last session (what changed, failures, snapshot paths)
- Offer next actions: HYGIENE, SNAPSHOT, UPDATE_MANUAL, or a specific RUNBOOK

## MODE: HANDOFF
- Fill docs/HANDOFF.md before asking higher AI
- Include recent changes, failures, commands used, artifacts, and crisp ask
- Save to docs/handoff/HANDOFF_<timestamp>.md

## SNAPSHOT+JOBS
- Create snapshot as usual, but include minimal job context for the specified <job_id> (events.jsonl, job.json). Do not include full sections.

## HYGIENE-DRYRUN
- Only list what would be removed (no deletion). Ask for "y/n" confirmation to proceed.

## ASK/DECIDE
- Check docs/INBOX.md for ASK/DECIDE tags first on STARTUP
- Surface these priorities before other tasks# Runbooks

This document contains standard operating procedures and runbooks for common XSArena tasks.

## JobSpec-First Workflow (Recommended)

### 0. JobSpec Overview
**Purpose**: Use declarative YAML/JSON specifications as the single source of truth for all runs

**Benefits**:
- Repeatable and versionable runs
- Clear separation of configuration from execution
- Better reliability and observability
- Easier debugging and sharing

**Structure**:
- JobSpec contains: subject, styles, continuation settings, budgets, backends, output paths, aids
- All UX entries (CLI, web UI) build and submit JobSpecs
- Runner executes based on the spec, not user session state

## Quick Start Runbooks

### 1. Basic Zero-to-Hero Book Generation (JobSpec-First)
**Purpose**: Create a comprehensive book on a topic using the recommended JobSpec-first approach

**Steps**:
1. Prepare environment: `xsarena doctor env`
2. Generate JobSpec: `xsarena z2h "Your Topic" --print-spec > recipes/topic.yml`
3. Review and edit spec: `cat recipes/topic.yml` (optional)
4. Run with spec: `xsarena run.recipe recipes/topic.yml`
5. Monitor progress: `xsarena serve run` (optional, for live preview)
6. Check results: `xsarena jobs summary <job_id>`
7. Export when complete: `xsarena publish run <job_id> --epub --pdf`

**Alternative**: Generate spec via wizard
- `xsarena wizard z2h` - Interactive wizard that creates the JobSpec

**Expected duration**: Varies by topic complexity and length settings

### 2. Multi-Subject Processing
**Purpose**: Process multiple subjects sequentially

**Steps**:
1. Prepare subjects: Format as `"Subject A; Subject B; Subject C"`
2. Run command: `xsarena z2h-list "Topic A; Topic B; Topic C" --max=4 --min=2500`
3. Monitor with: `xsarena jobs log <job_id>`
4. Review results: `xsarena jobs summary <job_id>`

## Advanced Runbooks

### 3. Lossless-First Workflow
**Purpose**: Build content from source materials with lossless processing

**Steps**:
1. Prepare source corpus: `cat sources/topic/*.* > sources/topic_corpus.md`
2. Create synthesis: `xsarena lossless ingest sources/topic_corpus.md books/topic.synth.md --chunk-kb 100 --synth-chars 16000`
3. Lossless rewrite: `xsarena lossless rewrite books/topic.synth.md books/topic.lossless.md`
4. Generate pedagogical content: `xsarena z2h "Topic" --out=./books/topic.final.md`
5. Create study aids: `xsarena flashcards from books/topic.lossless.md`, `xsarena glossary from books/topic.lossless.md`, etc.

### 4. Mastery-Level Content Creation
**Purpose**: Create maximally comprehensive content equivalent to master's level depth

**Settings**:
- Style: compressed narrative (no lists/checklists/drills)
- Continuation: anchor mode with 4200+ min chars
- Passes: 2 push passes
- Hammer: enabled for coverage
- Length: 20+ chunks for depth

**Commands**:
```
xsarena z2h "Your Topic" --out=./books/topic.final.md --max=24 --min=4200
# During run, apply:
/style.compressed on
/out.passes 2
/out.hammer on
/repeat.warn on
```

### 5. Job Recovery & Management
**Purpose**: Handle stuck, failed, or interrupted jobs

**Steps**:
1. List jobs: `xsarena jobs ls`
2. View job log: `xsarena jobs log <job_id>`
3. If job is stuck: `xsarena jobs cancel <job_id>`
4. If job needs continuation: `xsarena jobs resume <job_id>`
5. If job needs different backend: `xsarena jobs fork <job_id>`

**Troubleshooting**:
- If repeating: `/repeat.warn on` and `/repeat.thresh 0.35`
- If too short: increase `/out.minchars`
- If formatting wrong: `/style.compressed on` or `/style.narrative on`

## Study Tool Runbooks

### 6. Exam Preparation Kit
**Purpose**: Create comprehensive study materials from source content

**Steps**:
1. Start with source content (manual, synthesis, or lossless rewrite)
2. Create cram guide: `xsarena exam cram "Your Topic"`
3. Generate flashcards: `xsarena flashcards from books/topic.source.md books/topic.flashcards.md --n 220`
4. Create glossary: `xsarena glossary from books/topic.source.md books/topic.glossary.md`
5. Build index: `xsarena index from books/topic.source.md books/topic.index.md`
6. Combine into study package

### 7. Quality Assurance Run
**Purpose**: Evaluate and improve content quality

**Steps**:
1. Score content: `xsarena quality score books/topic.content.md`
2. Check uniqueness: `xsarena quality uniq books/topic.content.md`
3. Apply improvements based on scores
4. Re-score to verify improvements

## Service & Monitoring Runbooks

### 8. Local Web Preview Setup
**Purpose**: Set up local web interface for monitoring and preview

**Steps**:
1. Start server: `xsarena serve run` (default: http://127.0.0.1:8787)
2. Open browser to view books and job artifacts
3. Monitor live job events via the web interface
4. Use the dashboard to set budgets and add comments

### 9. Export & Publishing Pipeline
**Purpose**: Convert finished content to portable formats

**Prerequisites**:
- Install Pandoc: `apt install pandoc` (Linux), `brew install pandoc` (macOS), `winget install JohnMacFarlane.Pandoc` (Windows)

**Steps**:
1. Ensure job is complete: `xsarena jobs summary <job_id>`
2. Export formats: `xsarena publish run <job_id> --epub --pdf`
3. Verify outputs in books/ directory
4. Optional: Convert to audio: `xsarena audio run <job_id> --provider edge`

## Troubleshooting Runbooks

### 10. Common Issue Resolution
**Issue**: Unknown command for density knobs in PTK
- Solution: Run without PTK: `XSA_USE_PTK=0 xsarena`

**Issue**: Output not strictly English
- Solution: Add "English only" to system prompt

**Issue**: Model repeats content
- Solution:
  - `/book.repeat-warn on`
  - `/book.repeat-thresh 0.35`
  - Lower `/book.passes`
  - Reduce `/book.minchars`

**Issue**: Content too dense/terse
- Dense: `/book.budget off`, `/book.minchars 2500-3200`, `/book.passes 0-1`
- Terse: `/book.budget on`, `/book.minchars 4500-5200`, `/book.passes 2-3`

### 11. Performance Optimization
**Purpose**: Optimize generation for speed and quality

**Settings by goal**:
- **Speed**: Lower `/book.minchars`, fewer `/book.passes`, simpler style
- **Quality**: Higher `/book.minchars`, more passes, narrative style
- **Density**: `/book.budget on`, `/book.minchars 4500+`, compressed style
- **Flow**: `/style.narrative on`, anchor continuation, repetition guard

## Emergency Procedures

### 12. Job Emergency Stop
**When**: Job is producing incorrect content or consuming too many resources

**Steps**:
1. Identify job: `xsarena jobs ls`
2. Stop immediately: `xsarena jobs cancel <job_id>`
3. Preserve artifacts: Check `.xsarena/jobs/<job_id>/` for partial results
4. Adjust settings and restart if needed

### 13. System Health Check
**When**: Before starting large jobs or when experiencing issues

**Steps**:
1. Environment check: `xsarena doctor env`
2. Optional smoke test: `xsarena doctor run --subject "Smoke" --max 2 --min 800`
3. Check disk space: `df -h .`
4. Verify API keys and backend connectivity

## Backend-Specific Runbooks

### 14. Bridge Backend (Browser-based)
**Setup**:
1. Start CLI: `xsarena`
2. Open https://lmarena.ai with userscript
3. In CLI: `/capture`
4. Click Retry in browser once
5. Verify with `/status`

### 15. OpenRouter Backend (Direct API)
**Setup**:
1. Set API key: `export OPENROUTER_API_KEY=...`
2. In CLI: `/backend openrouter`
3. Set model: `/or.model openrouter/auto`
4. Verify: `/or.status`

## Experimental Features Runbooks

### 16. Coder Mode Session
**Purpose**: Advanced coding with tickets, patches, and git integration

**Steps**:
1. Start session: `xsarena coder start`
2. Create ticket: `xsarena coder ticket "Description"`
3. Get next step: `xsarena coder next`
4. Apply patch: `xsarena coder patch`
5. Test changes: `xsarena coder test`
6. Review diff: `xsarena coder diff`

### 17. Multi-Agent Pipeline
**Purpose**: Use Outliner → Writer → Editor → Continuity agents

**Command**: `xsarena z2h "Topic" --playbook z2h_multi`

**Note**: Each stage improves content quality and consistency.

## Snapshot & Backup Runbooks

### 18. Project State Capture
**Purpose**: Create project snapshot for debugging or backup

**Commands**:
- Basic: `xsarena snapshot run`
- Chunked: `xsarena snapshot run --chunk`
- With jobs: `xsarena snapshot run` (include .xsarena/jobs/<job_id>/events.jsonl and job.json when requested)

### 19. Environment Verification
**Purpose**: Verify complete system functionality

**Steps**:
1. `xsarena doctor env` - Check environment
2. `xsarena jobs ls` - Check job system
3. `xsarena serve run` - Test web server (optional)
4. `xsarena snapshot run` - Test snapshot utility

## Roleplay & Coaching Runbooks

### 20. Roleplay Session Setup
**Purpose**: Start interactive roleplay sessions

**Commands**:
- List personas: `xsarena rp list`
- Start session: `xsarena rp start`
- Speak as persona: `xsarena rp say`
- Set boundaries: `xsarena rp bounds`
- Export session: `xsarena rp export`

### 21. Coaching Session
**Purpose**: Engage in structured learning with drills and exams

**Commands**:
- Start session: `xsarena coach start`
- Take quiz: `xsarena coach quiz`
- Boss exam: `xsarena coach boss`
- Track progress: `xsarena joy streak`, `xsarena joy achievements`

## How to Get a Canonical JobSpec

### Method 1: Using --print-spec flag
Generate a complete JobSpec from any z2h command:
```
xsarena z2h "Your Topic" --max=6 --min=3000 --print-spec
```
This will print the canonical YAML specification to stdout. You can redirect it to a file:
```
xsarena z2h "Your Topic" --max=3000 --print-spec > recipes/my_topic.yml
```

### Method 2: Using the wizard
The interactive wizard creates a JobSpec for you:
```
xsarena wizard z2h
```

### Method 3: Template approach
Create a JobSpec manually using this template:

```yaml
task: book.zero2hero
subject: "Your Topic"
styles: [narrative]  # or [compressed] for mastery-style
continuation:
  mode: anchor
  minChars: 3000
  pushPasses: 1
  repeatWarn: true
budget:
  default_usd: 5.00
io:
  output: file
  outPath: "./books/topic.final.md"
max_chunks: 6
aids: [cram, flashcards, glossary, index, audio]
prelude:
  - "/style.narrative on"
system_text: |
  English only. Teach-before-use. Narrative transitions.
```

## Profile Examples

### Mastery Profile (Dense, Comprehensive)
```yaml
styles: [compressed]
continuation:
  mode: anchor
  minChars: 4200
  pushPasses: 2
system_text: |
  English only. Dense narrative prose. Avoid lists/checklists/drills.
```

### Pedagogy Profile (Teaching-Focused)
```yaml
styles: [narrative]
continuation:
  mode: anchor
  minChars: 3000
  pushPasses: 1
system_text: |
  English only. Teach-before-use approach. Include examples and quick checks.
```

### Reference Profile (Terse, Factual)
```yaml
styles: [nobs]
continuation:
  mode: anchor
  minChars: 2500
  pushPasses: 0
system_text: |
  English only. Concise, factual presentation. Minimal explanation.
```

---

**Note**: Always run `xsarena doctor env` before starting major operations to verify system health.
