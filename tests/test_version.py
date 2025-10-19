from typer.testing import CliRunner

from xsarena.cli.main import app

runner = CliRunner()


def test_version_command():
    """Test that 'xsarena version' command runs and prints a version string."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "XSArena v" in result.stdout
    assert len(result.stdout.strip().splitlines()) == 1


def test_version_module_import():
    """Test that the version is correctly exposed in the module."""
    import xsarena

    assert hasattr(xsarena, "__version__")
    assert isinstance(xsarena.__version__, str)
    assert len(xsarena.__version__.split(".")) >= 3
