from __future__ import annotations

import asyncio
import importlib
import os
import platform
import sys
from typing import Optional

import typer

app = typer.Typer(
    help="Health checks and smoke tests (DEPRECATED: use ops health instead)",
    hidden=True,
)


def _ok(m):
    typer.echo(f"[OK] {m}")


def _warn(m):
    typer.echo(f"[WARN] {m}")


def _err(m):
    typer.echo(f"[ERR] {m}")


@app.command("env")
def env():
    py = sys.version.split()[0]
    _ok(f"Python {py} on {platform.platform()}")
    req = ["typer", "aiohttp", "pydantic", "yaml", "requests", "rich"]
    miss = []
    for mod in req:
        try:
            importlib.import_module(mod)
        except Exception:
            miss.append(mod)
    if miss:
        _warn("Missing modules: " + ", ".join(miss))
        raise typer.Exit(code=1)


@app.command("ping")
def ping(
    ctx: typer.Context,
    backend: Optional[str] = typer.Option(None, "--backend"),
    retries: int = typer.Option(1, "--retries", help="Number of retry attempts"),
    delay: float = typer.Option(
        0.5, "--delay", help="Delay between retries in seconds"
    ),
    deep: bool = typer.Option(
        False, "--deep", help="Show detailed diagnostic information"
    ),
):
    typer.echo(
        "⚠️  WARNING: 'xsarena doctor ping' is deprecated. Use 'xsarena ops settings backend-test' instead."
    )

    cli = ctx.obj
    if backend:
        cli.state.backend = backend

    # Rebuild engine to ensure backend matches the requested type
    if backend:
        from ..core.backends import create_backend

        cli.engine.backend = create_backend(
            cli.state.backend,
            base_url=os.getenv("XSA_BRIDGE_URL", cli.config.base_url),
            api_key=cli.config.api_key,
            model=cli.state.model,
        )

    async def _go():
        last = None
        for i in range(retries):
            try:
                ok = await cli.engine.backend.health_check()
                if ok:
                    _ok("Bridge health: OK")
                    return 0
                last = "down"
            except Exception as e:
                last = e
            if i < retries - 1:
                await asyncio.sleep(delay)
        _err(f"Bridge health: DOWN ({last})")
        return 2

    raise typer.Exit(code=asyncio.run(_go()))


@app.command("run")
def run(ctx: typer.Context):
    typer.echo(
        "⚠️  WARNING: 'xsarena doctor' is deprecated. Use 'xsarena ops health' instead."
    )
    typer.echo("Running equivalent ops health commands...")

    try:
        env()
    except SystemExit as e:
        raise typer.Exit(code=e.code)

    # Use ctx.invoke to reuse Typer's context instead of creating a new one
    try:
        # Find the ping command in the app
        if hasattr(app, "commands") and "ping" in app.commands:
            ping_callback = app.commands["ping"]
            ctx.invoke(ping_callback, backend=None, retries=1, delay=0.5, deep=False)
        else:
            # Fallback if invoke doesn't work
            ping(ctx, backend=None, retries=1, delay=0.5, deep=False)
    except SystemExit as e:
        raise typer.Exit(code=e.code)
    except:
        # Fallback to direct call if invoke doesn't work
        ping(ctx, backend=None, retries=1, delay=0.5, deep=False)

    _ok(
        "Doctor run complete. Please use 'xsarena ops health' for future health checks."
    )
