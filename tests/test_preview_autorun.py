from pathlib import Path

import pytest
from typer.testing import CliRunner
from xsarena.cli.main import app

runner = CliRunner()


# Setup a minimal recipe for testing
@pytest.fixture(scope="module")
def minimal_recipe(tmp_path_factory):
    recipe_dir = tmp_path_factory.mktemp("recipes")
    recipe_path = recipe_dir / "test_preview.yml"

    content = """
subject: Test Preview Subject
system_text: |
  You are a test system. Your only job is to confirm the system prompt is received.
  Do not write anything else.
"""
    recipe_path.write_text(content)
    return recipe_path


def test_preview_run_autorun_no_crash(minimal_recipe, monkeypatch):
    """
    Test that 'xsarena preview run' with --autorun does not crash due to missing out_path.
    This validates the fix for Order 2.
    We mock the orchestrator to prevent a real job submission.
    """

    # Mock the orchestrator to prevent actual job submission
    class MockOrchestrator:
        async def run_spec(self, run_spec, backend_type):
            # Check that out_path is set to a default value
            assert run_spec.out_path is not None
            assert "books/test_preview_subject.final.md" in run_spec.out_path
            return "mock-job-id-123"

    monkeypatch.setattr(
        "xsarena.core.v2_orchestrator.orchestrator.Orchestrator", MockOrchestrator
    )

    # Ensure the default output directory exists for the mock to check the path
    Path("./books").mkdir(exist_ok=True)

    # Run the command with --autorun and --no-edit (to skip editor)
    result = runner.invoke(
        app,
        [
            "preview",
            "run",
            str(minimal_recipe),
            "--no-edit",
            "--autorun",
            "--no-sample",  # Skip sample generation to avoid engine calls
        ],
    )

    # The command should exit cleanly (exit code 0)
    assert result.exit_code == 0, f"Command crashed with error: {result.stderr}"
    assert "submitted: mock-job-id-123" in result.stdout
    assert "final → ./books/test_preview_subject.final.md" in result.stdout
    assert "submitted: mock-job-id-123" in result.stdout
    assert "final → ./books/test_preview_subject.final.md" in result.stdout


def test_prompt_run_smoke(minimal_recipe, monkeypatch):
    """
    Test that the new 'xsarena prompt run' command runs without crashing and uses the engine.
    This validates the fix for cmds_prompt.py.
    """

    MOCK_RESPONSE = "Mocked response from engine."

    # Mock the engine's send_and_collect method
    async def mock_send_and_collect(user_body, system_prompt=None):
        assert "You are a test system" in system_prompt
        assert (
            "Write your rough seeds below" not in user_body
        )  # Should not be in user body
        return MOCK_RESPONSE

    # Mock the engine method on the class where it is defined
    monkeypatch.setattr(
        "xsarena.core.engine.Engine.send_and_collect", mock_send_and_collect
    )

    # Run the command with --system (path to recipe) and --text (user input)
    result = runner.invoke(
        app,
        [
            "json",
            "run",
            "--system",
            str(minimal_recipe),
            "--text",
            "User prompt text",
        ],
    )

    # The command should exit cleanly (exit code 0)
    assert result.exit_code == 0, f"Command crashed with error: {result.stderr}"
    assert MOCK_RESPONSE in result.stdout
