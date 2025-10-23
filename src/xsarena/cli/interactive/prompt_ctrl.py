"""Prompt controllers for interactive mode."""

import logging
from typing import Any, Dict, List

from rich.console import Console

from ..context import CLIContext

logger = logging.getLogger(__name__)


class PromptController:
    """Controller for managing prompts in interactive mode."""

    def __init__(
        self,
        console: Console,
        ctx: CLIContext,
        profiles: Dict[str, Any],
        known_styles: List[str],
    ):
        self.console = console
        self.ctx = ctx
        self.profiles = profiles
        self.known_styles = known_styles

    def cmd_prompt_show(self, args=None):
        """Show current prompt settings."""
        active_profile = getattr(self.ctx.state, "active_profile", "None")
        active_overlays = getattr(
            self.ctx.state, "overlays_active", ["narrative", "no_bs"]
        )
        extra_note = getattr(self.ctx.state, "extra_note", "")

        self.console.print("[bold]Current Prompt Settings:[/bold]")
        self.console.print(f"  Profile: {active_profile}")
        self.console.print(f"  Overlays: {active_overlays}")
        self.console.print(f"  Extra Note: {extra_note}")

    def cmd_prompt_style(self, args):
        """Enable or disable a specific prompt style."""
        if len(args) < 2:
            self.console.print("[red]Usage: /prompt.style on|off <style_name>[/red]")
            return

        action = args[0].lower()
        style_name = args[1].lower()

        if style_name not in self.known_styles:
            self.console.print(
                f"[red]Unknown style: {style_name}. Available: {self.known_styles}[/red]"
            )
            return

        if action not in ["on", "off"]:
            self.console.print("[red]Action must be 'on' or 'off'[/red]")
            return

        # Get current active overlays
        active_overlays = getattr(
            self.ctx.state, "overlays_active", ["narrative", "no_bs"]
        )

        if action == "on" and style_name not in active_overlays:
            active_overlays.append(style_name)
        elif action == "off" and style_name in active_overlays:
            active_overlays.remove(style_name)

        # Update the state
        self.ctx.state.overlays_active = active_overlays
        self.console.print(
            f"[green]✓ Style '{style_name}' {'enabled' if action == 'on' else 'disabled'}[/green]"
        )

    def cmd_prompt_list(self, args=None):
        """List available prompts."""
        self.console.print("[bold]Available Profiles:[/bold]")
        for profile_name in self.profiles:
            self.console.print(f"  - {profile_name}")

        self.console.print("[bold]Known Styles:[/bold]")
        for style in self.known_styles:
            self.console.print(f"  - {style}")

    def cmd_prompt_profile(self, args):
        """Switch to a specific prompt profile."""
        if not args:
            self.console.print("[red]Usage: /prompt.profile <profile_name>[/red]")
            return

        profile_name = args[0]
        if profile_name not in self.profiles:
            self.console.print(
                f"[red]Unknown profile: {profile_name}. Available: {list(self.profiles.keys())}[/red]"
            )
            return

        profile_data = self.profiles[profile_name]

        # Apply profile settings
        self.ctx.state.active_profile = profile_name
        self.ctx.state.overlays_active = profile_data.get(
            "overlays", ["narrative", "no_bs"]
        )
        self.ctx.state.extra_note = profile_data.get("extra_note") or profile_data.get(
            "extra", ""
        )

        self.console.print(f"[green]✓ Profile '{profile_name}' applied[/green]")

    def cmd_prompt_preview(self, args):
        """Preview how content will be formatted with current prompt settings."""
        if not args:
            self.console.print("[red]Usage: /prompt.preview <recipe>[/red]")
            return

        recipe_text = " ".join(args)
        # For now, just show the current settings that would be applied
        self.console.print("[bold]Preview of current prompt settings:[/bold]")
        self.console.print(f"  Recipe: {recipe_text}")
        self.console.print(
            f"  Active profile: {getattr(self.ctx.state, 'active_profile', 'None')}"
        )
        self.console.print(
            f"  Active overlays: {getattr(self.ctx.state, 'overlays_active', ['narrative', 'no_bs'])}"
        )
        self.console.print(f"  Extra note: {getattr(self.ctx.state, 'extra_note', '')}")
