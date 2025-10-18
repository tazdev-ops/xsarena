# XSArena Directives

This directory contains various directive files for different specialized tasks in XSArena.

## Available Directive Packs

### Logical Fact Finder Pack
Tools for neutral, educational analysis of complex claims using definitions, logic, and evidence.

**Components:**
- **Roles:** Logical Fact Finder, Debate Referee (logic-first), Bayesian Reasoner
- **Style Overlays:** steelman-first, burden-of-proof, evidence-ladder, fallacy-scan, underdetermination-guard, clarity-first
- **JSON Templates:** claim_definition, argument_catalog, argument_evaluation, evidence_registry, bayesian_update_sheet, falsifiability_matrix, reasoned_brief

**Usage Example:**
```
xsarena prompt run -s directives/roles/role.logical_fact_finder.md -t "Question: Does God exist? Frame: classical theism; constraints: neutral, educational"
```

### Poet + Poem Translator Pack
Tools for poetry creation, translation, analysis, and scansion.

**Components:**
- **Roles:** Poet-Maker, Poem Translator, Scansion Analyst, Poem Explainer
- **Style Overlays:** sonnet_shakespeare, villanelle, ghazal, haiku_classic, free_verse_contemporary, meter_iambic_pentameter, imagist_minimal, alliterative_current
- **JSON Templates:** poem_brief, poem_output, poem_translation_plan, poem_translation_pairs, scansion_report, poem_alignment, poetic_glossary, rhythm_options

**Usage Example:**
```
xsarena prompt run -s directives/roles/role.poet_maker.md -t "Theme: winter light; Form: sonnet (Shakespearean); Tone: contemplative"
```

## Directory Structure
- `roles/` - Contains role-based directives that define specific AI personas and their behaviors
- `style/` - Contains style overlays that modify the behavior of roles
- `prompt/` - Contains JSON template directives for structured output
- `profiles/` - Contains profile-based directives
- `quickref/` - Contains quick reference materials

## Creating New Directives
When creating new directives, follow the established patterns:
- Roles define the primary persona and methodology
- Style overlays provide modular behavior modifications
- JSON templates provide structured output formats
- Documentation should include usage examples and clear explanations

For more detailed information about each pack, see:
- LOGICAL_FACT_FINDER.md
- POETRY_TRANSLATOR.md
