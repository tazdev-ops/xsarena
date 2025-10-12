# Style and Quality Profiles

This document describes the different content profiles available in XSArena and how to configure them in JobSpec files.

## Overview

Profiles define the approach, density, and style characteristics for content generation. Each profile combines specific settings for continuation, length, and narrative approach.

## Profile Types

### 1. Mastery Profile (Dense, Comprehensive)
**Purpose**: Maximally comprehensive content with dense narrative prose
**Characteristics**:
- Dense narrative prose without lists/checklists/drills
- High information density (4200-5200 characters per chunk)
- 24+ chunks for depth
- Coverage hammer enabled
- Repetition guard active

**JobSpec Configuration**:
```yaml
styles: [compressed]
continuation:
  mode: anchor
  minChars: 4200
  pushPasses: 2
  repeatWarn: true
system_text: |
  English only. Dense narrative prose. Avoid lists/checklists/drills. No forced headings beyond what you naturally need.
  Definitions inline only when helpful (no bold rituals). Remove filler; keep distinctions and mechanisms crisp.
  If approaching length limits, stop cleanly and end with: NEXT: [Continue].
```

### 2. Pedagogy Profile (Teaching-Focused)
**Purpose**: Educational content with teaching-before-use approach
**Characteristics**:
- Narrative overlay with teach-before-use principle
- Include examples and quick checks
- Moderate length (3000-4000 characters per chunk)
- Balanced approach between depth and clarity

**JobSpec Configuration**:
```yaml
styles: [narrative]
continuation:
  mode: anchor
  minChars: 3000
  pushPasses: 1
  repeatWarn: true
system_text: |
  English only. Teach-before-use approach. Define terms before use, include short vignettes.
  Use pedagogical principles: include examples and quick checks.
  Maintain consistent depth throughout.
```

### 3. Reference Profile (Terse, Factual)
**Purpose**: Concise, factual reference material
**Characteristics**:
- Minimal explanation, factual presentation
- Shorter chunks (2000-2500 characters)
- Direct, no-fluff approach
- Focus on facts and mechanisms

**JobSpec Configuration**:
```yaml
styles: [nobs]
continuation:
  mode: anchor
  minChars: 2500
  pushPasses: 0
system_text: |
  English only. Concise, factual presentation. Minimal explanation.
  Direct approach without fluff. Focus on facts and mechanisms.
```

### 4. Popular Science Profile
**Purpose**: Accessible content for general audiences
**Characteristics**:
- Engaging narrative style
- Analogies and relatable examples
- Balanced technical depth
- Storytelling approach

**JobSpec Configuration**:
```yaml
styles: [pop]
continuation:
  mode: anchor
  minChars: 3500
  pushPasses: 1
system_text: |
  English only. Popular science style. Use analogies and relatable examples.
  Engaging narrative that balances technical depth with accessibility.
  Include real-world applications and context.
```

## Using Profiles in JobSpecs

### Method 1: Direct Style Application
Apply profiles directly through the `styles` field in your JobSpec:

```yaml
task: book.zero2hero
subject: "Your Topic"
styles: [compressed]  # or [narrative], [nobs], [pop]
# ... other configuration
```

### Method 2: Profile-Specific System Text
Use profile-specific system text to achieve more granular control:

```yaml
task: book.zero2hero
subject: "Your Topic"
styles: [narrative]  # base style
system_text: |
  [Include profile-specific instructions here]
  This will override or complement the base style settings.
```

### Method 3: Predefined Profile Files
Reference external profile files in your JobSpec:

```yaml
task: book.zero2hero
subject: "Your Topic"
style_file: "directives/style.compressed_en.md"  # or other profile files
# ... other configuration
```

## Profile Switching

You can switch between profiles by modifying the `styles` field and/or `system_text` in your JobSpec. For best results:

1. Generate a base JobSpec: `xsarena z2h "Topic" --print-spec > recipes/topic.yml`
2. Edit the `styles` and `system_text` fields to match your desired profile
3. Run with the modified spec: `xsarena run.recipe recipes/topic.yml`

## Best Practices

1. **Choose the right profile upfront**: Select the most appropriate profile for your content goal
2. **Test with short runs**: Use `--max 2-3` chunks to validate profile behavior
3. **Document profile decisions**: Include comments in your JobSpec explaining profile choice
4. **Version control profiles**: Track profile configurations in your recipes/ directory
5. **Combine with continuation settings**: Pair profiles with appropriate `minChars` and `pushPasses` values

## Advanced Profile Combinations

You can combine multiple style elements in a single JobSpec:

```yaml
styles: [narrative, compressed]  # Combines teaching approach with dense prose
# Note: Order may matter - first style takes precedence where they conflict
```

## Troubleshooting Profile Issues

- If content doesn't match profile expectations: Check that `system_text` doesn't conflict with style settings
- If chunks are too short/long: Adjust `minChars` in continuation settings
- If narrative elements appear when not wanted: Use `[compressed]` style with stricter system text
- If content is too dense: Switch to `[narrative]` or `[pop]` profile

