# Collaboration Protocol (Operator × Advisor × Agent)

Roles
- Operator (human): sets priorities, approves risky changes, owns outcomes.
- Advisor (higher AI): plans, audits, documents, proposes minimal patches, writes specs/rulebooks.
- Operator bot (CLI AI): executes commands, generates reports, applies small changes when explicitly asked, never "guesses" destructive actions.

Language (shortcuts)
- C2 = command-and-control (queue + status + reports)
- SOP = standard operating procedure (checklists)
- Preflight/Postflight = verify before/after actions
- Minimal snapshot = curated txt with caps; Maximal = write zip
- Health OK = /v1/health status ok (bridge)
- Resume vs Overwrite = explicit choice for jobs targeting same output

Decision rules (defaults)
- Snapshots: prefer minimal (txt) with redaction; verify before sharing
- Jobs: choose --resume unless Operator requests --overwrite
- Dangerous operations: require explicit Operator approval (e.g., deleting outputs)
- Bug fixes: prefer config/policy first; code patch only if truly blocked
- Logs: never log tokens; keep bodies out of logs

Escalation
- If blocked, create review/agent_ticket_<ts>.md with: repro, observed vs expected, environment, minimal patch idea, and request approval.

Safety constraints
- No shell=True; no secrets in logs
- Bind bridge to 127.0.0.1 by default; /internal gated when configured
- Redaction on for txt snapshots by default
