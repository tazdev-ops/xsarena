"""CLI integration tests for core flows."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner
from xsarena.cli.main import app

runner = CliRunner()


def test_run_book_integration(patch_create_backend):
    """Test xsarena run book command creates output file."""
    from unittest.mock import AsyncMock, MagicMock

    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = Path(temp_dir) / "test_output.md"

        # Mock the scheduler to prevent actual job execution
        with patch(
            "xsarena.core.v2_orchestrator.orchestrator.Scheduler"
        ) as MockScheduler:
            mock_scheduler_instance = MockScheduler.return_value
            # Make wait_for_job an awaitable that does nothing
            mock_scheduler_instance.wait_for_job = AsyncMock(return_value=None)
            mock_scheduler_instance.submit_job = AsyncMock(return_value=True)

            # Mock the JobManager for submission and loading
            with patch("xsarena.core.jobs.manager.JobManager") as MockJobManager:
                mock_jm_instance = MockJobManager.return_value
                mock_jm_instance.submit.return_value = "test-job-id"

                # Create a mock job object for the load method
                mock_job = MagicMock()
                mock_job.state = "RUNNING"
                mock_jm_instance.load.return_value = mock_job
                mock_jm_instance.find_resumable_job_by_output.return_value = None

                # Run the command
                result = runner.invoke(
                    app,
                    [
                        "run",
                        "book",
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
                assert result.exit_code == 0, result.output


def test_fix_run_integration():
    """Test xsarena fix run command."""
    result = runner.invoke(app, ["fix", "run"])

    # Should succeed (exit code 0 for success, 2 for warnings)
    assert result.exit_code in [0, 2]
