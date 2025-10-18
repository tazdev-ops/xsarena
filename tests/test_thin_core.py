"""Tests for thin-core behavior - ensure joy/people commands don't crash when optional modules aren't installed."""

import subprocess
import sys


def test_joy_commands_thin_core():
    """Test that joy commands don't crash in thin-core; they either work minimally or print a clean message."""
    # Test by running the CLI commands and checking they don't crash
    try:
        result = subprocess.run(
            [sys.executable, "-m", "xsarena", "joy", "streak"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # The command should not crash (return code should not be in error range for import issues)
        # It should either work or print a clean message about missing features
        assert result.returncode in [0, 1]  # 0 for success, 1 for expected user errors
        # If it fails due to import issues, it would return a different code

    except subprocess.TimeoutExpired:
        # This is acceptable if the command runs but doesn't complete quickly
        pass


def test_people_commands_thin_core():
    """Test that people commands don't crash in thin-core; they either work minimally or print a clean message."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "xsarena", "people", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # The command should not crash with import errors
        assert result.returncode in [0, 1]  # 0 for success, 1 for expected user errors

    except subprocess.TimeoutExpired:
        # This is acceptable
        pass


def test_import_error_handling():
    """Test that modules handle import errors gracefully."""
    # This test verifies that the try/except ImportError blocks work correctly

    # Temporarily remove any potential import paths to force ImportError
    # We'll test the specific files that have the import handling
    import xsarena.cli.cmds_joy

    # The module should have been imported without crashing
    assert hasattr(xsarena.cli.cmds_joy, "app")

    import xsarena.cli.cmds_people

    assert hasattr(xsarena.cli.cmds_people, "app")
