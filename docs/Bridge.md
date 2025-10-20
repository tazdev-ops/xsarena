# Bridge v2 (Local-first)

Start
- xsarena ops service start-bridge-v2
- Open your LMArena page and add #bridge=5102 if your userscript expects it.

Health
- GET $(base_url)/v1/health → {"status":"ok","ws_connected":true|false,...}
  - base_url is normalized to end with /v1 in settings.

Capture IDs (recommended)
- xsarena unified-settings capture-ids
  - Sends /internal/start_id_capture to the bridge
  - Instructs you to click "Retry" in the browser
  - Polls /internal/config and persists bridge.session_id/message_id to .xsarena/config.yml

Models
- GET /v1/models returns current map; POST /internal/update_available_models updates via userscript page source.

Notes
- Cloudflare: bridge auto-refresh uses a guarded retry; let it finish.
- Idle restart: enable in config if desired; streams are respected.