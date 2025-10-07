#!/usr/bin/env python3

import typer

from ..utils.snapshot_v2 import create_snapshot, diff_snapshots

app = typer.Typer(help="Snapshot utilities (create, diff, share)")


@app.command("run")
def snapshot_run(
    project_root: str = typer.Option(".", "--project-root", "-r", help="Project root directory"),
    output: str = typer.Option("snapshot.txt", "--output", "-o", help="Output file name"),
    max_file_size: int = typer.Option(10000, "--max-file-size", "-m", help="Max file size to include (bytes)"),
    chunk: bool = typer.Option(False, "--chunk", "-c", help="Split output into chunks"),
    chunk_size: int = typer.Option(100000, "--size", "-s", help="Chunk size in bytes"),
    include_env: bool = typer.Option(True, "--env/--no-env", help="Include environment info"),
    include_git: bool = typer.Option(True, "--git/--no-git", help="Include git info"),
    include_pip: bool = typer.Option(True, "--pip/--no-pip", help="Include pip freeze"),
    redact: bool = typer.Option(True, "--redact/--no-redact", help="Redact sensitive info"),
    tar: bool = typer.Option(False, "--tar", help="Create tarball with sha256"),
):
    """Create a project snapshot with enhanced features."""
    create_snapshot(
        project_root=project_root,
        output_file=output,
        max_file_size=max_file_size,
        include_tree=True,
        include_files=True,
        include_git=include_git,
        include_pip=include_pip,
        include_env=include_env,
        chunk=chunk,
        chunk_size=chunk_size,
        redact=redact,
        tar=tar,
    )


@app.command("diff")
def snapshot_diff(
    snapshot_a: str = typer.Argument(..., help="First snapshot file"),
    snapshot_b: str = typer.Argument(..., help="Second snapshot file"),
):
    """Create a diff between two snapshot files."""
    diff_snapshots(snapshot_a, snapshot_b)


@app.command("share")
def snapshot_share(
    snapshot_file: str = typer.Argument(..., help="Snapshot file to share"),
    service: str = typer.Option("rs", "--paste", "-p", help="Paste service: rs (paste.rs) or gist (GitHub Gist)"),
):
    """Share a snapshot via paste service (placeholder implementation)."""
    typer.echo(f"[snapshot] Sharing {snapshot_file} via {service} (stub implementation)")
    # This would be implemented with actual paste/gist API calls
