# Overlays

This document explains how to use overlays to modify the style and pedagogy of generated content.

## Built-in Overlays

XSArena comes with several built-in overlays:

- `narrative` - Creates narrative, story-like content
- `no_bs` - Produces direct, no-nonsense content
- `compressed` - Generates concise, information-dense content
- `bilingual` - Creates content in two languages

## Toggle Overlays

You can toggle overlays on/off:

```bash
# In CLI
xsarena style no_bs on
xsarena style compressed off

# In interactive mode
/prompt.style on no_bs
/prompt.style off compressed
```

## Creating Custom Overlays

Custom overlays can be created by adding files to the `directives/` directory. Each overlay file should contain instructions for the AI model on how to modify its output style.

## Further Reading Overlay

The "Further Reading" overlay adds recommended resources at the end of major sections:

```bash
xsarena style reading on    # Enable
xsarena style reading off   # Disable
```

This uses the resource mapping in `data/resource_map.en.json` to suggest relevant materials.
