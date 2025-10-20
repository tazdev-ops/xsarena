# Troubleshooting

## The bridge won't connect
- Ensure it's running:
  - xsarena ops service start-bridge-v2
- Health endpoint:
  - curl http://127.0.0.1:5102/v1/health
- Open your model page with #bridge=5102 and click "Retry"
- If /internal endpoints are gated, set X-Internal-Token in tools that call them

## Commands say "Bridge not reachable"
- Your base_url should be http://127.0.0.1:5102/v1
- Start the bridge first; then retry the command

## Resume duplicated content
- Use "next" hints for fine control:
  - xsarena ops jobs next JOB_ID "Continue with <section>"
- Adjust SessionState anchor_length; consider raising to 360–420 if continuity is weak

## Hangs/loops on micro-extends
- Lower output_push_max_passes or min_chars
- Ensure repetition_threshold is reasonable (0.32–0.40 is a typical range)

## Cloudflare page blocks responses
- The bridge attempts one refresh; if it still fails, complete the challenge in the browser tab and retry

## Large files cause "argument list too long"
- Avoid passing entire files via shell args; prefer the Python helper pattern (see docs/USAGE.md translation section)
