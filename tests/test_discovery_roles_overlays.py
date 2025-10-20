"""Unit tests for roles and overlays discovery."""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from xsarena.cli.main import app


def test_roles_overlays_discovery():
    """Test that roles/overlays discovery lists entries with correct counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Create the directives structure
            roles_dir = Path("directives/roles")
            roles_dir.mkdir(parents=True)

            # Create some test role files
            (roles_dir / "role1.md").write_text("# Role 1\nThis is role 1 description")
            (roles_dir / "role2.md").write_text("# Role 2\nThis is role 2 description")

            # Create style overlay files
            directives_dir = Path("directives")
            (directives_dir / "style.test.md").write_text(
                "# Test Style\nOVERLAY: Test overlay for testing"
            )
            (directives_dir / "style.another.md").write_text(
                "# Another Style\nOVERLAY: Another overlay"
            )

            runner = CliRunner()

            # Test roles list
            result = runner.invoke(app, ["list", "roles"])
            assert result.exit_code == 0
            assert "role1.md" in result.output
            assert "role2.md" in result.output

            # Test roles show
            result = runner.invoke(app, ["roles", "show", "role1.md"])
            assert result.exit_code == 0
            assert "Role: role1.md" in result.output

            # Test overlays list
            result = runner.invoke(app, ["list", "overlays"])
            assert result.exit_code == 0
            assert "style.test.md" in result.output
            assert "style.another.md" in result.output
            assert "Test overlay for testing" in result.output
            assert "Another overlay" in result.output

        finally:
            os.chdir(original_cwd)
