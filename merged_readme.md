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
  - `pip install -e ".[dev]"`
- Optional extras:
  - TUI (textual): `pip install "textual>=0.40.0"`
  - GUI (GTK) if implemented: `pip install "PyGObject>=3.44"`
  - OpenRouter backend: set OPENROUTER_API_KEY
- For AUR users: see "AUR packaging" below.

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
  - `setx OPENROUTER_API_KEY …` (Windows)
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

## Handling browser "waiting…" stalls

- Cancel the stream (PTK): Ctrl+C once
- Check Cloudflare:
  - `/cf.status` → solve challenge → `/cf.resume` → `/book.resume`
- Reduce window size:
  - `/window 60` (or 40)
- Switch to OpenRouter and re‑run the same plan:
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
- `lma_cli.py` (compat) / `xsarena_cli.py` (if renamed)
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
  - Run without PTK: `XSA_USE_PTK=0 xsarena`
  - Or apply the CLI unification patch that adds handlers in both PTK and fallback
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
  - `mv lma_cli.py.bak lma_cli.py`

- **Unknown command: /book.hammer or /out.minchars**
  - If you haven't applied the patch, these may only exist in fallback REPL.
  - Fix: use this patched version or run `XSA_USE_PTK=0 python xsarena_cli.py`
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

## Cloudflare (Bridge backend)
- If you see a pause with a CF notice, solve the challenge in the browser, then:
  ```
  /cf.resume
  /book.resume
  ```
