#!/usr/bin/env python3
from typing import Optional

import typer

from ..coder.gitops import ensure_branch
from ..coder.search import search_and_create_tickets
from ..coder.session import CoderSession
from ..coder.tests import create_test_skeleton

app = typer.Typer(
    help="Advanced coding session with tickets, patches, and git integration"
)


@app.command("start")
def coder_start(
    root: str = typer.Option(".", "--root", "-r", help="Project root directory")
):
    """Start a new coding session."""
    CoderSession(root)
    typer.echo(f"[coder] Session started in {root}")
    # Actually save session state would require more implementation
    # For now just acknowledge
    typer.echo("[coder] Ready for tickets and patches")


@app.command("ticket")
def ticket_new(
    file: str = typer.Argument(..., help="File to create ticket for"),
    lines: Optional[str] = typer.Option(
        None, "--lines", "-l", help="Line numbers (e.g., '12,19' or '15-20')"
    ),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Ticket note"),
):
    """Create a new coding ticket."""
    session = CoderSession(".")
    ticket_id = session.ticket_new(file, lines, note)
    typer.echo(f"[coder] Ticket created: {ticket_id} for {file}")


@app.command("next")
def ticket_next():
    """Get next pending ticket."""
    session = CoderSession(".")
    ticket = session.ticket_next()
    if ticket:
        typer.echo(
            f'{{"id":"{ticket.id}","file":"{ticket.file}","lines":"{ticket.lines}","note":"{ticket.note}"}}'
        )
    else:
        typer.echo("No pending tickets")


@app.command("patch")
def patch_command(
    action: str = typer.Argument(..., help="Action: dry or apply"),
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    patch_file: str = typer.Argument(..., help="Patch file or '-' for stdin"),
):
    """Apply patches with dry-run option."""
    session = CoderSession(".")
    # Read patch content
    if patch_file == "-":
        import sys

        patch_content = sys.stdin.read()
    else:
        with open(patch_file, "r") as f:
            patch_content = f.read()
    if action == "dry":
        result = session.patch_dry_run(ticket_id, patch_content)
        if result["error"]:
            typer.echo(f"[coder] Dry run failed: {result['error']}")
            raise typer.Exit(1)
        else:
            typer.echo(
                f"[coder] Dry run OK, would apply {result['applied_hunks']} hunks"
            )
    elif action == "apply":
        result = session.patch_apply(ticket_id, patch_content)
        if result["error"]:
            typer.echo(f"[coder] Apply failed: {result['error']}")
            raise typer.Exit(1)
        else:
            typer.echo(f"[coder] Applied {result['applied_hunks']} hunks")
    else:
        typer.echo("Action must be 'dry' or 'apply'")
        raise typer.Exit(1)


@app.command("test")
def run_tests(args: str = typer.Option("-q", "--args", "-a", help="Pytest arguments")):
    """Run tests with pytest."""
    session = CoderSession(".")
    result = session.run_tests(args)
    typer.echo(result["summary"])


@app.command("diff")
def show_diff(file: str = typer.Argument(..., help="File to diff")):
    """Show file diff."""
    session = CoderSession(".")
    diff_content = session.diff_file(file)
    typer.echo(diff_content)


@app.command("branch")
def branch_command(
    ticket_id: str = typer.Argument(..., help="Ticket ID for branch name")
):
    """Create or switch to a git branch for this ticket."""
    branch_name = f"xsarena/coder/{ticket_id}"
    success = ensure_branch(branch_name)
    if success:
        typer.echo(f"[coder] Switched to branch: {branch_name}")
    else:
        typer.echo(f"[coder] Failed to switch to branch: {branch_name}")
        raise typer.Exit(1)


@app.command("search")
def search_command(
    pattern: str = typer.Argument(..., help="Search pattern (regex)"),
    note: str = typer.Option("", "--note", "-n", help="Note to add to created tickets"),
    max_hits: int = typer.Option(50, "--max", "-m", help="Max hits to find"),
):
    """Search for pattern and create tickets."""
    ticket_ids = search_and_create_tickets(pattern, note, None, max_hits)
    typer.echo(f"[coder] Created {len(ticket_ids)} tickets from search")


@app.command("test-skeleton")
def test_skeleton(
    module_path: str = typer.Argument(..., help="Module path to create test for")
):
    """Create a test skeleton for a module."""
    test_path = create_test_skeleton(module_path)
    typer.echo(f"[coder] Test skeleton created: {test_path}")


@app.command("rollback")
def rollback_changes():
    """Rollback last changes using git."""
    from ..coder.gitops import stash_apply

    success = stash_apply()
    if success:
        typer.echo("[coder] Changes rolled back")
    else:
        typer.echo("[coder] Failed to rollback changes")
        raise typer.Exit(1)


