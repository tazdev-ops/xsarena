XSArena — AI Writing, Study, and CLI Studio

Overview
XSArena is a power user's studio for generating long‑form books, study materials, and analysis with strong control over continuation, density, and style. It speaks to two backends:
- Bridge backend (default): works with the LMArena browser userscript (polling).
- OpenRouter backend: direct API streaming.

Major capabilities
- Book writing modes: zero‑to‑hero, reference, pop‑science, no‑BS, bilingual
- Lossless pipeline: ingest → synthesis → lossless rewrite
- Study tools: exam‑cram, flashcards, glossary, index
- Style tools: capture + apply, narrative/pedagogy overlays
- Autopilot: anchored continuation, output budget, repetition guard
- Prompt Booster: improve prompts with a single command
- Snapshot tooling: export your entire project for remote help

Install
- Python 3.9+
- pip install -e ".[dev]" (from repo root)
- Optional: install aiohttp if not present: pip install aiohttp
- For TUI: pip install "textual>=0.40.0"

Quick start (Bridge backend)
1) Start the CLI:
   python xsarena_cli.py
2) In your browser, open https://lmarena.ai with the included userscript (see src/xsarena/bridge/userscript_example.js)
3) In the CLI:
   /capture
   Click Retry on any message in the browser (captures session/message IDs)

Quick start (OpenRouter backend)
- Export OPENROUTER_API_KEY (or OPENAI_API_KEY)
- In CLI:
  /backend openrouter
  /or.model openrouter/auto
- Then use normal commands

Key concepts
- Autopilot: a loop that sends "BEGIN" then continues from an anchor chunk by chunk, writing to a file.
- Anchored continuation: the model sees the tail of last output to continue seamlessly.
- Output budget: a system addendum that pushes the model to use its full token window (produces dense chunks).
- Output push: optional in‑chunk micro‑continues to reach a minimal length.
- Repetition guard: jaccard n‑gram checking to avoid loops.

Primary commands
Core
- /help — list commands
- /status — show state
- /capture — capture IDs from the browser (then click Retry)
- /setids <sess> <msg> — set IDs manually
- /exit — quit

Backends
- /backend bridge|openrouter — switch
- /or.model <model> — set OpenRouter model
- /or.ref <url> | /or.title <text> — optional headers
- /or.status — show OpenRouter status

Book modes
- /book.zero2hero <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]
- /book.reference <subject> …
- /book.pop <subject> …
- /book.nobs <subject> …
- /book.bilingual <subject> --lang=LANG [--plan] …
- /exam.cram <subject> [--max=N] …

Autopilot control
- /book.pause | /book.resume | /book.stop
- /next "<hint>" — one‑shot steer
- /book.hammer on|off — anti‑wrap "coverage hammer" (prevents early wrap‑up)

Density, continuation, repetition
- /out.budget on|off — push for max per‑chunk content
- /out.push on|off — allow micro‑continues inside a chunk
- /out.minchars <N> — min characters per chunk (default 4500)
- /out.passes <N> — max micro‑continues (default 3)
- /cont.mode normal|anchor — continuation strategy
- /cont.anchor <N> — tail chars used as anchor
- /repeat.warn on|off — repetition warning
- /repeat.thresh <0..1> — repetition sensitivity

Styles
- /style.nobs on|off — cut fluff; plain language
- /style.narrative on|off — narrative + pedagogy overlay (teach‑before‑use, vignettes, quick checks)
- /style.capture <file> <style.synth.md> [chunkKB=30] [styleChars=6000]
- /style.apply <style.synth.md> <topic|file> [out.md] [--words=N]

Synthesis, lossless, study aids
- /ingest.synth <file> <synth.md> [chunkKB=45] [synthChars=9500]
- /rewrite.start <synth.md> <out.md>
- /rewrite.lossless <synth.md> [out.md]
- /lossless.run <file> [--outdir=DIR] [--chunkKB=45] [--synthChars=12000]
- /flashcards.from <synth.md> <out.md> [n=200]
- /glossary.from <synth.md> <out.md>
- /index.from <synth.md> <out.md>

Prompt Booster
- /prompt.boost "goal" [--ask] [--apply] [--meta]
- /prompt.answer — answer booster questions
- /prompt.apply [next|system] — apply improved prompt

Recipes and macros
- /run.recipe <recipe.json|yml>
- /run.quick task=... subject="..." out=path [max=N] [style=no-bs,chad]
- /macro.save <name> "<command template>"
- /macro.list | /macro.delete <name>
- /macro.run <name> [args…]

