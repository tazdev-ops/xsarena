Agent QuickRef — XSArena (Compressed Narrative) (1 page)

Purpose
- Tell the AI exactly how we work: which workflows to use, which knobs to set, how to recover mid‑run.
- Tone: compressed narrative, dense mastery by default; maximize information density.

Defaults (set these unless told otherwise)
- English only. Define terms before use; keep flow in dense prose (minimal headings, no bullet walls).
- Continuation: anchor mode; do not restart sections; do not wrap up early.
- No fluff; maximize information density per paragraph.

Core Knobs (preferred ranges)
- /cont.mode anchor; /cont.anchor 200
- /repeat.warn on; /repeat.thresh 0.35
- /out.minchars 4800–5200 (dense narrative)
- /out.passes 2 (longer: 3; terse: 1)
- /book.hammer on (anti‑wrap)
- Style: /style.nobs on (no‑BS), /style.compressed on (dense narrative). Turn off narrative style.

Workflows (pick one)
1) Mastery Manual (Zero‑to‑Hero, compressed)
   - Use when teaching with maximum density and flow.
   - Commands:
     - /style.nobs on; /style.compressed on
     - /out.minchars 4800; /out.passes 2
     - /z2h "TOPIC" --out=./books/TOPIC.final.md --max=12 --min=4200
   - If it lists too much: /out.passes 0; keep dense prose.

2) Lossless‑First → Pedagogy (when you have sources)
   - Build synth → rewrite → pedagogy.
   - Commands:
     - xsarena lossless ingest sources/corpus.md books/topic.synth.md --chunk-kb 100 --synth-chars 16000
     - xsarena lossless rewrite books/topic.synth.md books/topic.lossless.md
     - /z2h "TOPIC" --out=./books/TOPIC.final.md --max=8 --min=4800
     - /out.minchars 4800; /out.passes 2

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
- Standard narrative (less dense, flowing, more prose): /style.compressed off; /style.narrative on; /out.minchars 4200; /out.passes 1
- Reference handbook (tight, definitions first): use book.reference or keep z2h with lower passes and clearer headings.

Mid‑Run Troubleshooting
- Too listy or heading‑happy → /style.compressed on; /out.passes 2; keep dense narrative paragraphs.
- Too terse → /out.passes 3; /out.minchars 5200.
- Repeating → /repeat.warn on; /book.pause; /next "Continue exactly from anchor. No restart. No wrap‑up."
- Bridge stalls → /cf.status → solve in browser → /cf.resume → /book.resume.

Hygiene & Health (quick)
- Snapshot: xsarena snapshot run --chunk
- Quick doctor: xsarena doctor env
- Live preview: xsarena serve run (tail logs)
- Jobs: xsarena jobs ls | xsarena jobs summary <id>

Prompts (lightweight, reusable)
- "Max‑dense narrative; define terms inline; minimal headings; prose flow; avoid bullet walls unless clarity demands it. Continue exactly; no restarts; no early wrap‑ups."
- For standard narrative: "Teach‑before‑use; define terms inline; prose flow; avoid bullet walls."

Escalation (ask for help)
- If loop or drift persists: snapshot, jot the problem in docs/OUTBOX.md, and ask for a targeted steer (/next) or a small recipe.

End.
