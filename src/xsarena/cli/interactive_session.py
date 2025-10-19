"""Interactive cockpit (REPL-lite) using CLIContext."""

import asyncio
import shlex
from pathlib import Path

import requests
import yaml
from rich.console import Console

from ..core.backends import create_backend
from ..core.profiles import load_profiles
from ..core.v2_orchestrator.orchestrator import Orchestrator
from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset
from .context import CLIContext


class InteractiveSession:
    """Interactive session class for the cockpit REPL."""

    def __init__(self, ctx: CLIContext):
        self.ctx = ctx
        self.console = Console()
        self.orchestrator = Orchestrator()
        self.transport = create_backend(ctx.state.backend)

        # Load all available profiles and known styles
        self.profiles = load_profiles()
        self.known_styles = ["narrative", "no_bs", "compressed", "bilingual"]

        # Update commands dict to include prompt commands
        self.commands = {
            "help": self.show_help,
            "capture": self.capture_ids,
            "run.book": self.run_book,
            "continue": self.run_continue,
            "pause": self.pause_job,
            "resume": self.resume_job,
            "next": self.next_job,
            "cancel": self.cancel_job,
            "out.minchars": self.set_output_config,
            "out.passes": self.set_output_config,
            "minchars": self.set_output_config,  # Short alias for /out.minchars
            "passes": self.set_output_config,  # Short alias for /out.passes
            "cont.mode": self.set_continuation_config,
            "cont.anchor": self.set_continuation_config,
            "mode": self.set_continuation_config,  # Short alias for /cont.mode
            "anchor": self.set_continuation_config,  # Short alias for /cont.anchor
            "repeat.warn": self.set_repetition_config,
            "repeat.thresh": self.set_repetition_config,
            "warn": self.set_repetition_config,  # Short alias for /repeat.warn
            "thresh": self.set_repetition_config,  # Short alias for /repeat.thresh
            "config.show": self.show_config,
            "prompt.show": self.cmd_prompt_show,
            "prompt.style": self.cmd_prompt_style,
            "prompt.list": self.cmd_prompt_list,
            "prompt.profile": self.cmd_prompt_profile,
            "prompt.preview": self.cmd_prompt_preview,
            "exit": lambda args: exit(0),
        }

    def _infer_length_preset(self) -> LengthPreset:
        """Infer a LengthPreset from the configured minchars."""
        n = int(getattr(self.ctx.state, "output_min_chars", 4500))
        # Mapped to core.v2_orchestrator.specs presets
        if n >= 6800:
            return LengthPreset.MAX
        if n >= 6200:
            return LengthPreset.VERY_LONG
        if n >= 5800:
            return LengthPreset.LONG
        return LengthPreset.STANDARD

    async def start(self):
        """Start the interactive session."""
        self.console.print("[bold green]XSArena Interactive Cockpit[/bold green]")
        self.console.print("Type /help for available commands or /exit to quit")

        while True:
            try:
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                # Check if it's a command
                if user_input.startswith("/"):
                    await self.handle_command(user_input[1:])
                else:
                    # Treat as regular text input
                    self.console.print(
                        f"[yellow]Unknown command: {user_input}[/yellow]"
                    )
                    self.console.print("Type /help for available commands")

            except KeyboardInterrupt:
                self.console.print("\n[red]Use /exit to quit[/red]")
            except EOFError:
                self.console.print("\n[red]Use /exit to quit[/red]")

    async def handle_command(self, cmd_line: str):
        """Handle a command from the user."""
        parts = cmd_line.split(maxsplit=1)
        command_name = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ""

        try:
            args = shlex.split(args_str)
        except ValueError:
            self.console.print(
                f"[red]Error: Mismatched quotes in arguments for /{command_name}[/red]"
            )
            return

        handler = self.commands.get(command_name)
        if handler:
            # Pass the command name to handlers that need it
            if command_name in [
                "out.minchars",
                "out.passes",
                "cont.mode",
                "cont.anchor",
                "repeat.warn",
                "repeat.thresh",
            ]:
                if asyncio.iscoroutinefunction(handler):
                    await handler(command_name, args)
                else:
                    handler(command_name, args)
            else:
                if asyncio.iscoroutinefunction(handler):
                    await handler(args)
                else:
                    handler(args)
        else:
            self.console.print(f"[yellow]Unknown command: /{command_name}[/yellow]")

    def show_help(self):
        """Show help information."""
        help_text = """
Available commands:
  /capture - Capture session and message IDs from browser
  /run.book "Subject" [--profile ...] - Run a book generation job
  /continue ./books/file.final.md [--until-end] - Continue writing from a file
  /pause <job_id> - Pause a running job
  /resume <job_id> - Resume a paused job
  /next <job_id> "hint" - Send a hint to the next chunk of a job
  /cancel <job_id> - Cancel a running job
  /out.minchars N - Set minimum output characters per chunk
  /minchars N - Set minimum output characters per chunk (alias for /out.minchars)
  /out.passes N - Set number of output push passes
  /passes N - Set number of output push passes (alias for /out.passes)
  /cont.mode anchor|normal - Set continuation mode
  /mode anchor|normal - Set continuation mode (alias for /cont.mode)
  /cont.anchor N - Set anchor length for anchored continuation
  /anchor N - Set anchor length for anchored continuation (alias for /cont.anchor)
  /repeat.warn on|off - Enable/disable repetition warnings
  /warn on|off - Enable/disable repetition warnings (alias for /repeat.warn)
  /repeat.thresh F - Set repetition threshold (0.0-1.0)
  /thresh F - Set repetition threshold (0.0-1.0) (alias for /repeat.thresh)
  /prompt.show - Show active profile, overlays, and extra note
  /prompt.style on|off <name> - Toggle prompt overlays
  /prompt.profile <name> - Apply profile (clears manual overrides)
  /prompt.list - List available profiles and styles
  /prompt.preview <recipe> - Print system_text preview from recipe
  /config.show - Show current configuration
  /exit - Exit the interactive session
        """
        self.console.print(help_text)

    async def capture_ids(self):
        """Capture session and message IDs from browser."""
        self.console.print("Starting ID capture...")
        self.console.print("Please click 'Retry' in your browser to capture IDs")

        # Build URLs from config base_url
        base_url = self.ctx.config.base_url.rstrip("/v1")
        start_capture_url = f"{base_url}/internal/start_id_capture"
        config_url = f"{base_url}/internal/config"

        # Make request to start ID capture (requests is in dependencies)
        try:
            resp = requests.post(start_capture_url, timeout=10)
            if resp.status_code == 200:
                self.console.print(
                    "[green]ID capture started. Please click 'Retry' in browser.[/green]"
                )
            else:
                self.console.print(
                    f"[red]Failed to start ID capture: {resp.status_code}[/red]"
                )
                return
        except Exception as e:
            self.console.print(f"[red]Error starting ID capture: {e}[/red]")
            return

        # Poll for config until IDs appear
        max_attempts = 30  # 30 seconds max wait
        for _ in range(max_attempts):
            try:
                response = requests.get(config_url, timeout=5)
                if response.status_code == 200:
                    config_data = response.json()
                    session_id = config_data.get("bridge", {}).get("session_id")
                    message_id = config_data.get("bridge", {}).get("message_id")

                    if session_id and message_id:
                        self.console.print(f"[green]✓ Session ID: {session_id}[/green]")
                        self.console.print(f"[green]✓ Message ID: {message_id}[/green]")

                        # Show the saved config in .xsarena/config.yml
                        config_path = Path(".xsarena/config.yml")
                        if config_path.exists():
                            with open(config_path, "r", encoding="utf-8") as f:
                                saved_config = yaml.safe_load(f)
                                if saved_config and "bridge" in saved_config:
                                    saved_session_id = saved_config["bridge"].get(
                                        "session_id"
                                    )
                                    saved_message_id = saved_config["bridge"].get(
                                        "message_id"
                                    )
                                    if (
                                        saved_session_id == session_id
                                        and saved_message_id == message_id
                                    ):
                                        self.console.print(
                                            f"[green]✓ IDs saved to {config_path}[/green]"
                                        )
                        return
            except Exception:
                pass  # Continue polling

            await asyncio.sleep(1)  # Use async sleep to avoid blocking the event loop

        self.console.print("[red]Timeout waiting for IDs. Please try again.[/red]")

    async def run_book(self, args: list):
        """Run a book generation job."""
        if not args:
            self.console.print(
                '[red]Usage: /run.book "Subject" [--profile profile_name][/red]'
            )
            return

        subject = args[0].strip("\"'")

        # Parse any additional options
        profile = None
        for i, arg in enumerate(args):
            if arg == "--profile" and i + 1 < len(args):
                profile = args[i + 1]

        # Determine profile and extra note for this run
        active_profile = getattr(self.ctx.state, "active_profile", None)
        run_profile = profile or active_profile
        profile_data = self.profiles.get(run_profile, {})
        extra_note = profile_data.get("extra_note", "")

        # Get active overlays from state
        active_overlays = getattr(
            self.ctx.state, "overlays_active", ["narrative", "no_bs"]
        )

        # Create a valid RunSpecV2; dynamic lengths come from session_state
        run_spec = RunSpecV2(
            subject=subject,
            length=self._infer_length_preset(),
            span=SpanPreset.BOOK,
            overlays=active_overlays,
            extra_note=extra_note,
            profile=run_profile or "",
        )

        try:
            job_id = await self.orchestrator.run_spec(
                run_spec, backend_type=self.ctx.state.backend
            )
            self.console.print(f"[green]✓ Job submitted: {job_id}[/green]")
            self.console.print(f"[green]Subject: {subject}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error running book: {e}[/red]")

    async def run_continue(self, args: list):
        """Continue writing from an existing file."""
        if not args:
            self.console.print(
                "[red]Usage: /continue ./books/file.final.md [--until-end][/red]"
            )
            return

        file_path = args[0].strip("\"'")
        until_end = "--until-end" in args

        if not Path(file_path).exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return

        subject = f"Continue: {Path(file_path).stem}"

        # Get active profile and overlays from state
        active_profile = getattr(self.ctx.state, "active_profile", None)
        active_overlays = getattr(
            self.ctx.state, "overlays_active", ["narrative", "no_bs"]
        )

        # Determine extra note from active profile
        profile_data = self.profiles.get(active_profile, {})
        extra_note = profile_data.get("extra_note", "")

        # Valid RunSpecV2 for continuation
        run_spec = RunSpecV2(
            subject=subject,
            length=self._infer_length_preset(),
            span=SpanPreset.BOOK,
            overlays=active_overlays,
            extra_note=extra_note,
            profile=active_profile or "",
        )

        try:
            job_id = await self.orchestrator.run_continue(
                run_spec, file_path, until_end=until_end
            )
            self.console.print(f"[green]✓ Continue job submitted: {job_id}[/green]")
            self.console.print(f"[green]File: {file_path}[/green]")
            self.console.print(f"[green]Until end: {until_end}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error continuing: {e}[/red]")

    async def pause_job(self, args: list):
        """Pause a running job."""
        if not args:
            self.console.print("[red]Usage: /pause <job_id>[/red]")
            return

        job_id = args[0]
        try:
            await self.orchestrator.job_runner.send_control_message(job_id, "pause")
            self.console.print(f"[green]✓ Job {job_id} paused[/green]")
        except Exception as e:
            self.console.print(f"[red]Error pausing job: {e}[/red]")

    async def resume_job(self, args: list):
        """Resume a paused job."""
        if not args:
            self.console.print("[red]Usage: /resume <job_id>[/red]")
            return

        job_id = args[0]
        try:
            await self.orchestrator.job_runner.send_control_message(job_id, "resume")
            self.console.print(f"[green]✓ Job {job_id} resumed[/green]")
        except Exception as e:
            self.console.print(f"[red]Error resuming job: {e}[/red]")

    async def next_job(self, args: list):
        """Send a hint to the next chunk of a job."""
        if len(args) < 2:
            self.console.print('[red]Usage: /next <job_id> "hint text"[/red]')
            return

        job_id = args[0]
        hint = " ".join(args[1:]).strip("\"'")

        try:
            await self.orchestrator.job_runner.send_control_message(
                job_id, "next", hint
            )
            self.console.print(f"[green]✓ Hint sent to job {job_id}: {hint}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error sending hint: {e}[/red]")

    async def cancel_job(self, args: list):
        """Cancel a running job."""
        if not args:
            self.console.print("[red]Usage: /cancel <job_id>[/red]")
            return

        job_id = args[0]
        try:
            await self.orchestrator.job_runner.send_control_message(job_id, "cancel")
            self.console.print(f"[green]✓ Job {job_id} cancelled[/green]")
        except Exception as e:
            self.console.print(f"[red]Error cancelling job: {e}[/red]")

    async def set_output_config(self, command: str, args: list):
        """Set output configuration."""
        if command == "out.minchars" and args:
            try:
                new_minchars = int(args[0])
                old_minchars = getattr(self.ctx.state, "output_min_chars", 4500)
                self.ctx.state.output_min_chars = new_minchars
                self.ctx.save()
                self.console.print(
                    f"[green]✓ Output min chars set to: {new_minchars}[/green]"
                )

                # Provide context-sensitive tips
                if new_minchars > old_minchars:
                    self.console.print(
                        "[dim]Tip: Higher minchars may hit token limits. Consider 4500-5000 for most models[/dim]"
                    )
                elif new_minchars < 3000:
                    self.console.print(
                        "[dim]Tip: Lower minchars may produce less coherent chunks. Consider 3500+[/dim]"
                    )
            except ValueError:
                self.console.print("[red]Invalid number for minchars[/red]")
        elif command == "out.passes" and args:
            try:
                new_passes = int(args[0])
                old_passes = getattr(self.ctx.state, "output_push_max_passes", 3)
                self.ctx.state.output_push_max_passes = new_passes
                self.ctx.save()
                self.console.print(
                    f"[green]✓ Output passes set to: {new_passes}[/green]"
                )

                # Provide context-sensitive tips
                if new_passes > old_passes and new_passes > 3:
                    self.console.print(
                        "[dim]Tip: Many passes may cause loops. If loops occur, lower repetition_threshold to ~0.32[/dim]"
                    )
                elif new_passes == 0:
                    self.console.print(
                        "[dim]Tip: Zero passes means no micro-extends. Chunks may fall short of minchars[/dim]"
                    )
            except ValueError:
                self.console.print("[red]Invalid number for passes[/red]")
        else:
            self.console.print(
                f"[yellow]Unknown output config command: {command}[/yellow]"
            )

    async def set_continuation_config(self, command: str, args: list):
        """Set continuation configuration."""
        if command == "cont.mode" and args:
            mode = args[0]
            if mode in ["anchor", "normal"]:
                self.ctx.state.continuation_mode = mode
                self.ctx.save()
                self.console.print(f"[green]✓ Continuation mode set to: {mode}[/green]")
                # Provide a tip for this setting
                if mode == "anchor":
                    self.console.print(
                        "[dim]Tip: If loops persist, raise anchor_length to 360–420[/dim]"
                    )
            else:
                self.console.print("[red]Mode must be 'anchor' or 'normal'[/red]")
        elif command == "cont.anchor" and args:
            try:
                new_anchor = int(args[0])
                old_anchor = getattr(self.ctx.state, "anchor_length", 300)
                self.ctx.state.anchor_length = new_anchor
                self.ctx.save()
                self.console.print(
                    f"[green]✓ Anchor length set to: {new_anchor}[/green]"
                )

                # Provide context-sensitive tips
                if new_anchor < 200:
                    self.console.print(
                        "[dim]Tip: Anchor too short may cause continuity issues. Consider 300+[/dim]"
                    )
                elif new_anchor > 500:
                    self.console.print(
                        "[dim]Tip: Very long anchors may reduce creativity. Consider 300-420[/dim]"
                    )
                elif new_anchor > old_anchor:
                    self.console.print(
                        "[dim]Tip: Increasing anchor helps with continuity. If loops persist, also lower repetition_threshold[/dim]"
                    )
                else:
                    self.console.print(
                        "[dim]Tip: If loops persist, consider increasing anchor_length to 360–420[/dim]"
                    )
            except ValueError:
                self.console.print("[red]Invalid number for anchor[/red]")
        else:
            self.console.print(
                f"[yellow]Unknown continuation config command: {command}[/yellow]"
            )

    async def set_repetition_config(self, command: str, args: list):
        """Set repetition configuration."""
        if command == "repeat.warn" and args:
            arg = args[0].lower()
            if arg in ["on", "true", "1"]:
                self.ctx.state.repetition_warn = True
                self.ctx.save()
                self.console.print("[green]✓ Repetition warnings enabled[/green]")
            elif arg in ["off", "false", "0"]:
                self.ctx.state.repetition_warn = False
                self.ctx.save()
                self.console.print("[green]✓ Repetition warnings disabled[/green]")
            else:
                self.console.print("[red]Use 'on' or 'off'[/red]")
        elif command == "repeat.thresh" and args:
            try:
                val = float(args[0])
                old_thresh = getattr(self.ctx.state, "repetition_threshold", 0.35)
                if 0.0 <= val <= 1.0:
                    self.ctx.state.repetition_threshold = val
                    self.ctx.save()
                    self.console.print(
                        f"[green]✓ Repetition threshold set to: {val}[/green]"
                    )

                    # Provide context-sensitive tips
                    if val > old_thresh:
                        self.console.print(
                            "[dim]Tip: Higher threshold allows more similarity. If loops persist, consider lowering to ~0.32[/dim]"
                        )
                    else:
                        self.console.print(
                            "[dim]Tip: Lower threshold prevents more repetitions. If too restrictive, raise to ~0.40[/dim]"
                        )
                else:
                    self.console.print(
                        "[red]Threshold must be between 0.0 and 1.0[/red]"
                    )
            except ValueError:
                self.console.print("[red]Invalid number for threshold[/red]")
        else:
            self.console.print(
                f"[yellow]Unknown repetition config command: {command}[/yellow]"
            )

    def show_config(self):
        """Show current configuration."""
        self.console.print("[bold]Current Configuration:[/bold]")
        self.console.print(f"  Backend: {self.ctx.state.backend}")
        self.console.print(f"  Model: {self.ctx.state.model}")
        self.console.print(f"  Base URL: {self.ctx.config.base_url}")

        # Check if bridge IDs are set
        config_path = Path(".xsarena/config.yml")
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                saved_config = yaml.safe_load(f)
                if saved_config and "bridge" in saved_config:
                    session_id = saved_config["bridge"].get("session_id")
                    message_id = saved_config["bridge"].get("message_id")
                    if session_id and message_id:
                        self.console.print("  Bridge IDs: ✓ Set")
                        self.console.print(f"    Session ID: {session_id}")
                        self.console.print(f"    Message ID: {message_id}")
                    else:
                        self.console.print("  Bridge IDs: ❌ Not set")
                else:
                    self.console.print("  Bridge IDs: ❌ Not set")
        else:
            self.console.print("  Bridge IDs: ❌ Not set")

        self.console.print(
            f"  Output min chars: {getattr(self.ctx.state, 'output_min_chars', 4500)}"
        )
        self.console.print(
            f"  Output passes: {getattr(self.ctx.state, 'output_push_max_passes', 3)}"
        )
        self.console.print(
            f"  Continuation mode: {getattr(self.ctx.state, 'continuation_mode', 'anchor')}"
        )
        self.console.print(
            f"  Anchor length: {getattr(self.ctx.state, 'anchor_length', 300)}"
        )
        self.console.print(
            f"  Repetition threshold: {getattr(self.ctx.state, 'repetition_threshold', 0.35)}"
        )
        self.console.print(
            f"  Repetition warnings: {getattr(self.ctx.state, 'repetition_warn', True)}"
        )

    def cmd_prompt_show(self):
        """Show active profile, overlays, and extra note."""
        self.console.print("[bold]Current Prompt Configuration:[/bold]")

        active_profile = getattr(self.ctx.state, "active_profile", None)
        active_overlays = getattr(
            self.ctx.state, "overlays_active", ["narrative", "no_bs"]
        )

        profile_name = active_profile or "[none]"
        profile_data = self.profiles.get(active_profile, {})
        extra_note = profile_data.get("extra_note", "")

        self.console.print(f"  Active Profile: [green]{profile_name}[/green]")
        self.console.print(
            f"  Active Overlays: [green]{', '.join(sorted(active_overlays))}[/green]"
        )

        if extra_note:
            truncated_note = extra_note.split("\n")[0]
            if len(extra_note) > 80:
                truncated_note = extra_note[:77] + "..."
            self.console.print(
                f"  Profile Extra Note: [yellow]{truncated_note}[/yellow]"
            )
        else:
            self.console.print("  Profile Extra Note: [dim]None[/dim]")

    async def cmd_prompt_style(self, args: list):
        """Toggle prompt overlays."""
        if len(args) < 2:
            self.console.print("[red]Usage: /prompt.style on|off <name>[/red]")
            self.console.print(
                f"[dim]Known styles: {', '.join(self.known_styles)}[/dim]"
            )
            return

        action = args[0].lower()
        style_name = args[1].lower()

        if style_name not in self.known_styles:
            self.console.print(f"[red]Unknown style: {style_name}[/red]")
            self.console.print(
                f"[dim]Known styles: {', '.join(self.known_styles)}[/dim]"
            )
            return

        # Get current overlays from state
        current_overlays = set(
            getattr(self.ctx.state, "overlays_active", ["narrative", "no_bs"])
        )

        if action == "on":
            current_overlays.add(style_name)
            self.console.print(f"[green]✓ Overlay '{style_name}' enabled.[/green]")
        elif action == "off":
            if style_name in current_overlays:
                current_overlays.remove(style_name)
                self.console.print(f"[green]✓ Overlay '{style_name}' disabled.[/green]")
            else:
                self.console.print(
                    f"[yellow]Overlay '{style_name}' was already disabled.[/yellow]"
                )
        else:
            self.console.print("[red]Action must be 'on' or 'off'.[/red]")
            return

        # Save updated overlays to state
        self.ctx.state.overlays_active = list(current_overlays)
        self.ctx.save()

    def cmd_prompt_list(self):
        """List available profiles and styles."""
        self.console.print("[bold]Available Profiles:[/bold]")
        for name in sorted(self.profiles.keys()):
            self.console.print(f"  - [cyan]{name}[/cyan]")

        self.console.print("\n[bold]Known Styles (Overlays):[/bold]")
        active_overlays = set(
            getattr(self.ctx.state, "overlays_active", ["narrative", "no_bs"])
        )
        for name in sorted(self.known_styles):
            status = (
                "[green]ON[/green]" if name in active_overlays else "[dim]OFF[/dim]"
            )
            self.console.print(f"  - {name} ({status})")

    async def cmd_prompt_profile(self, args: list):
        """Apply overlays/extra from profile; clear manual overrides precedence."""
        if not args:
            self.console.print("[red]Usage: /prompt.profile <name>[/red]")
            self.cmd_prompt_list()
            return

        profile_name = args[0]
        if profile_name not in self.profiles:
            self.console.print(f"[red]Unknown profile: {profile_name}[/red]")
            self.cmd_prompt_list()
            return

        profile_data = self.profiles[profile_name]

        # Apply profile settings to state
        self.ctx.state.active_profile = profile_name

        # Overlays from profile (if present) or default to profile's overlays
        new_overlays = set(profile_data.get("overlays", ["narrative", "no_bs"]))
        self.ctx.state.overlays_active = list(new_overlays)
        self.ctx.save()

        self.console.print(f"[green]✓ Profile set to '{profile_name}'.[/green]")
        self.cmd_prompt_show()

    async def cmd_prompt_preview(self, args: list):
        """Print system_text preview from recipe (no backend call)."""
        if not args:
            self.console.print("[red]Usage: /prompt.preview <recipe_file>[/red]")
            return

        file_path = Path(args[0])
        if not file_path.exists():
            self.console.print(f"[red]Recipe file not found: {file_path}[/red]")
            return

        try:
            import yaml

            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            self.console.print(f"[red]Failed to load recipe: {e}[/red]")
            return

        system_text = (data.get("system_text") or "").strip()
        if not system_text:
            self.console.print("[yellow]Recipe contains no system_text.[/yellow]")
            return

        self.console.print(f"[bold]System Text Preview from {file_path}:[/bold]")
        self.console.print(system_text)
        self.console.print(f"[dim]Length: {len(system_text)} characters[/dim]")


async def start_interactive_session(ctx: CLIContext):
    """Start the interactive session with the given context."""
    session = InteractiveSession(ctx)
    await session.start()
