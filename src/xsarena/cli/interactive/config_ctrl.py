"""Configuration controllers for interactive mode."""

import logging

from rich.console import Console

from ..context import CLIContext

logger = logging.getLogger(__name__)


class ConfigController:
    """Controller for managing configuration in interactive mode."""

    def __init__(self, console: Console, ctx: CLIContext):
        self.console = console
        self.ctx = ctx

    def set_output_config(self, cmd_name: str, args):
        """Set output configuration parameters."""
        if not args:
            self.console.print(
                f"[red]Error: Please provide a value for {cmd_name}[/red]"
            )
            return

        try:
            if cmd_name in ["out.minchars", "minchars"]:
                value = int(args[0])
                self.ctx.state.output_min_chars = value
                self.console.print(f"[green]✓ Min chars set to {value}[/green]")
            elif cmd_name in ["out.passes", "passes"]:
                value = int(args[0])
                self.ctx.state.output_push_max_passes = value
                self.console.print(f"[green]✓ Passes set to {value}[/green]")
            else:
                self.console.print(
                    f"[red]Error: Unknown output config command {cmd_name}[/red]"
                )
        except ValueError:
            self.console.print(
                f"[red]Error: Invalid value '{args[0]}', must be a number[/red]"
            )

    def set_continuation_config(self, cmd_name: str, args):
        """Set continuation configuration parameters."""
        if not args:
            self.console.print(
                f"[red]Error: Please provide a value for {cmd_name}[/red]"
            )
            return

        try:
            if cmd_name in ["cont.mode", "mode"]:
                value = args[0]
                if value in ["anchor", "normal", "semantic"]:
                    if value == "semantic":
                        self.ctx.state.continuation_mode = "semantic-anchor"
                        self.ctx.state.semantic_anchor_enabled = True
                    else:
                        self.ctx.state.continuation_mode = value
                        self.ctx.state.semantic_anchor_enabled = False
                    self.console.print(
                        f"[green]✓ Continuation mode set to {value}[/green]"
                    )
                else:
                    self.console.print(
                        "[red]Error: Mode must be 'anchor', 'normal', or 'semantic'[/red]"
                    )
            elif cmd_name in ["cont.anchor", "anchor"]:
                value = int(args[0])
                self.ctx.state.anchor_length = value
                self.console.print(f"[green]✓ Anchor length set to {value}[/green]")
            else:
                self.console.print(
                    f"[red]Error: Unknown continuation config command {cmd_name}[/red]"
                )
        except ValueError:
            self.console.print(
                f"[red]Error: Invalid value '{args[0]}', must be a number for anchor[/red]"
            )

    def set_repetition_config(self, cmd_name: str, args):
        """Set repetition configuration parameters."""
        if not args:
            self.console.print(
                f"[red]Error: Please provide a value for {cmd_name}[/red]"
            )
            return

        try:
            if cmd_name in ["repeat.warn", "warn"]:
                value = args[0].lower()
                if value in ["on", "true", "1"]:
                    self.ctx.state.repetition_warn = True
                    self.console.print("[green]✓ Repetition warnings enabled[/green]")
                elif value in ["off", "false", "0"]:
                    self.ctx.state.repetition_warn = False
                    self.console.print("[green]✓ Repetition warnings disabled[/green]")
                else:
                    self.console.print("[red]Error: Value must be 'on' or 'off'[/red]")
            elif cmd_name in ["repeat.thresh", "thresh"]:
                value = float(args[0])
                if 0.0 <= value <= 1.0:
                    self.ctx.state.repetition_threshold = value
                    self.console.print(
                        f"[green]✓ Repetition threshold set to {value}[/green]"
                    )
                else:
                    self.console.print(
                        "[red]Error: Threshold must be between 0.0 and 1.0[/red]"
                    )
            else:
                self.console.print(
                    f"[red]Error: Unknown repetition config command {cmd_name}[/red]"
                )
        except ValueError:
            self.console.print(
                f"[red]Error: Invalid value '{args[0]}', must be a number for threshold[/red]"
            )

    def show_config(self, args=None):
        """Show current configuration."""
        state = self.ctx.state
        self.console.print("[bold]Current Configuration:[/bold]")
        self.console.print(
            f"  Output min chars: {getattr(state, 'output_min_chars', 4500)}"
        )
        self.console.print(
            f"  Output passes: {getattr(state, 'output_push_max_passes', 1)}"
        )
        self.console.print(
            f"  Continuation mode: {getattr(state, 'continuation_mode', 'anchor')}"
        )
        self.console.print(f"  Anchor length: {getattr(state, 'anchor_length', 360)}")
        self.console.print(
            f"  Repetition warn: {getattr(state, 'repetition_warn', True)}"
        )
        self.console.print(
            f"  Repetition threshold: {getattr(state, 'repetition_threshold', 0.35)}"
        )
        self.console.print(
            f"  Active overlays: {getattr(state, 'overlays_active', ['narrative', 'no_bs'])}"
        )
        self.console.print(
            f"  Active profile: {getattr(state, 'active_profile', 'None')}"
        )
