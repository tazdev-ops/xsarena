from __future__ import annotations
import subprocess, sys
from pathlib import Path
import typer

app = typer.Typer(help="Snapshot (unified): writes a single-file minimal snapshot to your home directory")

def _py() -> str:
    return sys.executable

@app.command("write")
def snapshot_write(out: str = typer.Option("", "--out", "-o", help="Override output path (default: ~/xsa_min_snapshot.txt)")):
    """Write a single-file minimal snapshot to $HOME or a provided path."""
    args = [_py(), "tools/snapshot_builder.py"]
    if out:
        args.append(out)
    typer.echo(f"[snapshot] running: {' '.join(args)}")
    try:
        subprocess.run(args, check=True)
        target = out or str(Path.home() / "xsa_min_snapshot.txt")
        typer.echo(f"[snapshot] wrote → {target}")
    except subprocess.CalledProcessError as e:
        typer.echo(f"[snapshot] failed: {e}", err=True)
        raise typer.Exit(1)