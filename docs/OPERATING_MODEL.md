# Operating Model (How it runs)

- Single source of truth: Typer CLI (also reused in /command REPL)
- Orchestrator composes system_text from templates + overlays; JobManager submits; JobExecutor loops (anchors + hints + micro-extends)
- Backends via transport factory; bridge-first default
- Artifacts: .xsarena/jobs/<id> (job.json + events.jsonl + outputs); run manifests saved
- Snapshots via txt (share) or write (ops/debug); verify gate ensures health
