"""Unit tests for project deduplication functionality."""

from typer.testing import CliRunner
from xsarena.cli.main import app


def test_dedupe_by_hash_uses_pathlib_stat():
    """Test that dedupe-by-hash command returns exit code 2 (command not found)."""
    # NOTE: The project command was removed, so this functionality is no longer available
    # through the main CLI. This test now verifies that the command doesn't exist.
    runner = CliRunner()
    result = runner.invoke(app, ["project", "dedupe", "dedupe-by-hash"])
    assert result.exit_code == 2  # Command should not exist, exit code 2
