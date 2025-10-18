# Configuration Guide

This document explains how to configure XSArena for your projects and workflows.

## Configuration Files

XSArena uses a layered configuration approach:

### 1. `.xsarena/config.yml`
This file contains project-specific defaults and can include a `settings:` section for persistent CLI knobs:

```yaml
# Bridge configuration
bridge:
  session_id: "your-session-id"
  message_id: "your-message-id"
  tavern_mode_enabled: false
  bypass_enabled: false
  enable_idle_restart: true
  stream_response_timeout_seconds: 300

# Default model and backend settings
model: "default"
backend: "bridge"
window_size: 100

# Output and continuation settings (persisted knobs)
settings:
  output_min_chars: 4500
  output_push_max_passes: 3
  continuation_mode: "anchor"
  anchor_length: 300
  repetition_threshold: 0.35
  repetition_warn: true
  smart_min_enabled: true
  outline_first_enabled: false
  semantic_anchor_enabled: true
```

### 2. `.xsarena/session_state.json`
This file contains dynamic session state that overrides config settings:

```json
{
  "output_min_chars": 5000,
  "continuation_mode": "anchor",
  "anchor_length": 350,
  "repetition_threshold": 0.32
}
```

## Managing Configuration

### Persisting Session Settings
To save current session settings to config.yml:

```bash
xsarena settings persist
```

### Resetting Session Settings
To reset session settings from config.yml:

```bash
xsarena settings reset
```

## Key Configuration Options

### Output Settings
- `output_min_chars`: Minimum characters per chunk (default: 4500)
- `output_push_max_passes`: Max micro-extend passes per chunk (default: 3)
- `output_push_on`: Toggle output push (default: true)

### Continuation Settings
- `continuation_mode`: 'anchor', 'normal', or 'semantic-anchor' (default: 'anchor')
- `anchor_length`: Length of text anchor in characters (default: 300)

### Repetition Settings
- `repetition_threshold`: Jaccard similarity threshold (0.0-1.0, default: 0.35)
- `repetition_warn`: Toggle repetition detection warning (default: true)

### Advanced Settings
- `smart_min_enabled`: Token-aware minimum length scaling
- `outline_first_enabled`: Outline-first seed for first chunk only
- `semantic_anchor_enabled`: Use semantic anchoring instead of text anchoring

## Endpoints Configuration

Create an `endpoints.yml` file to define multiple endpoint configurations:

```yaml
default_gpt4:
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o"
  api_key_env: "OPENAI_API_KEY"
  overlays: ["narrative", "no_bs"]

claude:
  base_url: "https://api.anthropic.com/v1"
  model: "claude-3-opus-20240229"
  api_key_env: "ANTHROPIC_API_KEY"
  overlays: ["compressed", "no_bs"]
```

Use endpoints with the `--endpoint` flag:

```bash
xsarena run book "Subject" --endpoint default_gpt4
```
