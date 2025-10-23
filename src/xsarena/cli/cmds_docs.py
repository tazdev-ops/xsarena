"""CLI commands for documentation generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(help="Documentation generation commands")


@app.command("gen-help")
def gen_help():
    """Generate help documentation by dynamically discovering the command tree."""

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

    # Dynamically discover top-level commands from the registry
    # Top-level groups as per the registry
    top_level_groups = [
        "run",
        "interactive",
        "settings",
        "report",
        "preview",
        "publish",
        "pipeline",
        "project",
        "metrics",
        "debug",
        "adapt",
        "checklist",
        "upgrade",
        "macros",
        "playground",
        "roles",
        "overlays",
        "json",
        "controls",
        "docs",
        "endpoints",
        "audio",
        "bilingual",
        "booster",
        "coach",
        "coder",
        "joy",
        "list",
        "modes",
        "people",
        "policy",
        "workshop",
    ]

    # Ops subcommands
    ops_subcommands = [
        "service",
        "jobs",
        "health",
        "snapshot",
        "config",
        "handoff",
        "orders",
    ]

    # Generate help for top-level commands
    for cmd in top_level_groups:
        # Skip hidden commands that might not have help
        if cmd in [
            "audio",
            "bilingual",
            "coder",
            "joy",
            "modes",
            "people",
            "policy",
            "workshop",
        ]:
            continue

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

    # Generate help for ops subcommands
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
