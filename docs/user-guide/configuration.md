# Configuration

XSArena uses a layered configuration system that combines default values, file-based configuration, and runtime settings.

## Configuration Files

### Main Configuration File

The main configuration file is located at `.xsarena/config.yml`. If it doesn't exist, XSArena will use default values.

Example configuration:

```yaml
# Backend configuration
backend: bridge  # Options: bridge, openrouter, null
model: default   # Model name (backend-specific)
base_url: http://localhost:5102/v1  # Bridge server URL
api_key: ""      # API key for OpenRouter (leave empty for bridge)

# Job execution settings
window_size: 100           # History window size
continuation_mode: anchor  # Options: anchor, strict, off
anchor_length: 300         # Length of continuation anchor
max_retries: 3            # Max retries for failed requests
timeout: 300              # Request timeout in seconds

# Output control
output_min_chars: 3000         # Minimum characters per chunk
output_push_max_passes: 3      # Maximum micro-extend passes
repetition_threshold: 0.35     # Similarity threshold for repetition detection
repetition_warn: true          # Warn on repetition detection

# Features
redaction_enabled: false       # Enable automatic redaction
coverage_hammer_on: true       # Anti-wrap continuation
reading_overlay_on: false      # Further reading suggestions

# Bridge-specific settings
bridge:
  session_id: ""                         # LMArena session ID
  message_id: ""                         # LMArena message ID
  enable_idle_restart: false             # Auto-restart on idle
  idle_restart_timeout_seconds: 3600     # Idle timeout (1 hour)
  stream_response_timeout_seconds: 360   # Stream timeout (6 minutes)
  tavern_mode_enabled: false             # Tavern mode (merge system messages)
  bypass_enabled: false                  # Bypass mode (add trailing user message)

# Scheduler settings
scheduler:
  max_concurrent: 1              # Global concurrent job limit
  concurrency:
    total: 1                     # Total concurrent jobs
    bridge: 1                    # Bridge backend limit
    openrouter: 1                # OpenRouter backend limit
  quiet_hours:
    enabled: false               # Enable quiet hours
    monday: [22, 6]             # Start hour, end hour (24h format)
    # Add other days as needed

# Advanced settings
settings:
  smart_min_enabled: false           # Token-aware min chars scaling
  outline_first_enabled: false       # Generate outline first
  semantic_anchor_enabled: false     # Use semantic anchors
  lossless_enforce: false            # Enforce lossless metrics
  target_density: 0.55               # Target lexical density
  max_adverbs_per_k: 15             # Max adverbs per 1000 words
  max_sentence_len: 22               # Max average sentence length
```

## Session State

In addition to the main configuration, XSArena maintains session state in `.xsarena/session_state.json`. This file stores runtime settings that persist between commands in a session.

## Configuration Commands

### Show Current Settings

```bash
xsarena settings show
```

### Set Specific Settings

```bash
xsarena settings set --backend bridge
xsarena settings set --output-min-chars 4000
xsarena settings set --repetition-threshold 0.35
```

### Persist Current Settings

```bash
xsarena settings persist
```

This saves current CLI settings to the configuration file.

### Reset to Persisted Settings

```bash
xsarena settings reset
```

## Backend Configuration

### Bridge Backend (Default)

The bridge backend connects to a local server that interfaces with LMArena. Configure with:

```bash
xsarena settings set --backend bridge
xsarena settings set --base-url http://localhost:5102/v1
```

### OpenRouter Backend

To use OpenRouter, configure with your API key:

```bash
xsarena settings set --backend openrouter
xsarena settings set --api-key your-openrouter-api-key
xsarena settings set --model openrouter/auto
```

## Advanced Configuration

### Concurrency Settings

Control how many jobs can run simultaneously:

```yaml
scheduler:
  max_concurrent: 1
  concurrency:
    total: 1
    bridge: 1
    openrouter: 1
```

### Quiet Hours

Schedule when jobs should not run:

```yaml
scheduler:
  quiet_hours:
    enabled: true
    monday: [22, 6]    # Don't run jobs from 10 PM to 6 AM on Mondays
    tuesday: [23, 7]   # Don't run jobs from 11 PM to 7 AM on Tuesdays
```

## Troubleshooting Configuration Issues

If you encounter configuration-related issues:

1. Check that your config file is valid YAML: `python -c "import yaml; print(yaml.safe_load(open('.xsarena/config.yml')))"`

2. Run the health check: `xsarena ops health fix-run`

3. Verify backend connectivity: `xsarena backend ping`