Snapshots
- /snapshot [--chunk] — build snapshot.txt or 100KB chunks in snapshot_chunks/

Modes and TUI
- /mono — toggle monochrome
- xsarena_tui.py — launches a Textual UI that wraps the CLI with buttons (capture/status/book controls)

Recommended workflows

A) Zero‑to‑hero book (English)
- Set style/knobs:
  /style.narrative on
  /out.budget off
  /out.minchars 3000
  /repeat.warn on
  /cont.mode anchor
- Start:
  /repo.use book.zero2hero "Clinical Psychology"
  /book.zero2hero "Clinical Psychology" --plan
- Steer mid‑run (if needed):
  /book.pause
  /next "Revisit the last section in the narrative style: define all terms before use, add a short vignette and a quick check; then continue."
  /book.resume

B) Tight reference → pedagogy
- Build a synthesis from your corpus:
  /ingest.synth sources/clinical_corpus.md books/clinical.synth.md 100 16000
- Lossless rewrite:
  /rewrite.start books/clinical.synth.md books/clinical.lossless.md
- Pedagogical run on top:
  /style.narrative on
  /book.zero2hero "Clinical Psychology"

C) Exam cram + study aids
- /exam.cram "Clinical Psychology"
- /flashcards.from books/clinical.synth.md books/clinical.flashcards.md 220
- /glossary.from books/clinical.synth.md books/clinical.glossary.md
- /index.from books/clinical.synth.md books/clinical.index.md

D) Bilingual transform
- /bilingual.file path/to/en.md --lang=Japanese --outdir=books --chunkKB=45

Density tuning recipes (hands‑off)
recipes/clinical.narrative.yml
```yaml
task: book.zero2hero
subject: "Clinical Psychology"
styles: [no-bs]
style_file: "directives/style.narrative_en.md"   # optional – same overlay text as /style.narrative
hammer: true
continuation:
  mode: anchor
  minChars: 3000
  pushPasses: 1
  repeatWarn: true
io:
  output: file
  outPath: "./books/clinical.manual.en.narrative.md"
max_chunks: 6
```
Run:
  /run.recipe recipes/clinical.narrative.yml

How continuation works (anchor mode)
- The tail ~N characters (configurable) of the last assistant output are injected into the next prompt as an anchor.
- The model is told to "continue exactly from after the anchor; do not reintroduce; do not summarize."
- This avoids resets, keeps tight continuity, and prevents "chapter 1… again" restarts.

Repetition guard
- Jaccard n‑gram similarity between the last tail and the new head of output
- If similarity > threshold, it warns and pauses; steer with /next

Cloudflare (Bridge backend)
- If you see a pause with a CF notice, solve the challenge in the browser, then:
  /cf.resume
  /book.resume

Troubleshooting
- Unknown command: /book.hammer or /out.minchars
  - If you haven't applied the patch, these may only exist in fallback REPL.
  - Fix: use this patched version or run XSA_USE_PTK=0 python xsarena_cli.py
- Model won't do narrative: ensure /style.narrative on and consider /out.budget off and minChars ~3000
- Too terse: /out.budget on, /out.minchars 4500–5200, /out.passes 2–3
- Too verbose: /out.budget off, /out.minchars 2500–3200, /out.passes 0–1
- Hard restarts: ensure /cont.mode anchor; if still occurs, append a brief "CONTINUATION" hint with /next
- English only: append a one‑liner to system:
  "Output must be 100% English. If inputs contain other languages, translate to English before use."

Developer guide (architecture)
- src/xsarena/core: engine, backends, templates, chunking, state, pipeline tools
- src/xsarena/cli: command modules, main entrypoint, service management
- src/xsarena/modes: book/lossless/bilingual/policy/study/chad wrappers
- Bridge servers: src/xsarena/bridge/server.py (simple), compat_server.py (OpenAI‑style)
- TUI: xsarena_tui.py (Textual)

Extending styles
- Add new overlays to xsarena_templates.py (like NARRATIVE_OVERLAY)
- Expose toggles in xsarena_cli.py similar to /style.narrative
- For run.recipe, pass style_file to apply overlays automatically

Testing
- pytest (tests are light-weight)
- test_cli.py verifies import and key symbols

Contributing
- Follow PEP 8; type hints; docstrings
- Run pre-commit hooks; Ruff/Black
- Submit PRs with tests and sample commands

License
MIT