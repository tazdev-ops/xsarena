"""Debugging CLI commands for LMASudio."""
import typer
from typing import Optional
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
def save_state(filepath: str = typer.Argument("./.lmastudio/session_state.json", help="Path to save state file")):
    """Save current state to a file."""
    state = SessionState()
    state.save_to_file(filepath)
    typer.echo(f"State saved to {filepath}")

@app.command("load-state")
def load_state(filepath: str = typer.Argument("./.lmastudio/session_state.json", help="Path to load state file")):
    """Load state from a file."""
    state = SessionState.load_from_file(filepath)
    # In a real implementation, we would update the active session with this state
    typer.echo(f"State loaded from {filepath}")
    typer.echo(f"Loaded state has history length: {len(state.history)}")

@app.command("toggle-redaction")
def toggle_redaction(enabled: bool = typer.Argument(..., help="Enable or disable redaction filter")):
    """Toggle the redaction filter."""
    if enabled:
        typer.echo("Redaction filter enabled: sensitive information will be filtered")
    else:
        typer.echo("Redaction filter disabled")
    
    # In the actual engine, this would update the redaction filter