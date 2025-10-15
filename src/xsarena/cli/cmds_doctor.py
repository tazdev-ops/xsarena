from __future__ import annotations
import os
import sys
import platform
import importlib
import asyncio
from typing import Optional
import typer
from .context import CLIContext

app = typer.Typer(help="Health checks and smoke tests")


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
    req = ["typer", "aiohttp", "pydantic", "yaml"]
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
def ping(backend: Optional[str] = typer.Option(None, "--backend")):
    ctx = CLIContext.load()
    if backend:
        ctx.state.backend = backend
    if ctx.state.backend == "bridge":
        async def _go():
            import aiohttp
            url = (ctx.config.base_url or "").rstrip("/") + "/health"
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=8) as r:
                        j = await r.json()
                        _ok(f"Bridge health: {j}")
                        return 0
            except Exception as e:
                _err(f"Bridge ping failed: {e}")
                _warn("Start bridge: xsarena service start-bridge; userscript on; click Retry; rerun.")
                return 2
        raise typer.Exit(code=asyncio.run(_go()))
    else:
        if not (os.getenv("OPENROUTER_API_KEY") or ctx.config.api_key):
            _err("OPENROUTER_API_KEY not set")
            _warn("export OPENROUTER_API_KEY=... then rerun.")
            raise typer.Exit(code=2)
        _ok("OpenRouter config present.")
        raise typer.Exit(code=0)


@app.command("run")
def run():
    try:
        env()
    except SystemExit as e:
        raise typer.Exit(code=e.code)
    try:
        ping()
    except SystemExit as e:
        raise typer.Exit(code=e.code)
    _ok("Doctor run complete.")