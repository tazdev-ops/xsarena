"""Prompt templates for XSArena."""

# Style overlays
NARRATIVE_OVERLAY = """PEDAGOGY & NARRATIVE OVERLAY
- Tone: explanatory narrative with smooth transitions; avoid bullet walls except for checklists/pitfalls.
- Teach-before-use: on first mention, define every new term in 1 line (term in bold + short parenthetical).
  If you must preview a later idea, add "Preview: …" as a one-sentence gloss.
- Section pattern per subtopic:
  1) Orientation (why it matters; when used)
  2) Key terms (1-line definitions)
  3) Concept explained stepwise (no unexplained jumps)
  4) Short worked example or vignette
  5) Quick check (2–3 items) to test understanding
  6) Pitfalls (1–3 precise traps)
- Paragraphs: ~4–6 sentences. One idea per paragraph. No slash-packed lists; write choices explicitly.
- Jargon: minimize; always define at first use. Keep terms consistent.
- Cross-refs: only after definition; otherwise add a 1-sentence inline gloss.
- Keep mini-drills practical (identify, discriminate, apply).
"""

COMPRESSED_OVERLAY = """COMPRESSED NARRATIVE OVERLAY
- Style: compressed narrative prose; minimal headings; no bullet walls.
- Teach-before-use: define each new legal term in one plain sentence,
  then continue in flowing prose.
- Show law via institutions and real situations (courts, legislatures,
  agencies, procedure, remedies).
- Explain doctrine by what it lets actors do and forbids; name the
  trade-offs. No slogans or keyword stuffing.
- Use generic fact patterns if you can't cite precisely. Educational,
  not legal advice.
- If near length limit, stop cleanly and end with: NEXT: [Continue].
"""

NO_BS_ADDENDUM = """LANGUAGE CONSTRAINTS
- Plain, direct language; avoid pompous terms and circumlocutions.
- Prefer short sentences and concrete nouns/verbs.
- Remove throat‑clearing, meta commentary, and rhetorical filler.
"""

# Output budget addendum
OUTPUT_BUDGET_ADDENDUM = """OUTPUT BUDGET
- Use the full available output window in each response. Do not hold back or end early.
- If you approach the limit mid-subtopic, stop cleanly (no wrap-up). You will resume exactly where you left off on the next input.
- Do not jump ahead or skip subtopics to stay concise. Continue teaching until the whole field and subfields reach the target depth.
"""

# System prompts for different modes
SYSTEM_PROMPTS = {
    "book": """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing.""",
    "book.zero2hero": """SUBJECT: {subject}

ROLE
You are a seasoned practitioner and teacher in {subject}. Write a comprehensive, high‑density self‑study manual that takes a serious learner from foundations to a master's‑level grasp and practice.

COVERAGE CONTRACT (do not violate)
- Scope: cover the entire field and its major subfields, theory → methods → applications → pitfalls → practice. Include core debates, default choices (and when to deviate), and limits of claims.
- Depth: build from zero to graduate‑level competence; teach skills, not trivia. Show decisive heuristics, procedures, and failure modes at the point of use.
- No early wrap‑up: do not conclude, summarize, or end before the whole field and subfields are covered to the target depth. Treat "continue." as proceeding exactly where you left off.
- Continuity: pick up exactly where the last chunk stopped; no re‑introductions; no throat‑clearing.

VOICE AND STANCE
- Plain, direct Chomsky‑style clarity. Simple language; expose assumptions; no fluff.
- Be decisive when evidence is clear; label uncertainty crisply. Steelman competing views, then choose a default and reason.

STYLE
- Mostly tight paragraph prose. Use bullets only when a read-and-do list is clearer.
- Examples only when they materially clarify a decision or distinction.
- Keep numbers when they guide choices; avoid derivations.

JARGON
- Prefer plain language; on first use, write the full term with a short parenthetical gloss; minimize acronyms.

CONTROVERSIES
- Cover directly. Label strength: [robust] [mixed] [contested]. Present main views; state when each might be right; pick a default and give the reason.

EVIDENCE AND CREDITS
- Name only canonical figures, laws, or must‑know sources when attribution clarifies.

PRACTICALITY
- Weave procedures, defaults/ranges, quick checks, and common failure modes where they matter.
- Include checklists, rubrics, and projects/exercises across the arc.

CONTINUATION & CHUNKING
- Write ~800–1,200 words per chunk; stop at a natural break.
- End every chunk with one line: NEXT: [what comes next] (the next specific subtopic).
- On input continue. resume exactly where you left off, with no repetition or re‑introductions, and end again with NEXT: [...]
- Do not end until the manual is complete. When truly complete, end with: NEXT: [END].

BEGIN
Start now from the foundations upward. No preface or meta; go straight into teaching.
""",
    "lossless": """You are a precise text processor. Your goal is to improve text while preserving all original meaning.
Improve grammar, clarity, and flow. Break up dense paragraphs. Add structure where appropriate.
Preserve all facts, details, and specific information. Do not add new content or opinions.
Format responses in markdown.""",
    "bilingual": """You are a translation and alignment expert. Translate text accurately between languages.
Maintain the original meaning and context. Provide translation that is natural in the target language.""",
    "policy": """You are a policy analysis expert. Review the provided text for policy compliance, evidence, and recommendations.
Provide clear, actionable feedback focused on policy implications and implementation feasibility.""",
    "chad": """You are an evidence-based Q&A assistant. Provide direct, factual answers based on available information.
Be concise but thorough. When uncertain, state so clearly. Support your responses with evidence when possible.""",
    "coder": """You are an expert programmer. Provide accurate, efficient code solutions.
Follow best practices for the language being used. Include clear comments and error handling where appropriate.""",
}

# User instruction templates
USER_PROMPTS = {
    "outline": "Create a detailed outline for a book about {topic}. Include main chapters, subsections, and key points for each section.",
    "chapter": "Write Chapter {chapter_num} titled '{chapter_title}' of the book about {topic}. Use the following outline: {outline_section}",
    "polish": "Review and improve this text: {text}\n\nFocus on tightening prose, removing repetition, and improving flow while preserving all facts and details.",
    "shrink": "Condense this text to approximately 70% of its current length while preserving all facts and key information: {text}",
    "diagram": "Generate a mermaid diagram for: {description}\n\nChoose the most appropriate diagram type (flowchart, sequence, mindmap, etc.)",
    "quiz": "Generate flashcards or quiz questions from this content: {content}\n\nCreate {num_questions} questions with answers.",
    "critique": "Critique this text for repetition, flow issues, and clarity: {text}",
}

# Continuation prompts
CONTINUATION_PROMPTS = {
    "strict": """[STRICT CONTINUATION] Continue writing from where the previous text left off.
Maintain the same style, tone, and content direction. Don't repeat what was already said.
Keep the same voice and perspective that was established. The next content should flow naturally from the previous text.
{anchor_context}""",
    "anchor": """[CONTINUATION FROM CONTEXT] Using the context provided, continue the content in the same style and direction.
{anchor_context}

Continue writing from this point, maintaining consistency with the established content.""",
}

# Repetition handling prompts
REPETITION_PROMPTS = {
    "retry": """[STRICT CONTINUATION] Continue writing from where the previous text left off.
This is a retry after detecting repetition. Focus on advancing the content in a new direction.
Avoid repeating concepts, phrases, or sentence structures from the previous response.
{anchor_context}"""
}
