# Bridge v2 (Local-first, Modular)

Overview
- FastAPI server with WebSocket to a userscript tab.
- Per-request Cloudflare detection + refresh; per-peer rate limits; simple image markdown passthrough.
- IDs captured via internal endpoints + CLI helpers; stored in .xsarena/config.yml.

Start + Health
- Start bridge: xsarena ops service start-bridge-v2
- Health: GET $(base)/v1/health → {"status":"ok","ws_connected":true|false,...}
  - base_url normalized to end with /v1

Capture IDs (recommended)
- xsarena unified-settings capture-ids
  - Sends /internal/start_id_capture to the bridge
  - Instructs you to click "Retry" in your browser
  - Polls /internal/config
  - Persists bridge: {session_id, message_id} into .xsarena/config.yml

Models
- GET /v1/models shows the current list
- Update via POST /internal/update_available_models (userscript posts page source)
- Per-model mapping (optional): model_endpoint_map.json supports session/message IDs and mode/battle_target

Guards
- Cloudflare: automatic refresh with a capped retry per request
- Rate limits: per-peer "burst/window" read from CONFIG on each call
- Idle restart: optional with reconnect message; disabled during active streams

Notes
- API key (optional): set CONFIG.api_key to enforce Authorization: Bearer
- Image outputs: userscript stream is parsed; image URLs become markdown: ![Image](url)