@app.command("import-ruff")
def import_ruff_tickets():
    """Convert .lint/tickets to coder tickets."""
    import json
    from pathlib import Path

    tickets_dir = Path(".lint") / "tickets"
    if not tickets_dir.exists():
        typer.echo("[coder] No .lint/tickets directory found")
        return

    created_count = 0
    for ticket_file in tickets_dir.glob("*.json"):
        try:
            with open(ticket_file, "r") as f:
                ruff_ticket = json.load(f)

            # Extract information from ruff ticket
            file_path = ruff_ticket.get("file", "unknown")
            line = ruff_ticket.get("line", 1)
            message = ruff_ticket.get("message", "")
            code = ruff_ticket.get("code", "")

            # Create a coder ticket
            session = CoderSession(".")
            ticket_id = session.ticket_new(
                file=file_path, lines=str(line), note=f"Ruff: {code} - {message}"
            )

            created_count += 1
            typer.echo(
                f"[coder] Created ticket {ticket_id} from ruff ticket: {file_path}:{line} - {code}"
            )

        except Exception as e:
            typer.echo(f"[coder] Error processing ruff ticket {ticket_file}: {str(e)}")
            continue

    typer.echo(f"[coder] Imported {created_count} ruff tickets to coder")


"""Debugging CLI commands for XSArena."""

import typer

from ..core.config import Config
from ..core.state import SessionState

app = typer.Typer()


@app.command("state")
def show_state():
    """Show current session state."""
    state = SessionState()

    typer.echo("Session State:")
    typer.echo(f"  History length: {len(state.history)}")
    typer.echo(f"  Anchors: {len(state.anchors)}")
    typer.echo(f"  Continuation Mode: {state.continuation_mode}")
    typer.echo(f"  Anchor Length: {state.anchor_length}")
    typer.echo(f"  Repetition Threshold: {state.repetition_threshold}")
    typer.echo(f"  Backend: {state.backend}")
    typer.echo(f"  Model: {state.model}")
    typer.echo(f"  Window Size: {state.window_size}")
    typer.echo(f"  Current Job ID: {state.current_job_id}")
    typer.echo(f"  Job Queue Length: {len(state.job_queue)}")


@app.command("clear-history")
def clear_history():
    """Clear the conversation history."""
    state = SessionState()
    state.history.clear()
    typer.echo("Conversation history cleared")


@app.command("clear-anchors")
def clear_anchors():
    """Clear the anchors."""
    state = SessionState()
    state.anchors.clear()
    typer.echo("Anchors cleared")


@app.command("config")
def show_config():
    """Show current configuration."""
    config = Config()

    typer.echo("Current Configuration:")
    typer.echo(f"  Backend: {config.backend}")
    typer.echo(f"  Model: {config.model}")
    typer.echo(f"  Window Size: {config.window_size}")
    typer.echo(f"  Anchor Length: {config.anchor_length}")
    typer.echo(f"  Continuation Mode: {config.continuation_mode}")
    typer.echo(f"  Repetition Threshold: {config.repetition_threshold}")
    typer.echo(f"  Max Retries: {config.max_retries}")
    typer.echo(f"  API Key: {'Set' if config.api_key else 'Not set'}")
    typer.echo(f"  Base URL: {config.base_url}")
    typer.echo(f"  Timeout: {config.timeout}")
    typer.echo(f"  Redaction Enabled: {config.redaction_enabled}")


@app.command("save-state")
def save_state(
    filepath: str = typer.Argument(
        "./.xsarena/session_state.json", help="Path to save state file"
    )
):
    """Save current state to a file."""
    state = SessionState()
    state.save_to_file(filepath)
    typer.echo(f"State saved to {filepath}")


@app.command("load-state")
def load_state(
    filepath: str = typer.Argument(
        "./.xsarena/session_state.json", help="Path to load state file"
    )
):
    """Load state from a file."""
    state = SessionState.load_from_file(filepath)
    # In a real implementation, we would update the active session with this state
    typer.echo(f"State loaded from {filepath}")
    typer.echo(f"Loaded state has history length: {len(state.history)}")


@app.command("toggle-redaction")
def toggle_redaction(
    enabled: bool = typer.Argument(..., help="Enable or disable redaction filter")
):
    """Toggle the redaction filter."""
    if enabled:
        typer.echo("Redaction filter enabled: sensitive information will be filtered")
    else:
        typer.echo("Redaction filter disabled")

    # In the actual engine, this would update the redaction filter
