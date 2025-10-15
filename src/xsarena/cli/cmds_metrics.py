"""Metrics commands for XSArena - cost tracking and observability."""

from __future__ import annotations

import typer

app = typer.Typer(help="Metrics and observability commands.")

@app.command("show")
def metrics_show():
    """Show current metrics summary."""
    try:
        from ..utils.metrics import get_metrics
        metrics_collector = get_metrics()
        
        typer.echo("=== XSArena Metrics Summary ===")
        typer.echo(f"Prometheus available: {metrics_collector._enabled}")
        
        total_cost = metrics_collector.get_total_cost()
        typer.echo(f"Total estimated cost: ${total_cost:.4f}")
        
        if metrics_collector._job_costs:
            typer.echo("Costs by model:")
            for model, cost in metrics_collector._job_costs.items():
                typer.echo(f"  {model}: ${cost:.4f}")
    except Exception as e:
        typer.echo(f"Metrics not available: {e}")
        typer.echo("Metrics will work when extras are installed: pip install xsarena[metrics]")


@app.command("start-server")
def metrics_start_server(port: int = typer.Option(8000, "--port", "-p", help="Port to start metrics server on")):
    """Start the metrics server."""
    try:
        from ..utils.metrics import get_metrics
        metrics_collector = get_metrics()
        metrics_collector.start_server(port)
        typer.echo(f"Metrics server started on port {port} (if prometheus is available)")
    except Exception as e:
        typer.echo(f"Failed to start metrics server: {e}")
        typer.echo("Install extras to enable metrics: pip install xsarena[metrics]")


@app.command("status")
def metrics_status():
    """Show metrics system status."""
    try:
        from ..utils.metrics import get_metrics
        metrics_collector = get_metrics()
        typer.echo(f"Metrics system enabled: {metrics_collector._enabled}")
        typer.echo(f"Total tracked models: {len(metrics_collector._job_costs)}")
        typer.echo(f"Total estimated cost: ${metrics_collector.get_total_cost():.4f}")
    except Exception as e:
        typer.echo(f"Metrics not available: {e}")
        typer.echo("Metrics will work when extras are installed: pip install xsarena[metrics]")