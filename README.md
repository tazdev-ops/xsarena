# XSArena — AI Writing & Study Studio (CLI)

XSArena is a power-user studio for generating long‑form books, exam‑prep materials, and study aids with precise control over continuation, density, and style. It supports both a browser bridge backend (for use with LMArena) and a direct API backend (OpenRouter). It's built to be stable for long jobs and practical for real study pipelines.

- Status: Active development (production‑ready for CLI usage)
- Primary interface: CLI (xsarena)
- Optional: TUI (textual), GTK GUI (if implemented), AUR packaging

## Contents
- [Overview](#overview)
- [Key capabilities](#key-capabilities)
- [Installation](#installation)
- [Quick start (Bridge and OpenRouter)](#quick-start)
- [Essential workflows](#essential-workflows)
- [Command cheat sheet](#command-cheat-sheet)
- [Continuation, density, and style](#continuation-density-and-style)
- [Synthesis & lossless rewrite](#synthesis--lossless-rewrite)
- [Study tools & exam‑prep](#study-tools--exam‑prep)
- [Recipes (file and inline one‑shot)](#recipes)
- [Session management (resume, checkpoints, transplanting context)](#session-management)
- [Handling browser "waiting…" stalls](#handling-browser-waiting-stalls)
- [Project snapshot & support](#project-snapshot--support)
- [Directory structure & architecture](#directory-structure--architecture)
- [AUR packaging (optional)](#aur-packaging-optional)
- [Troubleshooting](#troubleshooting)
- [Security & privacy](#security--privacy)
- [License](#license)

## Overview

XSArena is a power user's studio for generating long‑form books, study materials, and analysis with strong control over continuation, density, and style. It speaks to two backends:

- Bridge backend (default): works with the LMArena browser userscript (polling).
- OpenRouter backend: direct API streaming.

Key features:
- Anchored continuation: The next chunk sees the tail of the last output to continue seamlessly (no "chapter 1 again" restarts).
- Output budget & repetition guard: Control density per chunk and avoid loops.
- Pedagogy overlay: Teach‑before‑use and narrative flow when you need less "dense manual," more "clear teaching".
- Two backends: Bridge (browser-based) and OpenRouter (direct API streaming)

## Key capabilities

- Book authoring modes:
  - zero2hero: pedagogical manual from foundations to advanced practice
  - reference: tight reference handbook
  - nobs: "no‑bullshit" stripped style
  - pop: popular‑science style
  - bilingual: interleaved text in two languages
- Zero-to-Hero mode (enhanced):
  - z2h: no-bs + narrative overlay + outline-first + hammer (automated workflow)
  - z2h-list: run multiple subjects sequentially
- Job system with failover:
  - Automatic recovery from stalls (retry mechanism)
  - Failover to OpenRouter when bridge unavailable
  - Resume from checkpoints
  - Fork jobs for continued work
- Lossless text pipeline:
  - ingest.synth: build a compact synthesis from files
  - rewrite.lossless: re‑express with no meaning loss
- Study tools:
  - exam.cram: high‑yield quick prep
  - flashcards.from: study cards from a synthesis
  - glossary.from / index.from
- Styles & tuning:
  - style.nobs: plain language, zero fluff
  - style.narrative: teach‑before‑use narrative overlay (define terms before use, add vignettes and quick checks)
- Jobs & recipes:
  - run.recipe: run a plan from YAML/JSON file
  - run.inline: paste an inline recipe and run in one shot (if enabled)
- Session control:
  - book.pause/resume/stop; book.save/load; auto.out (change output path on resume)

## Installation

- Python 3.9+
- Clone:
  - `git clone https://github.com/tazdev-ops/xsarena`
  - `cd xsarena`
- Install dev extras:
  - Linux/macOS: `pip install -e ".[dev]"`
  - Windows (Command Prompt): `py -3 -m pip install -e ".[dev]"`
  - Windows (PowerShell): `py -3 -m pip install -e ".[dev]"`
- Optional extras:
  - TUI (textual): `pip install "textual>=0.40.0"`
  - GUI (GTK) if implemented: `pip install "PyGObject>=3.44"` (note: GTK4 GUI is experimental on Windows)
  - OpenRouter backend: set OPENROUTER_API_KEY
- For AUR users: see "AUR packaging" below.

### Windows-specific notes:
- Ensure Python 3.9+ is installed and in your PATH
- Use `py -3` to explicitly call Python 3 on Windows
- Optional TUI: `py -3 -m pip install "textual>=0.40.0"`
- OpenRouter: Use `setx OPENROUTER_API_KEY yourkey` (Command Prompt) or `$env:OPENROUTER_API_KEY="yourkey"` (PowerShell)
- Running XSArena:
  - If installed as console script: `xsarena`
  - Direct execution: `py -3 xsarena` or `py -3 lma_cli.py` (legacy compatibility)
  - If you encounter issues with PTK: `setx XSA_USE_PTK 0` then restart terminal

### Windows quickstart:
- Install Python 3.9+ and ensure it's in your PATH
- Install dependencies: `py -3 -m pip install -e ".[dev]"`
- Disable PTK for smoother experience: `setx XSA_USE_PTK 0` (then restart terminal)
- Set OpenRouter key (optional): `setx OPENROUTER_API_KEY yourkey`
- Run: `xsarena`

## Quick start

### A) Bridge backend (browser)
1) Start the CLI:
   - `xsarena`
2) In a browser, open https://lmarena.ai with the included userscript (see src/xsarena/bridge/userscript_example.js).
3) In CLI:
   - `/capture`
   - Click Retry once on any message in the browser; the CLI prints session/message IDs.
4) You're connected. Use `/status` to verify, then run commands.

### B) OpenRouter backend (no browser)
- Export your key:
  - `export OPENROUTER_API_KEY=…` (Linux/macOS)
  - `setx OPENROUTER_API_KEY …` (Windows Command Prompt)
  - `$env:OPENROUTER_API_KEY="…"` (Windows PowerShell - session only)
- In CLI:
  - `/backend openrouter`
  - `/or.model openrouter/auto`
  - `/or.status`

## Essential workflows

### 1) A pedagogical manual (English)
- Load directives (your study domain):
  - `/systemfile directives/your_topic.en.txt`
- Optional: enforce pedagogy:
  - `/style.narrative on`
- Start:
  - `/repo.use book.zero2hero "Your Topic"`
  - `/book.zero2hero "Your Topic" --plan`

### 2) Reference → pedagogy (two‑step)
- Build a synthesis:
  - `/ingest.synth sources/topic_corpus.md books/topic.synth.md 100 16000`
- Lossless rewrite:
  - `/rewrite.start books/topic.synth.md books/topic.lossless.md`
- Pedagogical pass:
  - `/style.narrative on`
  - `/book.zero2hero "Your Topic"`

### 3) Exam‑prep
- `/exam.cram "Your Topic"`
- From a synthesis:
  - `/flashcards.from books/topic.synth.md books/topic.flashcards.md 220`
  - `/glossary.from books/topic.synth.md books/topic.glossary.md`
  - `/index.from books/topic.synth.md books/topic.index.md`

### 4) Resume later
- `/book.save myrun`
- Next time:
  - `xsarena`
  - `/book.load myrun`
  - `/status`
  - `/book.resume`
- Change output path mid‑resume:
  - `/auto.out books/myrun.cont.md`
  - `/book.resume`

## Command cheat sheet

### Core
- `/help` — list commands
- `/status` — show state
- `/capture` — capture IDs (bridge); click Retry once in browser
- `/setids <sess> <msg>` — set IDs manually
- `/exit` — quit

### Backends
- `/backend bridge|openrouter`
- `/or.model <model>`
- `/or.ref <url>` | `/or.title <text>`
- `/or.status`

### Book modes
- `/book.zero2hero <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]`
- `/book.reference <subject> …`
- `/book.nobs <subject> …`
- `/book.pop <subject> …`
- `/book.bilingual <subject> --lang=LANG [--plan] …`
- `/exam.cram <subject> [--max=N] …`

### Autopilot & sessions
- `/book.pause` | `/book.resume` | `/book.stop`
- `/next "hint"` — one‑shot steer
- `/book.save [name]` | `/book.load <name>`
- `/auto.out <path>`

### Continuation, density, and style
- `/cont.mode normal|anchor`
- `/cont.anchor <N>`
- `/out.budget on|off` — push for max chunk density
- `/out.minchars <N>` — min chars per chunk
- `/out.passes <N>` — in‑chunk micro‑continues
- `/repeat.warn on|off` | `/repeat.thresh <0..1>`
- `/style.nobs on|off` — plain, no fluff
- `/style.narrative on|off` — teach‑before‑use narrative overlay

### Synthesis & lossless
- `/ingest.synth <file> <synth.md> [chunkKB=45] [synthChars=9500]`
- `/rewrite.start <synth.md> <out.md>`
- `/rewrite.lossless <synth.md> [out.md]`
- `/lossless.run <file> [--outdir=DIR] [--chunkKB=45] [--synthChars=12000]`

### Study tools
- `/flashcards.from <synth.md> <out.md> [n=200]`
- `/glossary.from <synth.md> <out.md>`
- `/index.from <synth.md> <out.md>`

### Prompt booster & Q&A
- `/prompt.boost "goal" [--ask] [--apply] [--meta]`
- `/prompt.answer` — answer booster questions
- `/prompt.apply [next|system]`
- `/chad "question" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]`

### Recipes & macros
- `/run.recipe <recipe.(json|yml)>`
- `/run.inline` (paste YAML/JSON inline, end with EOF) — if enabled
- `/run.quick task=… subject=… out=…`
- `/macro.save <name> "template"`
- `/macro.list` | `/macro.delete <name>`
- `/macro.run <name> [args…]`

### Cloudflare (bridge)
- `/cf.status`
- `/cf.resume` | `/cf.reset`

## Continuation, density, and style (how they work)

- **Anchored continuation** (`/cont.mode anchor`): The next prompt includes the tail of your last output, so the model continues mid‑paragraph without re‑introductions or summaries.
- **Output budget**: If on, the system prompt encourages the model to use most of the token window per chunk (great for dense manual writing).
- **Min chunk & passes**: Tweak `/out.minchars` and `/out.passes` to balance flow vs density.
- **Styles**: `/style.nobs` (zero fluff) and `/style.narrative` (teach‑before‑use, short vignettes, quick checks). You can combine them, but typically pick one per run.

Key concepts:
- **Autopilot**: a loop that sends "BEGIN" then continues from an anchor chunk by chunk, writing to a file.
- **Anchored continuation**: the model sees the tail of last output to continue seamlessly.
- **Output budget**: a system addendum that pushes the model to use its full token window (produces dense chunks).
- **Output push**: optional in‑chunk micro‑continues to reach a minimal length.
- **Repetition guard**: jaccard n‑gram checking to avoid loops.

## Synthesis & lossless rewrite (recommended pattern)

- Aggregate your sources to a per‑topic corpus (plain text):
  - `cat sources/topic/*.* > sources/topic_corpus.md`
- Build compact synthesis:
  - `/ingest.synth sources/topic_corpus.md books/topic.synth.md 100 16000`
- Lossless rewrite (cleaned, structured):
  - `/rewrite.start books/topic.synth.md books/topic.lossless.md`
- Use the lossless output to produce pedagogy or study aids.

## Study tools & exam‑prep

- `exam.cram`: high‑yield outline and pitfalls
- `flashcards.from`: Q/A cards; specify n
- `glossary.from`: tight definitions; why it matters
- `index.from`: grouped index of topics/subtopics

## Recipes (file and inline one‑shot)

### File recipe:
```yaml
recipes/manual.yml:
task: book.zero2hero
subject: "Ancient Iranian Languages"
styles: [no-bs]
system_text: |
  English only. Teach-before-use. Narrative transitions.
prelude:
  - "/out.budget off"
  - "/cont.mode anchor"
  - "/repeat.warn on"
  - "/style.narrative on"
io:
  output: file
  outPath: "./books/ancient-iranian-languages.manual.en.md"
max_chunks: 6
```
Run: `/run.recipe recipes/manual.yml`

### Inline recipe (one‑shot, paste once, end with EOF) — if enabled:
- `/run.inline`
- Paste YAML (same schema as above)
- EOF

## Session management (resume, checkpoints, transplanting context)

- Save while running:
  - `/book.save myrun`
- Resume later:
  - `/book.load myrun`
  - `/status`
  - `/book.resume`
- Change output path:
  - `/auto.out books/myrun.cont.md`
- Continue an existing browser chat (not started by the app):
  - Open that chat in the browser
  - `/capture` in CLI; click Retry once on that chat
  - The CLI now sends into that thread
- Fork a stuck chat into a new one (and transplant context):
  - In browser: New chat → `/capture` → Retry
  - `/system.append`
    ```
    Conversation transplant (English only). Continue exactly.
    - Goal: …
    - Covered so far: …
    - NEXT: …
    EOF
    ```

## Handling browser "waiting…" stalls and Failover

- Cancel the stream (PTK): Ctrl+C once
- Check Cloudflare:
  - `/cf.status` → solve challenge → `/cf.resume` → `/book.resume`
- Reduce window size:
  - `/window 60` (or 40)
- Automatic failover behavior:
  - Job runner automatically detects stalls
  - After configured retries, switches to fallback backend (e.g., OpenRouter)
  - Continues from the last saved state
- Switch to OpenRouter manually:
  - `/backend openrouter` → `/or.model openrouter/auto`
- Fork & transplant (as above)

## Project snapshot & support

- Create a snapshot txt or 100KB chunked files:
  - `./snapshot.sh`
  - `./snapshot.sh --chunk`
- Share snapshot_chunks with helpers for context. Excludes build artifacts and large binaries.

## Directory structure & architecture

### Top‑level dirs/files you'll use most
- `books/` — outputs (manuals, cram, flashcards, glossaries, indexes)
- `directives/` — system directives/templates (e.g., your_topic.en.txt)
- `sources/` — your input corpora (group by topic)
- `data/` — blueprints, resource maps, tag maps
- `recipes/` — YAML/JSON plans for run.recipe
- `.xsarena/` or `.lmastudio/` — local state (checkpoints, macros)
- `xsarena` (main entry) / `lma_cli.py` (legacy compatibility shim)
- `src/xsarena/` — core engine, modes, CLI command modules, bridge servers, etc.

### Architecture (high level)
- `src/xsarena/core`: engine, backends, chunking, templates, state, pipeline
- `src/xsarena/cli`: command routers, service launchers
- `src/xsarena/modes`: book/study/lossless/bilingual/policy/chad wrappers
- `src/xsarena/bridge`: local bridge servers (simple polling and OpenAI‑compatible API)

## AUR packaging (optional)

- Provide two packages:
  - xsarena (stable): build from a tagged release (PKGBUILD uses python‑build + python‑installer)
  - xsarena‑git (VCS): build from main (pkgver uses git describe or commit count)
- Test locally with makepkg -si; run xsarena /status after install
- See the provided PKGBUILD templates in your packaging folder or write your own as per Arch guidelines.

## Troubleshooting

- "Unknown command" for density knobs in PTK:
  - Linux/macOS: Run without PTK: `XSA_USE_PTK=0 xsarena`
  - Windows (Command Prompt): `setx XSA_USE_PTK 0` then restart terminal
  - Windows (PowerShell): `$env:XSA_USE_PTK="0"` (session only) or `setx XSA_USE_PTK 0` (persistent)
  - Or apply the CLI unification patch that adds handlers in both PTK and fallback
- Server startup on Windows: If Windows Firewall prompts, allow Python on Private networks only.
- Output not strictly English:
  - `/system.append` a strict English‑only line and continue
- Model repeats:
  - `/repeat.warn on`; `/repeat.thresh 0.35`
  - Lower `/out.passes`; reduce `/out.minchars`
- Dense vs terse:
  - Dense: `/out.budget off`; `/out.minchars 2500–3200`; `/out.passes 0–1`
  - Terse: `/out.budget on`; `/out.minchars 4500–5200`; `/out.passes 2–3`
- Bridge CF issues:
  - `/cf.status`; after solving challenge → `/cf.resume` → `/book.resume`
- Restore a file after a one‑liner patch:
  - `mv lma_cli.py.bak2 lma_cli.py` (if you keep backups)

- **Unknown command: /book.hammer or /out.minchars**
  - If you haven't applied the patch, these may only exist in fallback REPL.
  - Fix: use this patched version or run `XSA_USE_PTK=0 python lma_cli.py`
- **Model won't do narrative**: ensure `/style.narrative on` and consider `/out.budget off` and `minChars ~3000`
- **Too terse**: `/out.budget on`, `/out.minchars 4500–5200`, `/out.passes 2–3`
- **Too verbose**: `/out.budget off`, `/out.minchars 2500–3200`, `/out.passes 0–1`
- **Hard restarts**: ensure `/cont.mode anchor`; if still occurs, append a brief "CONTINUATION" hint with `/next`
- **English only**: append a one‑liner to system:
  "Output must be 100% English. If inputs contain other languages, translate to English before use."

## Security & privacy

- Respect test security. Do not ingest or reproduce restricted materials.
- When using OpenRouter, your prompts/outputs go to the selected model provider under their terms. Do not send sensitive data you aren't comfortable sharing.
- Bridge backend streams via your browser; treat your browser session as authenticated and private.

## Contributing

- PRs welcome. Please:
  - Follow PEP8, type hints; docstrings for public functions
  - Run Ruff + Black; tests via pytest
  - Keep behavioral changes isolated from formatting in separate commits
  - Add docs/examples for new commands or styles
- If you need help, run `./snapshot.sh --chunk` and share the chunks with your advisor AI.

## License

MIT (see LICENSE).

## Recommended workflows

### A) Zero‑to‑hero book (English)
- Set style/knobs:
  ```
  /style.narrative on
  /out.budget off
  /out.minchars 3000
  /repeat.warn on
  /cont.mode anchor
  ```
- Start:
  ```
  /repo.use book.zero2hero "Clinical Psychology"
  /book.zero2hero "Clinical Psychology" --plan
  ```
- Steer mid‑run (if needed):
  ```
  /book.pause
  /next "Revisit the last section in the narrative style: define all terms before use, add a short vignette and a quick check; then continue."
  /book.resume
  ```

### B) Enhanced Zero-to-Hero (z2h) - Recommended
- Quick start with all enhancements:
  ```
  /z2h "Clinical Psychology" --out=./books/psychology.final.md --max=6 --min=3000
  ```
- Process multiple subjects:
  ```
  /z2h-list "Subject A; Subject B; Subject C" --max=4 --min=2500
  ```

### B) Tight reference → pedagogy
- Build a synthesis from your corpus:
  - `/ingest.synth sources/clinical_corpus.md books/clinical.synth.md 100 16000`
- Lossless rewrite:
  - `/rewrite.start books/clinical.synth.md books/clinical.lossless.md`
- Pedagogical run on top:
  - `/style.narrative on`
  - `/book.zero2hero "Clinical Psychology"`

### C) Exam cram + study aids
- `/exam.cram "Clinical Psychology"`
- `/flashcards.from books/clinical.synth.md books/clinical.flashcards.md 220`
- `/glossary.from books/clinical.synth.md books/clinical.glossary.md`
- `/index.from books/clinical.synth.md books/clinical.index.md`

### D) Bilingual transform
- `/bilingual.file path/to/en.md --lang=Japanese --outdir=books --chunkKB=45`

## How continuation works (anchor mode)
- The tail ~N characters (configurable) of the last assistant output are injected into the next prompt as an anchor.
- The model is told to "continue exactly from after the anchor; do not reintroduce; do not summarize."
- This avoids resets, keeps tight continuity, and prevents "chapter 1… again" restarts.

## Repetition guard
- Jaccard n‑gram similarity between the last tail and the new head of output
- If similarity > threshold, it warns and pauses; steer with /next

## Common Commands Quick Reference

### Essential Workflow Commands
```
# Start a zero-to-hero book
xsarena book zero2hero --subject "Your Topic"

# Run enhanced zero-to-hero (with no-bs, narrative, hammer)
xsarena z2h "Your Topic" --out=./books/final.md --max=6 --min=3000

# Run z2h on multiple subjects
xsarena z2h-list "Subject A; Subject B; Subject C" --max=4 --min=2500

# Run lossless rewrite on a file
xsarena lossless run --input-file path/to/file.md

# Start bridge server
xsarena service start-bridge

# Check status
xsarena --help

# Job management
xsarena jobs ls              # List all jobs
xsarena jobs log <id>        # Show job log events
xsarena jobs resume <id>     # Resume a job
xsarena jobs cancel <id>     # Cancel a job
xsarena jobs fork <id>       # Fork a job to new backend
xsarena jobs open <id>       # Open job artifacts folder
```

## Windows Command Examples

### Environment Setup
- Set API keys: `$env:OPENROUTER_API_KEY="yourkey"` (PowerShell) or `setx OPENROUTER_API_KEY "yourkey"` (Command Prompt)
- Disable PTK: `setx XSA_USE_PTK 0` then restart terminal

### Running on Windows
```
# Install
py -3 -m pip install -e ".[dev]"

# Run main CLI
py -3 -m xsarena

# Or with console scripts after install
xsarena
```

## Recovery: Unstick a Dead LMArena Chat

### Fork & Transplant Method
1. In browser: Open a new chat → `/capture` in CLI → click Retry once
2. `/system.append` to transplant context:
   ```
   Conversation transplant (English only). Continue exactly.
   - Goal: [original goal]
   - Covered so far: [brief summary of what was covered]
   - NEXT: [specific next step]
   EOF
   ```
3. Continue working in the new chat

### Alternative Recovery
- Cancel current stream: Ctrl+C (if using PTK)
- Check Cloudflare status: `/cf.status`
- Resume: `/book.resume`
- Reduce window size: `/window 60` if issues persist

## Preview & Publish

### Local Web Preview (Serve)
Browse books/ and per-job artifacts in a clean local web UI with live job logs.

- `xsarena serve run` — start local web server (default: http://127.0.0.1:8787)
- Open browser to view books, job artifacts, and tail live job events

### Export to EPUB/PDF
Export finished manuals to portable formats using Pandoc.

- `xsarena publish run <job_id> --epub --pdf` — export job to EPUB and PDF
- Requires Pandoc installation:
  - Linux: `apt install pandoc` or `yum install pandoc`
  - macOS: `brew install pandoc`
  - Windows: `winget install JohnMacFarlane.Pandoc`

## Advanced Pro Features

XSArena includes enterprise-grade features for cost control, quality, and observability:

### Multi-Agent Pipeline
- **z2h_multi playbook**: `xsarena z2h "Topic" --playbook z2h_multi` runs Outliner → Writer → Editor → Continuity agents
- **Quality assurance**: Each stage improves content quality and consistency

### Cost Tracking & Budgets
- **Install metrics**: `pip install -e ".[metrics]"`
- **Real-time cost tracking**: Monitors tokens and USD estimates per job
- **Budget limits**: Set `budget_usd: 5.00` in playbook/project to auto-stop jobs that exceed budget

### SSE Streaming & Live Monitoring
- **Live event streaming**: `xsarena serve` provides real-time job monitoring via Server-Sent Events
- **URL**: `http://127.0.0.1:8787/stream/jobs/{job_id}/events`
- **Live dashboard**: Monitor progress, costs, and failures in real-time

### Model Routing & Fallback
- **LiteLLM router**: `xsarena backend set --router litellm --base-url http://localhost:4000 --api-key sk-...`
- **Fallback chains**: Automatic failover to backup models/providers when primary fails
- **Adaptive routing**: Switch to different models based on availability and cost

### Caching for Cost Reduction
- **Install cache**: `pip install -e ".[cache]"` (Redis or file-based)
- **Prompt caching**: Avoids repeated costs for identical prompts/contexts
- **Typical savings**: 30-40% reduction in token usage on retries and similar content

### REST API
- **Programmatic access**: Full API at `http://127.0.0.1:8787/api/`
- **Endpoints**: `/api/jobs`, `/api/jobs/{id}`, `/api/jobs/{id}/events`, `/api/jobs/z2h`
- **Integrations**: Control XSArena from other tools and scripts

## Audio Books (Optional)

Convert EPUB to audiobooks using Edge TTS (free) or external tools.

- **Install optional audio dependencies**: `pip install -e ".[audio]"`
- **FFmpeg requirement**: Install via package manager (apt/brew/choco) if you'll transcode beyond what edge-tts produces
- **Basic usage**: `xsarena audio run <job_id> --provider edge --voice en-US-JennyNeural --format mp3 --outdir ./audio`
- **External tool support**: If `epub_to_audiobook` is installed, can delegate to it for maximum features: `xsarena audio run <job_id> --provider external --voice en-US-JennyNeural`
- **Windows users**: Install ffmpeg (choco install ffmpeg) if you need formats beyond edge defaults
- **Simple flow example**:
  - `xsarena z2h "Topic"`
  - `xsarena publish run <job_id> --epub`
  - `xsarena audio run <job_id> --provider edge --voice en-US-JennyNeural`

## Health Checks & Diagnostics

Verify environment and run synthetic smoke tests.

- `xsarena doctor env` — check environment, Python version, API keys
- `xsarena doctor run` — run a tiny z2h job (2 chunks) and verify artifacts
- Reports PASS/FAIL with timing information

## New CLI Commands Summary

### Core Commands
- `xsarena z2h "Subject"` — run enhanced zero-to-hero with no-bs, narrative, hammer
- `xsarena z2h-list "A; B; C"` — process multiple subjects sequentially
- `xsarena jobs ls/log/resume/cancel/fork/open` — job management
- `xsarena doctor env/run` — environment checks and smoke tests

### Preview & Publish
- `xsarena serve run` — local web preview server (with live job logs and SSE streaming)
- `xsarena publish run <job_id> --epub --pdf` — export to portable formats

### Audio
- `xsarena audio run <job_id> --provider edge` — convert to audiobook

### Advanced Features (Pro)
- `xsarena backend set --router litellm` — switch to LiteLLM router
- `xsarena z2h-multi "Subject"` — run multi-agent pipeline (outliner → writer → editor → continuity)

### Windows Notes
- Set environment variables: `$env:OPENROUTER_API_KEY="yourkey"` (PowerShell) or `setx OPENROUTER_API_KEY "yourkey"` (Command Prompt)
- Disable PTK for smoother experience: `setx XSA_USE_PTK 0` then restart terminal
- Install optional dependencies: `py -3 -m pip install -e ".[dev]"`

## Professional-Grade Features

### Cost & Token Metering
- Automatic cost estimation for OpenRouter chunks
- Events logged to job's `events.jsonl` with token counts and estimated costs
- `xsarena jobs log <id>` shows cumulative tokens and cost information

### Adaptive Chunk Sizing
- Auto-tunes minChars per section based on observed output lengths
- Nudges ±10-15% to hit stable ~3000 char targets without truncation
- Reduces variability in chunk lengths over time

### Failover & Recovery
- Automatic watchdog detects stalled streams
- After max retries, switches to fallback backend (e.g., OpenRouter)
- Fork command clones jobs with transplant summary for context continuity

### Quality Assurance
- Built-in linting for pedagogy rules (teach-before-use enforcement)
- NEXT marker validation to ensure smooth continuation
- Live web preview with SSE streaming for real-time monitoring

### Concurrency Management
- Configurable concurrency limits per backend
- Automatic throttling to respect rate limits
- Queue management for multiple simultaneous jobs
