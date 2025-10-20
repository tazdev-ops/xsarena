# Shared Jargon and Shortcuts

- Bridge: local FastAPI server + Firefox Tampermonkey userscript
- Health OK: GET /v1/health returns status:"ok"
- RunSpec: typed spec (subject, length, span, overlays, files, out path)
- /command: interactive REPL commands reusing the Typer app
- Preflight/Postflight: verify before/after doing (snapshots, runs)
- Verify categories: oversize, disallowed, secrets, binary, missing_required
- Minimal snapshot: xsarena ops snapshot txt (ultra-tight)
- Maximal snapshot: xsarena ops snapshot write (tight/full) + zip
- "QA lane": continuity + coverage + (optional) density check before release
- "Connect": start bridge, open /console, wait for ws_connected (wrapper optional)
