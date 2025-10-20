# Defaults and Decisions

- Jobs:
  - Continue: prefer --resume; use --overwrite only on explicit Operator request
  - Always start with a dry-run
- Snapshots:
  - For sharing: txt ultra-tight with redaction; preflight verify; postflight verify optional
  - For ops: write tight/full + zip; avoid git/jobs/manifests context unless needed
- Bridge:
  - Loopback bind (127.0.0.1); /internal gated if token set; one Cloudflare refresh attempt
- Errors:
  - Prefer config/policy fixes; code patches only if blocked
  - Record errors in .xsarena/jobs/<id>/events.jsonl and open a small ticket
