# Deprecations & Legacy Components

This document tracks deprecated components and their new locations/replacements.

## Deprecated Files & Locations

### Interactive Monolith
- **Old location**: `src/xsarena/interactive.py`
- **New location**: `legacy/interactive/interactive_monolith.py`
- **Status**: Moved to legacy/interactive/ directory
- **Note**: Monolithic interactive CLI deprecated; use xsarena interactive instead

### TUI Components
- **Old location**: `xsarena_tui.py` (root)
- **New location**: `contrib/tui/xsarena_tui.py`
- **Status**: Moved to contrib/ directory
- **Note**: Root stub maintains backward compatibility

### LMA-era Wrappers
- **Old location**: `lma_tui.py` (root)
- **New location**: `legacy/lma_tui.py`
- **Status**: Moved to legacy/ directory
- **Note**: No replacement; deprecated

- **Old location**: `lma_cli.py` (root)
- **New location**: `legacy/lma_cli.py`
- **Status**: Moved to legacy/ directory
- **Note**: Maintains backward compatibility with deprecation notice

## Migration Guide

### For Users of xsarena_tui.py
1. Update your import/references to point to `contrib/tui/xsarena_tui.py`
2. The root stub will continue to work but shows a deprecation warning

### For Users of LMA-era Tools
1. These are legacy components from the LMArena era
2. They have been moved to the `legacy/` directory
3. Use the modern `xsarena` CLI instead

## Timeline
- These changes were implemented to improve project organization
- Old locations will continue to work with deprecation warnings
- Full removal will happen in a future major release
