"""Interactive cockpit (REPL-lite) using CLIContext."""

import asyncio
import shlex
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
import yaml
from rich.console import Console

from ..core.backends import create_backend
from ..core.profiles import load_profiles
from ..core.v2_orchestrator.orchestrator import Orchestrator
from ..core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset
from .context import CLIContext
from .dispatch import dispatch_command
from .interactive.checkpoint_ctrl import CheckpointController
from .interactive.config_ctrl import ConfigController
from .interactive.jobs_ctrl import JobsController
from .interactive.prompt_ctrl import PromptController


class InteractiveSession:
    """Interactive session class for the cockpit REPL."""

    def __init__(self, ctx: CLIContext):
        self.ctx = ctx
        self.console = Console()
        self.orchestrator = Orchestrator()
        self.transport = create_backend(ctx.state.backend)

        # Busy guard to prevent overlapping command runs
        self._command_busy = False
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Load all available profiles and known styles
        self.profiles = load_profiles()
        self.known_styles = ["narrative", "no_bs", "compressed", "bilingual"]

        # Initialize controllers
        self.prompt_controller = PromptController(
            self.console, self.ctx, self.profiles, self.known_styles
        )
        self.jobs_controller = JobsController(self.console, self.ctx, self.orchestrator)
        self.config_controller = ConfigController(self.console, self.ctx)
        self.checkpoint_controller = CheckpointController(self.console, self.ctx)

        # Update commands dict to include prompt commands
        self.commands = {
            "help": self.show_help,
            "capture": self.capture_ids,
            "run.book": self.run_book,
            "continue": self.run_continue,
            "pause": self.jobs_controller.pause_job,
            "resume": self.jobs_controller.resume_job,
            "next": self.jobs_controller.next_job,
            "cancel": self.jobs_controller.cancel_job,
            "out.minchars": self.config_controller.set_output_config,
            "out.passes": self.config_controller.set_output_config,
            "minchars": self.config_controller.set_output_config,  # Short alias for /out.minchars
            "passes": self.config_controller.set_output_config,  # Short alias for /out.passes
            "cont.mode": self.config_controller.set_continuation_config,
            "cont.anchor": self.config_controller.set_continuation_config,
            "mode": self.config_controller.set_continuation_config,  # Short alias for /cont.mode
            "anchor": self.config_controller.set_continuation_config,  # Short alias for /cont.anchor
            "repeat.warn": self.config_controller.set_repetition_config,
            "repeat.thresh": self.config_controller.set_repetition_config,
            "warn": self.config_controller.set_repetition_config,  # Short alias for /repeat.warn
            "thresh": self.config_controller.set_repetition_config,  # Short alias for /repeat.thresh
            "config.show": self.config_controller.show_config,
            "prompt.show": self.prompt_controller.cmd_prompt_show,
            "prompt.style": self.prompt_controller.cmd_prompt_style,
            "prompt.list": self.prompt_controller.cmd_prompt_list,
            "prompt.profile": self.prompt_controller.cmd_prompt_profile,
            "prompt.preview": self.prompt_controller.cmd_prompt_preview,
            # Power commands
            "run.inline": self.cmd_run_inline,
            "quickpaste": self.cmd_quickpaste,
            "checkpoint.save": self.checkpoint_controller.cmd_ckpt_save,
            "checkpoint.load": self.checkpoint_controller.cmd_ckpt_load,
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

        # Check if this is a Typer command (not starting with a known local command)
        if command_name not in self.commands and not command_name.startswith("help"):
            # This is a Typer command, dispatch it in background thread
            if self._command_busy:
                self.console.print("[yellow]Command busy, please wait...[/yellow]")
                return

            self._command_busy = True
            try:
                # Import the app here to avoid circular imports
                from .registry import app

                # Dispatch the command to the Typer app in a background thread
                loop = asyncio.get_event_loop()
                exit_code = await loop.run_in_executor(
                    self._executor, dispatch_command, app, cmd_line, self.ctx
                )

                if exit_code != 0:
                    self.console.print(
                        f"[red]Command failed with exit code: {exit_code}[/red]"
                    )
            finally:
                self._command_busy = False
            return

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
  /run.inline - Paste and run a multi-line YAML recipe (end with EOF)
  /quickpaste - Paste multiple /commands (end with EOF)
  /checkpoint.save [name] - Save current session state to checkpoint
  /checkpoint.load [name] - Load session state from checkpoint
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

        # Get internal token from environment, config file, or default
        import os

        internal_token = os.getenv("XSA_INTERNAL_TOKEN")
        if not internal_token:
            # Try to load from config file
            config_path = Path(".xsarena/config.yml")
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = yaml.safe_load(f) or {}
                    internal_token = config_data.get("bridge", {}).get(
                        "internal_api_token"
                    )
                except Exception:
                    pass  # Continue if config file can't be read

        if not internal_token:
            internal_token = "dev-token-change-me"  # Default fallback
            self.console.print(
                "[yellow]Tip: Set XSA_INTERNAL_TOKEN or add bridge.internal_api_token in .xsarena/config.yml[/yellow]"
            )

        # Prepare headers with internal token
        headers = {"x-internal-token": internal_token}

        # Make request to start ID capture (requests is in dependencies)
        try:
            resp = requests.post(start_capture_url, headers=headers, timeout=10)
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
                response = requests.get(config_url, headers=headers, timeout=5)
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
        extra_note = profile_data.get("extra_note") or profile_data.get("extra", "")

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
        extra_note = profile_data.get("extra_note") or profile_data.get("extra", "")

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

    async def cmd_run_inline(self, args: list):
        """Read a multi-line YAML recipe until a line 'EOF' and run it."""
        self.console.print("[dim]Paste YAML recipe. End with a line: EOF[/dim]")
        buf = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip() == "EOF":
                break
            buf.append(line)
        recipe = "\n".join(buf)
        if not recipe.strip():
            self.console.print("[red]No content provided[/red]")
            return
        # Write to temp file and call run_from_recipe via orchestrator
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile(
            "w", delete=False, suffix=".yml", encoding="utf-8"
        ) as tf:
            tf.write(recipe)
            path = tf.name
        self.console.print(f"[dim]Recipe → {path}[/dim]")
        try:
            # Minimal loader: parse subject,length,span,overlays
            import yaml

            data = yaml.safe_load(recipe) or {}
            subject = data.get("subject") or "inline"
            length = data.get("length", "long")
            span = data.get("span", "book")
            overlays = data.get("overlays") or getattr(
                self.ctx.state, "overlays_active", ["narrative", "no_bs"]
            )
            out_path = (data.get("io") or {}).get("outPath") or ""
            run_spec = RunSpecV2(
                subject=subject,
                length=LengthPreset(length),
                span=SpanPreset(span),
                overlays=overlays,
                out_path=out_path,
            )
            job_id = await self.orchestrator.run_spec(
                run_spec, backend_type=self.ctx.state.backend
            )
            self.console.print(f"[green]✓ Submitted inline job: {job_id}[/green]")
        except Exception as e:
            self.console.print(f"[red]Inline run failed: {e}[/red]")

    async def cmd_quickpaste(self, args: list):
        """Paste multiple /commands; end with 'EOF'."""
        self.console.print("[dim]Paste /commands (one per line). End with: EOF[/dim]")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip() == "EOF":
                break
            lines.append(line.strip())
        for ln in lines:
            if not ln:
                continue
            if not ln.startswith("/"):
                self.console.print(f"[yellow]Skipping (not a /command): {ln}[/yellow]")
                continue
            await self.handle_command(ln[1:])


async def start_interactive_session(ctx: CLIContext):
    """Start the interactive session with the given context."""
    session = InteractiveSession(ctx)
    await session.start()
