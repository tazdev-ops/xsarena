# Operations: Bridge + Health + Troubleshooting

## Start and connect the bridge
- Start:
  - xsarena ops service start-bridge-v2
- Health:
  - curl http://127.0.0.1:5102/v1/health
- Connect the userscript:
  - Open your model page in Firefox; add #bridge=5102 to the URL; click "Retry"
  - Bridge logs: "✅ Userscript connected via WebSocket."

Optional helper ideas (if enabled in your build)
- connect wrapper:
  - xsarena ops service connect
  - Starts the bridge, opens /console, opens your launch URL#bridge=PORT, waits for ws_connected

## Health and quick smoke
- Quick check:
  - xsarena settings config-check
  - xsarena dev simulate "Sanity" --length standard --span medium
  - xsarena run book "Sanity" --dry-run
- Jobs health:
  - xsarena ops jobs ls
  - xsarena ops jobs follow JOB_ID

## Troubleshooting
- Bridge "Unauthorized" on /internal/*:
  - You enabled token gating. Add header: X-Internal-Token: YOUR_TOKEN (see .xsarena/config.yml under bridge.internal_api_token)
- Cloudflare page blocks requests:
  - The bridge attempts one automatic refresh; if it still fails, solve the challenge in the browser tab and retry.
- "Bridge not reachable":
  - Ensure: xsarena ops service start-bridge-v2
  - Your base_url should be http://127.0.0.1:5102/v1
- Resume duplicates content:
  - Prefer sending "next" hints; resume is last_done + 1 with anchor from file tail for chunk>1. If problem persists, run continuity check and adjust anchor length in settings.

## Useful environment/config knobs
- XSA_BRIDGE_HOST: override default host (defaults to 127.0.0.1)
- .xsarena/config.yml
  - bridge:
    - internal_api_token: "<secret>"
    - stream_response_timeout_seconds: 360
    - cloudflare_patterns: ["Just a moment", "Checking your browser"]
    - max_refresh_attempts: 1