Profiles provide a structured approach to content generation, ensuring consistency and predictability in your outputs.# Command Matrix

This matrix provides a quick reference for XSArena commands and their primary functions.

## Core Commands

| Command | Function | Primary Use Case |
|---------|----------|------------------|
| `xsarena z2h` | Zero-to-Hero book generation | Comprehensive content from foundations to advanced practice (use with --print-spec for JobSpec-first) |
| `xsarena jobs` | Job management | Submit, list, resume, cancel, fork jobs |
| `xsarena serve` | Local web preview | Browse books and job artifacts with live monitoring |
| `xsarena snapshot` | Project snapshotting | Create project representation for debugging |
| `xsarena doctor` | Health checks | Verify environment and run smoke tests |
| `xsarena publish` | Export formats | Convert to EPUB/PDF |
| `xsarena audio` | Audio conversion | Create audiobooks from text |
| `xsarena lossless` | Text processing | Ingest and rewrite without meaning loss |
| `xsarena style` | Style management | Toggle narrative, nobs, compressed styles |
| `xsarena book` | Book authoring | Various book generation modes |

## Job Management Commands

| Command | Function | Use Case |
|---------|----------|----------|
| `xsarena jobs ls` | List jobs | View all jobs and their status |
| `xsarena jobs log` | View job log | Monitor job events and progress |
| `xsarena jobs resume` | Resume job | Restart a paused job |
| `xsarena jobs cancel` | Cancel job | Stop a running job |
| `xsarena jobs fork` | Fork job | Clone job to different backend |
| `xsarena jobs summary` | Job summary | Detailed metrics (chunks, stalls, retries) |
| `xsarena jobs run` | Run job | Execute a job from spec (alias: run.recipe) |
| `xsarena run.recipe` | Run recipe/spec | Execute a JobSpec from YAML/JSON file (canonical JobSpec-first path) |

## Study Tools

| Command | Function | Purpose |
|---------|----------|---------|
| `xsarena exam cram` | Quick prep | High-yield outlines and pitfalls |
| `xsarena flashcards from` | Create flashcards | Q/A cards from content |
| `xsarena glossary from` | Create glossary | Definitions and explanations |
| `xsarena index from` | Create index | Grouped topic index |

## Quality & Monitoring

| Command | Function | Purpose |
|---------|----------|---------|
| `xsarena quality score` | Score content | Evaluate content quality |
| `xsarena quality uniq` | Check uniqueness | Verify content originality |
| `xsarena doctor env` | Environment check | Verify setup and dependencies |
| `xsarena doctor run` | Smoke test | Run synthetic z2h test |

## Backend & Service

| Command | Function | Purpose |
|---------|----------|---------|
| `xsarena service start-bridge` | Start bridge server | Enable browser integration |
| `xsarena backend` | Backend config | Configure bridge/OpenRouter |
| `xsarena mode` | Mode toggles | Switch between different modes |

## Advanced Features

| Command | Function | Purpose |
|---------|----------|---------|
| `xsarena coder` | Coding session | Advanced coding with tickets/patches |
| `xsarena templates` | Templates | Manage templates registry |
| `xsarena import` | Import content | Convert PDF/DOCX/MD to Markdown |
| `xsarena rp` | Roleplay | Interactive roleplay sessions |
| `xsarena joy` | Daily activities | Streaks, achievements, kudos |
| `xsarena coach` | Coaching | Drills and boss exams |

## Output Knobs

| Command | Function | Effect |
|---------|----------|---------|
| `xsarena book minchars` | Set min chars | Control chunk length |
| `xsarena book passes` | Set passes | Control micro-continuations |
| `xsarena book budget` | Toggle budget | Push for max density |
| `xsarena book hammer` | Toggle hammer | Anti-wrap continuation hint |
| `xsarena book cont-mode` | Set continuation | Change strategy (normal/anchor) |
| `xsarena book repeat-warn` | Toggle warnings | Repetition alerts |
| `xsarena book repeat-thresh` | Set threshold | Repetition sensitivity |

## Quick Reference

### Common Workflows
- **Quick book**: `xsarena z2h "Topic" --max=6 --min=3000`
- **List jobs**: `xsarena jobs ls`
- **Check health**: `xsarena doctor env`
- **Create snapshot**: `xsarena snapshot run`
- **Serve locally**: `xsarena serve run`
- **Export**: `xsarena publish run <job_id> --epub --pdf`

### Job Lifecycle
1. Submit: `xsarena z2h "Topic"` or `xsarena jobs run spec.yml`
2. Monitor: `xsarena jobs log <id>` or `xsarena serve run`
3. Manage: `xsarena jobs resume/cancel/fork <id>`
4. Review: `xsarena jobs summary <id>`
5. Export: `xsarena publish run <id>`
