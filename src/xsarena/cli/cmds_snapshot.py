import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(
    help="Generate an intelligent, minimal, and configurable project snapshot."
)


@app.command("write")
def snapshot_write(
    out: str = typer.Option(
        None, "--out", "-o", help="Output file path. Defaults to xsa_min_snapshot.txt."
    ),
    with_git: bool = typer.Option(
        False, "--with-git", help="Include git status information."
    ),
    with_jobs: bool = typer.Option(
        False, "--with-jobs", help="Include a summary of recent jobs."
    ),
    with_manifest: bool = typer.Option(
        False, "--with-manifest", help="Include a code manifest of src/."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be included without creating the file.",
    ),
):
    """
    Generate a snapshot using the advanced snapshot builder.

    This tool is configurable via .snapshotinclude and .snapshotignore files.
    """
    script_path = "tools/snapshot_builder.py"
    if not Path(script_path).exists():
        typer.echo(f"Error: Snapshot builder not found at '{script_path}'", err=True)
        raise typer.Exit(1)

    args = [sys.executable, script_path]
    if out:
        args.append(out)
    if with_git:
        args.append("--with-git")
    if with_jobs:
        args.append("--with-jobs")
    if with_manifest:
        args.append("--with-manifest")
    if dry_run:
        args.append("--dry-run")

    typer.echo(f"[snapshot] running: {' '.join(args)}")
    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"[snapshot] failed: {e}", err=True)
        raise typer.Exit(1)
