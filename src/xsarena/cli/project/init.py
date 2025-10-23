"""Initialization commands for XSArena project management."""

import os

import typer

from ..cmds_directives import directives_index as directives_index_func

app = typer.Typer(help="Initialization commands")


@app.command("init")
def project_init_cmd(
    dir_path: str = typer.Option(
        ".", "--dir", help="Directory to initialize (default: current directory)"
    )
):
    """Initialize XSArena project structure (.xsarena/, books/, etc.) and index directives if present."""
    root_dir = os.path.abspath(dir_path)
    xsarena_dir = os.path.join(root_dir, ".xsarena")

    created_paths = []

    # Create .xsarena directory and subdirectories
    os.makedirs(xsarena_dir, exist_ok=True)
    created_paths.append(xsarena_dir)

    finals_dir = os.path.join(root_dir, "books", "finals")
    os.makedirs(finals_dir, exist_ok=True)
    created_paths.append(finals_dir)

    outlines_dir = os.path.join(root_dir, "books", "outlines")
    os.makedirs(outlines_dir, exist_ok=True)
    created_paths.append(outlines_dir)

    review_dir = os.path.join(root_dir, "review")
    os.makedirs(review_dir, exist_ok=True)
    created_paths.append(review_dir)

    # Create minimal .xsarena/config.yml if it doesn't exist
    config_path = os.path.join(xsarena_dir, "config.yml")
    if not os.path.exists(config_path):
        minimal_config = """# XSArena Configuration
# This file contains user/project defaults for XSArena

# Bridge configuration (for connecting to LMArena through browser)
# bridge:
#   session_id: "your-session-id"
#   message_id: "your-message-id"
#   tavern_mode_enabled: false
#   bypass_enabled: false
#   enable_idle_restart: true
#   stream_response_timeout_seconds: 300

# Default model and backend settings
# model: "default"
# backend: "bridge"
# window_size: 100

# Output and continuation settings
# output_min_chars: 50
# output_push_max_passes: 3
# continuation_mode: "auto"
# anchor_length: 200
# repetition_threshold: 0.8
# repetition_warn: true
# smart_min_enabled: true
# outline_first_enabled: false
# semantic_anchor_enabled: true
"""
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(minimal_config)
        created_paths.append(config_path)

    # Run directives index if directives/ exists
    directives_dir = os.path.join(root_dir, "directives")
    if os.path.exists(directives_dir):
        typer.echo("Indexing directives...")
        try:
            # Call the index command function directly
            directives_index_func(out="directives/manifest.yml")  # Use default output
            created_paths.append("directives indexed")
        except Exception as e:
            typer.echo(f"Warning: Could not index directives: {e}")

    typer.echo("XSArena project initialized successfully!")
    typer.echo("Created paths:")
    for path in created_paths:
        typer.echo(f"  - {path}")

    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("  1. Start the bridge: xsarena ops service start-bridge-v2")
    typer.echo("  2. Install the userscript: xsarena_bridge.user.js")
    typer.echo("  3. Begin capturing session IDs: /capture in interactive mode")
    typer.echo("  4. Start authoring: xsarena interactive or xsarena run")
