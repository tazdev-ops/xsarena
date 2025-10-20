"""CLI commands for documentation generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(help="Documentation generation commands")


@app.command("gen-help")
def gen_help():
    """Generate help documentation by running xsarena --help and subcommand --help."""

    # Create docs directory if it doesn't exist
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    # Get the main help
    try:
        result = subprocess.run(
            [sys.executable, "-m", "xsarena", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        (docs_dir / "_help_root.txt").write_text(result.stdout)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error getting root help: {e}")

    # Get help for common subcommands
    # We'll get help for subcommands by trying to call them with --help
    subcommands = [
        "run",
        "interactive",
        "control",
        "report",
        "profiles",
        "config",
        "backend",
        "preview",
        "ingest",
        "lossless",
        "style",
        "study",
        "policy",
        "chad",
        "bilingual",
        "booster",
        "tools",
        "coach",
        "joy",
        "agent",
        "coder",
        "pipeline",
        "project",
        "metrics",
        "debug",
        "adapt",
        "boot",
        "checklist",
        "upgrade",
        "fix",
        "clean",
        "mode",
        "macros",
        "playground",
        "people",
        "roles",
        "overlays",
        "json",
    ]

    for cmd in subcommands:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "xsarena", cmd, "--help"],
                capture_output=True,
                text=True,
                check=True,
            )
            (docs_dir / f"_help_{cmd.replace('-', '_')}.txt").write_text(result.stdout)
        except subprocess.CalledProcessError:
            # Some commands might not have --help or might require arguments
            continue

    # Get help for ops subcommands
    ops_subcommands = [
        "jobs",
        "service",
        "snapshot",
        "health",  # replacing deprecated "doctor"
    ]

    for cmd in ops_subcommands:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "xsarena", "ops", cmd, "--help"],
                capture_output=True,
                text=True,
                check=True,
            )
            (docs_dir / f"_help_ops_{cmd.replace('-', '_')}.txt").write_text(
                result.stdout
            )
        except subprocess.CalledProcessError:
            # Some commands might not have --help or might require arguments
            continue

    typer.echo(f"Generated help documentation in {docs_dir}/ directory")
