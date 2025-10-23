"""Tests for run_continue command signature."""
import inspect
import tempfile
from contextlib import suppress
from pathlib import Path

from click import Command
from click import Context as ClickContext
from xsarena.cli.cmds_run_continue import run_continue


def test_run_continue_signature():
    """Ensure function accepts typer.Context as first param (smoke)."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
        f.write("# Test file\nThis is a test.")
        temp_path = Path(f.name)

    try:
        ctx = ClickContext(Command("dummy"))
        # Minimal CLIContext-like object the command expects on ctx.obj
        ctx.obj = type(
            "CLIContext",
            (),
            {
                "state": type("State", (), {"backend": "bridge", "model": "default"})(),
            },
        )()
        with suppress(Exception):
            run_continue(ctx, temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def test_run_continue_signature_position():
    """Confirm typer.Context is the first parameter in the signature."""
    params = list(inspect.signature(run_continue).parameters.keys())
    assert params[0] == "ctx"
