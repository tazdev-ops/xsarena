# Solo Use Optimization Guide

This document explains the optimizations made to XSArena for solo users, making it a more streamlined and focused tool for individual use.

## Overview

XSArena has been optimized for solo users who want a focused, efficient tool for AI-powered writing and content creation. The optimizations include:

- Reduced command groups from 30+ to ≤10 core groups
- Config.yml as the single source of truth for settings
- Optional bridge usage (not mandatory)
- Simplified file structure
- Quality-of-life improvements

## Key Changes

### 1. Reduced Command Groups

The command structure has been simplified from over 30 groups to just 10 main groups:

- `run` - Run books or recipes in authoring mode
- `interactive` - Interactive authoring sessions
- `settings` - Unified settings interface
- `author` - Core content creation workflows
- `ops` - System health, jobs, services, and configuration
- `utils` - General utility commands
- `docs` - Documentation generation commands

This makes the tool much more approachable and reduces cognitive load.

### 2. Single Source of Truth

All configuration is now managed through `.xsarena/config.yml`. This file is the single source of truth for:

- Backend settings (openrouter, bridge, etc.)
- Output settings
- Project configuration
- API keys and endpoints

No more surprise overrides from `session_state.json` or other files.

### 3. Optional Bridge Usage

The bridge is now optional rather than mandatory:

- For users primarily using OpenRouter/Anthropic APIs: Use `backend=openrouter` in config.yml
- For users who need the bridge: Start it with `xsarena ops service start` when needed
- Bridge startup is no longer required for basic functionality

### 4. Quality-of-Life Improvements

#### Version Command
```bash
xsarena version
```
Shows the current XSArena version.

#### Quick Health Check
```bash
xsarena ops health quick
```
Performs a quick health check of core functionality.

#### Recent Jobs
```bash
xsarena ops jobs recent
```
Shows the 5 most recent jobs (configurable with `--count`).

## Configuration

Your main configuration file is located at `.xsarena/config.yml`. Example:

```yaml
backend: openrouter  # or 'bridge' if you use the bridge
output_dir: ./books
concurrency:
  total: 3
  bridge: 2
  openrouter: 1
```

## Typical Workflow

For solo users, a typical workflow looks like:

1. Configure your settings in `.xsarena/config.yml`
2. Run content creation jobs:
   ```bash
   xsarena run book "My Topic" --draft
   ```
3. Monitor jobs:
   ```bash
   xsarena ops jobs recent
   xsarena ops jobs ls
   ```
4. Check system health:
   ```bash
   xsarena ops health quick
   ```

## Advanced Groups (Hidden)

Some advanced groups have been hidden by default as they're primarily useful for multi-user or complex team scenarios. These can be re-enabled by uncommenting them in the registry if needed.

## Troubleshooting

### Bridge Not Starting
- Check if you actually need the bridge - if using OpenRouter API, you might not need it
- Ensure your config.yml has the correct backend setting
- Start the bridge explicitly with `xsarena ops service start` if needed

### Settings Not Applying
- Verify all settings are in `.xsarena/config.yml`
- Check that no other configuration files are overriding your settings
- Run `xsarena settings` to see the current effective configuration

## Benefits for Solo Use

- **Simpler interface**: Fewer commands to learn and remember
- **Faster startup**: Less initialization overhead
- **Clearer configuration**: Single file controls everything
- **More reliable**: Reduced complexity means fewer points of failure
- **Better focus**: Concentrated on the core use case of AI-powered writing
