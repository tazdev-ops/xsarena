#!/usr/bin/env python3
import json
import pathlib

import typer

app = typer.Typer(help="Summarize job metrics")


@app.command("job")
def job_summary(job_id: str):
    path = pathlib.Path(".xsarena") / "jobs" / job_id / "events.jsonl"
    if not path.exists():
        typer.echo("No events")
        raise typer.Exit(1)
    events = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    stalls = sum(1 for e in events if e.get("type") == "stalled")
    retries = sum(1 for e in events if e.get("type") == "retry")
    failovers = sum(1 for e in events if e.get("type") == "failover")
    chunks = sum(1 for e in events if e.get("type") == "section_done")
    tokens_in = sum(e.get("input_tokens", 0) for e in events if e.get("type") == "cost")
    tokens_out = sum(e.get("output_tokens", 0) for e in events if e.get("type") == "cost")
    cost = sum(e.get("estimated_cost", 0.0) for e in events if e.get("type") == "cost")
    print(
        json.dumps(
            {
                "job": job_id,
                "chunks": chunks,
                "stalls": stalls,
                "retries": retries,
                "failovers": failovers,
                "tokens": {"in": tokens_in, "out": tokens_out},
                "cost_usd": round(cost, 4),
            }
        )
    )
