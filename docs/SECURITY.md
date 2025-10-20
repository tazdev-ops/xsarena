# Security Model (Bridge-first)

## Defaults to safe local use
- Bridge binds to 127.0.0.1 by default; override via XSA_BRIDGE_HOST if needed
- Public Bearer checks use constant-time compare
- /internal endpoints can be token-gated with X-Internal-Token (constant-time compare)
- Redaction: snapshot flattener and simple builder can redact secrets from content before sharing (on by default)

## Recommended practices
- Keep /internal token gating on if you export beyond localhost
- Use loopback host for the bridge unless you understand LAN exposure implications
- Add a short .gitignore entry for generated snapshot files:
  - repo_flat.txt
  - xsa_snapshot.txt
  - xsa_snapshot.zip
- Do not log request bodies or tokens; keep logs minimal and redacted

## First-run hints
- If the bridge isn't reachable, commands should print a friendly guide:
  - "Start the bridge first: xsarena ops service start-bridge-v2"
  - "Open your model page in Firefox with #bridge=5102 and click Retry"

## Secrets
- Utils include a secrets scanner:
  - xsarena ops health scan-secrets --path .
- Snapshot outputs should be verified before sharing (see docs/SNAPSHOT_VERIFY.md if you added it)
