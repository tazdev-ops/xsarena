"""Dispatcher module to reuse Typer app for /command in interactive mode."""
import io
import shlex
import sys
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from typer import Typer


def dispatch_command(app: Typer, command_line: str, cli_context: Any) -> int:
    """
    Dispatch a command line string to the Typer app programmatically.

    Args:
        app: The main Typer application instance
        command_line: The command line string to execute (e.g., "run book 'Title' --dry-run")
        cli_context: The CLI context to pass to the app

    Returns:
        int: Exit code from the command execution
    """
    try:
        # Parse the command line with shlex
        args = shlex.split(command_line)
    except ValueError as e:
        print(f"Error parsing command: {e}")
        return 1

    # Capture stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        # Run the Typer app programmatically with captured output
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Set the context object for the app
            app(args, obj=cli_context, standalone_mode=False)

        # Get the captured output
        stdout_content = stdout_capture.getvalue()
        stderr_content = stderr_capture.getvalue()

        # Print both stdout and stderr
        if stdout_content:
            print(stdout_content, end="")
        if stderr_content:
            print(stderr_content, end="", file=sys.stderr)

        # Return success code (Typer with standalone_mode=False doesn't return exit codes directly)
        # In case of successful execution without exceptions, return 0
        return 0

    except SystemExit as e:
        # If the command called sys.exit(), capture the exit code
        stdout_content = stdout_capture.getvalue()
        stderr_content = stderr_capture.getvalue()

        # Print any captured output before the SystemExit
        if stdout_content:
            print(stdout_content, end="")
        if stderr_content:
            print(stderr_content, end="", file=sys.stderr)

        # Return the exit code from SystemExit
        return e.code if isinstance(e.code, int) else (1 if e.code else 0)

    except Exception as e:
        # Handle any other exceptions
        stderr_content = stderr_capture.getvalue()
        if stderr_content:
            print(stderr_content, end="", file=sys.stderr)

        print(f"Error executing command: {e}", file=sys.stderr)
        return 1
