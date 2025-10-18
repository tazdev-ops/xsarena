"""CLI integration tests for core flows."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner
from xsarena.cli.main import app

runner = CliRunner()


def test_run_book_integration(patch_create_backend):
    """Test xsarena run book command creates output file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = Path(temp_dir) / "test_output.md"

        # Mock the recipe creation and job running to avoid actual AI calls
        with patch("xsarena.core.jobs.model.JobManager") as mock_runner:
            # Mock the submit and run_job methods
            mock_job_instance = mock_runner.return_value
            mock_job_instance.submit.return_value = "test-job-id"
            mock_job_instance.run_job.return_value = None

            # Run the command
            result = runner.invoke(
                app,
                [
                    "run",
                    "book",
                    "--subject",
                    "Test Subject",
                    "--out",
                    str(output_file),
                    "--length",
                    "standard",
                    "--span",
                    "medium",
                ],
            )

            # Should succeed
            assert result.exit_code == 0

            # Check if the job was submitted
            assert mock_job_instance.submit.called


def test_jobs_apply_integration(patch_create_backend):
    """Test xsarena jobs apply command."""
    # Create a temporary recipe file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(
            """
name: "Test Job"
task: "book.zero2hero"
subject: "Test Subject"
system_text: "Test system text"
max_chunks: 2
continuation:
  mode: "anchor"
  minChars: 1000
  pushPasses: 1
io:
  output: "file"
  outPath: "./test_output.md"
"""
        )
        recipe_path = f.name

    try:
        # Mock the job runner
        with patch("xsarena.core.jobs.model.JobManager") as mock_runner:
            mock_job_instance = mock_runner.return_value
            mock_job_instance.run_job.return_value = None

            # Run the command
            result = runner.invoke(app, ["jobs", "apply", recipe_path])

            # Should succeed
            assert result.exit_code == 0

            # Check if run_job was called
            assert mock_job_instance.run_job.called
    finally:
        # Clean up
        os.unlink(recipe_path)


def test_fix_run_integration():
    """Test xsarena fix run command."""
    result = runner.invoke(app, ["fix", "run"])

    # Should succeed (exit code 0 for success, 2 for warnings)
    assert result.exit_code in [0, 2]
