# Style and Quality Profiles

This document contains standardized style and quality profiles for XSArena content generation.

## Content Styles

### No-Bullshit (No-BS)
- Direct, to-the-point language
- No fluff or unnecessary explanations
- Focus on actionable information
- Minimal examples, maximum substance
- Command: `/style.nobs on`

### Narrative Overlay
- Teach-before-use approach
- Define terms before first use (with bold emphasis)
- Include short vignettes and examples
- Quick checks and pitfall warnings
- Command: `/style.narrative on`

### Compressed Narrative
- Dense prose style with minimal drill/checklist elements
- Focus on flowing paragraphs over bullet points
- Avoid forced headings beyond natural needs
- Maximize information density
- Command: `/style.compressed on`

### Popular Science
- Accessible language for general audiences
- Analogies and relatable examples
- Engaging storytelling elements
- Balance between depth and accessibility
- Command: `/book.pop "Topic"`

## Quality Profiles

### Pedagogy Profile (XSA_QUALITY_PROFILE=pedagogy)
- Emphasizes teaching and learning
- More examples and explanations
- Step-by-step breakdowns
- Quick checks and summaries
- Use: `XSA_QUALITY_PROFILE=pedagogy xsarena ...`

### Compressed Profile (XSA_QUALITY_PROFILE=compressed)
- Maximum information density
- Minimal redundancy
- Focus on core concepts and mechanisms
- Avoid verbose explanations
- Use: `XSA_QUALITY_PROFILE=compressed xsarena ...`

## Output Knobs and Settings

### Character Minimums (/out.minchars)
- Default: 4500 characters per chunk
- Dense content: 4800-5200
- Light content: 3000-3500
- Command: `/out.minchars <N>`

### Extension Passes (/out.passes)
- Default: 3 passes maximum
- Dense content: 0-1 passes (tighter control)
- Exploratory content: 2-3 passes (more development)
- Command: `/out.passes <N>`

### Budget Addendum (/out.budget)
- Append output budget snippet to prompts
- Encourages density and completion
- Command: `/out.budget on|off`

### Continuation Modes

#### Anchor Mode (/cont.mode anchor)
- Uses tail of last output as continuation context
- Prevents repetition and maintains flow
- Default: 200 character anchors
- Command: `/cont.anchor <N>` to adjust length

#### Normal Mode (/cont.mode normal)
- Standard continuation without anchoring
- Less context preservation
- Use when anchor mode causes issues

## Repetition Guards

### Warning System (/repeat.warn)
- Detects and warns about repetitive content
- Can auto-pause for manual intervention
- Command: `/repeat.warn on|off`

### Threshold Control (/repeat.thresh)
- Jaccard similarity threshold (0.0-1.0)
- Default: 0.35 (35% similarity triggers warning)
- Lower values = more sensitive
- Command: `/repeat.thresh <0..1>`

## Coverage Hammer (/book.hammer)
- Prevents early wrap-up or conclusion
- Maintains continuation for comprehensive coverage
- Particularly useful for self-study materials
- Command: `/book.hammer on|off`

## Study Aid Profiles

### Flashcard Generation
- Question/Answer format
- Focus on definitions and key concepts
- 200-300 cards typical for comprehensive topic
- Command: `/flashcards.from <synth> <out> [n=200]`

### Glossary Generation
- A-Z organization of terms
- Tight definitions with "why it matters"
- Contextual examples where needed
- Command: `/glossary.from <synth> <out>`

### Index Generation
- Grouped by topics and subtopics
- Quick lookup structure
- Hierarchical organization
- Command: `/index.from <synth> <out>`

## Quality Metrics

### Uniqueness Threshold
- Minimum originality percentage
- Default: 80% for acceptable content
- Command: `xsarena quality uniq <file>`

### Quality Scoring
- 1-10 scale for content quality
- Considers clarity, completeness, accuracy
- Command: `xsarena quality score <file>`

## Custom Profile Creation

To create custom style profiles:

1. Generate a synthesis with desired characteristics
2. Capture the style: `xsarena style.capture <reference> <profile>`
3. Apply to new topics: `xsarena style.apply <profile> <topic> <output>`

Example custom profile workflow:
```
# Create reference content with desired style
xsarena z2h "Reference Topic" --out=refs/reference_style.md --max=2

# Capture the style
xsarena style.capture refs/reference_style.md profiles/custom.style.md

# Apply to new topics
xsarena style.apply profiles/custom.style.md "New Topic" books/new_content.md
```
