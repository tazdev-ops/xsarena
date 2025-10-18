# XSArena Bridge Documentation

## Overview

The XSArena Bridge is a WebSocket-based proxy server that connects XSArena to LMArena, enabling seamless interaction between the two systems. The bridge handles session and message ID management, Cloudflare protection, and provides a stable connection between XSArena and the LMArena web interface.

## Installation and Setup

### 1. Install the Userscript

First, install the userscript by adding `xsarena_bridge.user.js` to your browser extension (Tampermonkey, Greasemonkey, etc.).

### 2. Start the Bridge Server

```bash
xsarena service start-bridge-v2
```

The bridge server will start on port 5102 by default.

### 3. Configure Your Browser

Open https://lmarena.ai and add `#bridge=5102` to the URL to connect to the bridge.

## Capturing Session and Message IDs

### Interactive Method (Legacy)

Use the interactive cockpit to capture session and message IDs:

```bash
xsarena interactive
# Then use the /capture command
```

### Standalone Method (New)

Use the new standalone command to capture IDs:

```bash
xsarena config capture-ids
```

This command will:
1. Guide you to start the bridge and open LMArena
2. Send a start capture command to the bridge
3. Instruct you to click "Retry" in your browser
4. Poll the bridge for captured IDs
5. Save the IDs to your configuration file

## Bridge Reliability Features

### Cloudflare Auto-Refresh

The bridge includes automatic Cloudflare challenge detection and handling:
- When Cloudflare protection is detected, the bridge automatically sends a refresh command to the userscript
- The userscript will reload the page to bypass the challenge
- The bridge will continue processing after the challenge is resolved

### Idle Auto-Restart

The bridge includes an idle restart mechanism to maintain connection stability:
- Configurable timeout period (default: 1 hour)
- When idle timeout is reached, the bridge sends a reconnect command to the userscript
- The bridge process then restarts to maintain optimal performance

To enable idle restart, add the following to your `.xsarena/config.yml`:

```yaml
bridge:
  enable_idle_restart: true
  idle_restart_timeout_seconds: 3600  # 1 hour
```

## Endpoint Mapping

You can define multiple endpoint configurations in an `endpoints.yml` file to simplify workflow management.

### Creating endpoints.yml

Create a file named `endpoints.yml` in your project root:

```yaml
development:
  overlays: ["narrative", "no_bs"]
  extra: "Development mode - faster responses, less accuracy"
  length: "standard"
  span: "medium"
  bridge_session_id: "dev-session-id"
  bridge_message_id: "dev-message-id"

production:
  overlays: ["narrative", "no_bs", "quality-focus"]
  extra: "Production mode - highest accuracy"
  length: "long"
  span: "book"
  bridge_session_id: "prod-session-id"
  bridge_message_id: "prod-message-id"
  extra_files:
    - "policies/production-rules.md"
```

### Using Endpoints

Run with a specific endpoint configuration:

```bash
xsarena run book "My Subject" --endpoint development
```

This will apply all the settings defined in the `development` endpoint, including:
- Overlays and extra notes
- Length and span presets
- Bridge session and message IDs
- Extra files to include
- Output path
