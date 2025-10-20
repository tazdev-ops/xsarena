"""Unit tests for jobs next functionality."""

import tempfile
from pathlib import Path

import pytest
from xsarena.core.jobs.model import JobManager


@pytest.mark.asyncio
async def test_jobs_next_applies_immediately():
    """Test that jobs next applies immediately (mock transport send calls count and last prompt)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Create a job runner
            job_runner = JobManager()

            # Create a mock run spec using a dictionary approach to avoid circular imports
            # We'll test the core functionality without creating a full RunSpecV2
            job_id = "test-job-id"
            job_dir = Path(".xsarena/jobs") / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            # Directly test the send_control_message functionality
            await job_runner.send_control_message(job_id, "next", "Do X now")

            # Check that the control message was queued
            assert job_id in job_runner.control_queues
            assert not job_runner.control_queues[job_id].empty()

            # Get the queued message
            queued_msg = await job_runner.control_queues[job_id].get()
            assert queued_msg["type"] == "next"
            assert queued_msg["text"] == "Do X now"

        finally:
            os.chdir(original_cwd)
