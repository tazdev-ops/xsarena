# src/xsarena/cli/cmds_orders.py
import time
from pathlib import Path

import typer

from .cmds_health import merge_rules  # reuse helper

app = typer.Typer(help="Append and list ONE ORDERs.")


def _ts():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC")


@app.command("new")
def new(title: str, body: str = typer.Option(None, "--body")):
    src = Path("directives/_rules/sources")
    src.mkdir(parents=True, exist_ok=True)
    log = src / "ORDERS_LOG.md"
    content = body or typer.edit("# Write your order body below\n")
    if content is None:
        typer.echo("Aborted.")
        raise typer.Exit(1)
    block = ["\n# ONE ORDER — " + title, f"Date (UTC): {_ts()}", content.strip(), "\n"]
    with log.open("a", encoding="utf-8") as f:
        f.write("\n".join(block))
    try:
        merge_rules.callback()  # invoke Typer command function
    except Exception:
        pass
    typer.echo(f"✓ logged → {log}")


@app.command("ls")
def ls():
    log = Path("directives/_rules/sources/ORDERS_LOG.md")
    if not log.exists():
        typer.echo("(no ORDERS_LOG.md yet)")
        return
    text = log.read_text(encoding="utf-8", errors="ignore").splitlines()
    heads = [ln for ln in text if ln.startswith("# ONE ORDER")]
    for ln in heads[-5:]:
        typer.echo("• " + ln.replace("# ", ""))
