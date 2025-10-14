Agent QuickRef — XSArena (Bilingual) (1 page)

Purpose
- Tell the AI exactly how we work: which workflows to use, which knobs to set, how to recover mid‑run.
- Tone: bilingual pairs (EN/FA) by default; flip to compressed when needed.

Defaults (set these unless told otherwise)
- English/Persian bilingual pairs. Define terms before use; keep flow in prose (no bullet walls unless explicitly asked).
- Continuation: anchor mode; do not restart sections; do not wrap up early.
- No fluff; avoid headings unless they help.

Core Knobs (preferred ranges)
- /cont.mode anchor; /cont.anchor 200
- /repeat.warn on; /repeat.thresh 0.35
- /out.minchars 4200 (dense 4800–5200)
- /out.passes 1 (longer: 2–3; terse: 0)
- /book.hammer on (anti‑wrap)
- Style: /style.nobs on (no‑BS), /style.narrative on (teach‑before‑use). Turn off narrative if we go compressed.
- Output: EN/FA pairs (bilingual transformation)

Workflows (pick one)
1) Mastery Manual (Zero‑to‑Hero, bilingual)
   - Use when teaching from basics to practice in both languages.
   - Commands:
     - /style.nobs on; /style.narrative on
     - /bilingual.file books/TOPIC.en.md --lang=fa
     - /z2h "TOPIC" --out=./books/TOPIC.final.md --max=12 --min=4200
   - If it lists too much: /out.passes 0; keep prose.

2) Lossless‑First → Pedagogy (when you have sources)
   - Build synth → rewrite → pedagogy.
   - Commands:
     - xsarena lossless ingest sources/corpus.md books/topic.synth.md --chunk-kb 100 --synth-chars 16000
     - xsarena lossless rewrite books/topic.synth.md books/topic.lossless.md
     - /bilingual.file books/TOPIC.en.md --lang=fa
     - /z2h "TOPIC" --out=./books/TOPIC.final.md --max=8 --min=4200

3) Study Pack (fast exam prep)
   - xsarena exam cram "TOPIC"
   - xsarena flashcards from books/topic.synth.md books/topic.cards.md --n 200
   - xsarena glossary from books/topic.synth.md books/topic.glossary.md

4) Publish + Audio
   - xsarena publish run <job_id> --epub --pdf
   - xsarena audio run <job_id> --provider edge --voice en-US-JennyNeural

5) Bilingual
   - /bilingual.file path/to/text.md --lang=LANG  (pairs or full transform)

When to switch styles
- Compressed mastery (dense, flowing, few lists): /style.narrative off; /style.compressed on; /out.minchars 4800; /out.passes 2
- Reference handbook (tight, definitions first): use book.reference or keep z2h with lower passes and clearer headings.

Mid‑Run Troubleshooting
- Too listy or heading‑happy → /style.compressed on; /out.passes 0; keep narrative paragraphs.
- Too terse → /out.passes 2–3; /out.minchars 4800–5200.
- Repeating → /repeat.warn on; /book.pause; /next "Continue exactly from anchor. No restart. No wrap‑up."
- Bridge stalls → /cf.status → solve in browser → /cf.resume → /book.resume.
- Bilingual drift → /bilingual.file path/to/text.md --lang=fa; ensure consistent translation quality.

Hygiene & Health (quick)
- Snapshot: xsarena snapshot run --chunk
- Quick doctor: xsarena doctor env
- Live preview: xsarena serve run (tail logs)
- Jobs: xsarena jobs ls | xsarena jobs summary <id>

Prompts (lightweight, reusable)
- "Teach‑before‑use; define terms inline; prose flow; avoid bullet walls unless clarity demands it. Continue exactly; no restarts; no early wrap‑ups. Output EN/FA pairs."
- For compressed: "Max‑dense narrative; minimal headings; no drills or checklists. Output EN/FA pairs."

Escalation (ask for help)
- If loop or drift persists: snapshot, jot the problem in docs/OUTBOX.md, and ask for a targeted steer (/next) or a small recipe.

End.
