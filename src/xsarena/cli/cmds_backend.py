"""Backend management commands for XSArena."""

import os
from typing import Optional

import typer

app = typer.Typer(help="Backend configuration commands")


@app.command("set")
def backend_set(
    router: Optional[str] = typer.Option(None, "--router", help="Set router backend (litellm|openrouter)"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="LiteLLM base URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for backend"),
    model: Optional[str] = typer.Option(None, "--model", help="Default model to use"),
):
    """Configure backend settings."""
    changes = []

    if router:
        os.environ["XSA_ROUTER_BACKEND"] = router
        changes.append(f"router={router}")

    if base_url:
        os.environ["LITELLM_BASE"] = base_url
        changes.append(f"base_url={base_url}")

    if api_key:
        os.environ["LITELLM_API_KEY"] = api_key
        os.environ["OPENROUTER_API_KEY"] = api_key  # Also set for OpenRouter
        changes.append("api_key=***")

    if model:
        os.environ["XSA_DEFAULT_MODEL"] = model
        changes.append(f"model={model}")

    if changes:
        typer.echo(f"Backend settings updated: {', '.join(changes)}")
    else:
        typer.echo("Use --router, --base-url, --api-key, or --model to configure settings")

    # Show current settings
    typer.echo(f"Current router: {os.getenv('XSA_ROUTER_BACKEND', 'openrouter')}")
    typer.echo(f"Current base URL: {os.getenv('LITELLM_BASE', 'not set for LiteLLM')}")
    typer.echo(f"Current model: {os.getenv('XSA_DEFAULT_MODEL', 'default')}")


@app.command("show")
def backend_show():
    """Show current backend configuration."""
    typer.echo(f"Router backend: {os.getenv('XSA_ROUTER_BACKEND', 'openrouter')}")
    typer.echo(f"LiteLLM base: {os.getenv('LITELLM_BASE', 'not set')}")
    typer.echo(f"OpenRouter API key: {'set' if os.getenv('OPENROUTER_API_KEY') else 'not set'}")
    typer.echo(f"Default model: {os.getenv('XSA_DEFAULT_MODEL', 'default')}")
    typer.echo("Available routers: openrouter, litellm")
