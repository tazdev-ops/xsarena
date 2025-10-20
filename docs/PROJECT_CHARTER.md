# Project Charter

Nature
- A local-first, bridge-first studio for generating, continuing, and analyzing long-form text (books, manuals, study materials) with reproducibility and safe resume.

Goals
- Produce high-quality, long-form output reliably with deterministic flows
- Keep users in control (local bridge + browser userscript)
- Make operations agent-friendly and non-interactive
- Enable lean, redacted snapshots for sharing

Non-goals
- Heavy GUIs; everything should be operable via CLI (and optional /command REPL)
- Cloud-only operation (bridge-first is the default, not SaaS-first)

Principles
- Secure-by-default bridge (loopback bind, constant-time token checks, /internal gated if configured)
- Single source of truth: Typer CLI (also reused by interactive /command)
- Declarative prompt composition (bases + overlays + extra files)
- Deterministic jobs (resume = last_done+1; prefer hints over anchors)
- Verify before share (snapshot preflight/postflight audit)
