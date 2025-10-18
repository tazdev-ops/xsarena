# Poet + Poem Translator Pack

This pack provides tools for poetry creation, translation, analysis, and scansion.

## Components

### Roles
- `role.poet_maker.md` - Composes original poems faithful to requested form, meter, and tone
- `role.poem_translator.md` - Produces literal and literary translations of poems
- `role.scansion_analyst.md` - Analyzes meter, rhyme, and sound devices
- `role.poem_explainer.md` - Provides reader-friendly explanations of poems

### Style Overlays
- `poetry_overlays.md` - Provides poetry form overlays like sonnet_shakespeare, villanelle, ghazal, etc.

### Prompt Templates (JSON)
- `poem_brief.json.md` - Creates structured poem briefs
- `poem_output.json.md` - Outputs poems in structured format
- `poem_translation_plan.json.md` - Plans poem translations
- `poem_translation_pairs.json.md` - Creates aligned literal and literary translations
- `scansion_report.json.md` - Analyzes poem scansion and metrics
- `poem_alignment.json.md` - Aligns source and target poem segments
- `poetic_glossary.json.md` - Creates poetic term glossaries
- `rhythm_options.json.md` - Explores meter and rhyme alternatives

## Usage Examples

### Original Poetry Creation
```
xsarena prompt run -s directives/roles/role.poet_maker.md -t "Theme: winter light; Form: sonnet (Shakespearean); Tone: contemplative"
```

### Poem Translation
```
xsarena prompt run -s directives/roles/role.poem_translator.md -t "SourceLang: Persian; TargetLang: English; Goal: preserve imagery and cadence"
```

### Translation Pairs
```
xsarena prompt run -s directives/prompt.poem_translation_pairs.json.md -t "Paste source text here" | jq .
```

### Scansion Analysis
```
xsarena prompt run -s directives/prompt.scansion_report.json.md -t "Paste the English poem here" | jq .
```

### Mix Overlays in Cockpit
```
/prompt.style on sonnet_shakespeare
/prompt.style on free_verse_contemporary
/prompt.style on meter_iambic_pentameter
/prompt.style on imagist_minimal
```

## Ready-to-try Examples

- Original poem (Shakespearean sonnet): role.poet_maker + overlays: sonnet_shakespeare, meter_iambic_pentameter, imagist_minimal
- Free verse, contemporary: role.poet_maker + overlays: free_verse_contemporary, imagist_minimal, alliterative_current
- Translation: Persian → English: role.poem_translator; then prompt.poem_translation_pairs.json.md to get aligned literal + literary outputs
- Scansion + analysis: role.scansion_analyst or prompt.scansion_report.json.md
- Explain a poem: role.poem_explainer for paraphrase/themes/devices

For more details on the suggested workflow, see the individual template files or the original documentation.
