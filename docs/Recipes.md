# Recipes

This document explains how to create and use recipes for XSArena.

## Recipe Structure

Recipes are YAML files that define how to generate content. They specify:

- Task type (book, continue, etc.)
- Subject matter
- Styling options
- Continuation settings
- Output configuration

## Example Recipe

```yaml
task: book.zero2hero
subject: Clinical Psychology
styles: [no-bs, compressed]
hammer: true
continuation:
  mode: anchor
  anchorLen: 300
  minChars: 4500
  pushPasses: 3
io:
  output: file
  outPath: ./books/clinical-psychology.manual.md
max_chunks: 10
outline_first: true
```

## Key Parameters

- `task`: The type of task to perform
- `subject`: The main topic to cover
- `styles`: List of styling overlays to apply
- `hammer`: Whether to enable coverage hammer (prevents summarization)
- `continuation.mode`: How to continue writing (anchor, normal, semantic-anchor)
- `continuation.anchorLen`: Length of text anchor in characters
- `continuation.minChars`: Minimum characters per chunk
- `continuation.pushPasses`: Maximum micro-extend passes
- `max_chunks`: Maximum number of chunks to generate
- `outline_first`: Whether to start with an outline

## Dry Run and Preview

To preview what a recipe would do without running it:

```bash
xsarena preview --recipe recipes/your-recipe.yml
```

This shows the prompt that would be sent to the AI without actually generating content.
