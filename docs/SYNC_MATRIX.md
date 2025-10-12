# Sync Matrix

## What is this?
A simple list of known top-level items and their policy (keep/ignore/exclude from snapshot).

## Whitelist (keep tracked in git)
- src/
- directives/
- data/
- playbooks/
- recipes/
- docs/
- README.md
- CLI_AGENT_RULES.md
- pyproject.toml
- models.json
- xsarena_cli.py
- xsarena_doctor.py
- .gitignore
- legacy/
- contrib/

## Local State (not tracked)
- .xsarena/agent/

## Generated (ignored by default)
- xsarena.egg-info/
- docs/_help_*.txt
- snapshot_chunks/

## Exceptions
- SNAPSHOT+JOBS: include .xsarena/jobs/<job_id>/events.jsonl and job.json only when explicitly requested.
