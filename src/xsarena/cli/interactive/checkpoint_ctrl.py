"""Checkpoint controllers for interactive mode."""

import logging
from pathlib import Path

from rich.console import Console

from ...core.state import SessionState
from ..context import CLIContext

logger = logging.getLogger(__name__)


class CheckpointController:
    """Controller for managing checkpoints in interactive mode."""

    def __init__(self, console: Console, ctx: CLIContext):
        self.console = console
        self.ctx = ctx

    def cmd_ckpt_save(self, args):
        """Save current session checkpoint."""
        path = args[0] if args else None
        if path is None:
            import time

            path = f"checkpoint_{int(time.time())}.json"

        # Ensure checkpoints directory exists
        checkpoints_dir = Path(".xsarena/checkpoints")
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_path = checkpoints_dir / path
        try:
            self.ctx.state.save_to_file(checkpoint_path)
            self.console.print(
                f"[green]✓ Checkpoint saved to {checkpoint_path}[/green]"
            )
        except Exception as e:
            self.console.print(f"[red]Error saving checkpoint: {e}[/red]")

    def cmd_ckpt_load(self, args):
        """Load session from checkpoint."""
        if not args:
            self.console.print("[red]Error: Please provide a checkpoint path[/red]")
            return

        path = args[0]
        checkpoint_path = Path(path)

        if not checkpoint_path.exists():
            # Check in default checkpoints directory
            checkpoint_path = Path(".xsarena/checkpoints") / path
            if not checkpoint_path.exists():
                self.console.print(f"[red]Error: Checkpoint {path} not found[/red]")
                return

        try:
            # Load session state from file
            session_state = SessionState.load_from_file(checkpoint_path)
            self.ctx.state = session_state
            self.console.print(
                f"[green]✓ Checkpoint loaded from {checkpoint_path}[/green]"
            )
        except Exception as e:
            self.console.print(f"[red]Error loading checkpoint: {e}[/red]")
