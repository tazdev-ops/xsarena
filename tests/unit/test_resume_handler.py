"""Tests for resume handler."""
from unittest.mock import Mock
from xsarena.core.jobs.resume_handler import ResumeHandler


def test_resume_handler_check_and_handle_resume():
    """Test the resume handler logic."""
    # Create a mock job runner
    mock_job_runner = Mock()
    mock_job_runner.find_resumable_job_by_output.return_value = "test-job-id"
    
    # Create resume handler
    handler = ResumeHandler(mock_job_runner)
    
    # Test case: existing job found, resume=True
    should_create_new, existing_job_id = handler.check_and_handle_resume(
        out_path="test.txt",
        resume=True,
        overwrite=False,
        is_tty=False
    )
    assert should_create_new is False
    assert existing_job_id == "test-job-id"
    
    # Test case: existing job found, overwrite=True
    should_create_new, existing_job_id = handler.check_and_handle_resume(
        out_path="test.txt",
        resume=None,
        overwrite=True,
        is_tty=False
    )
    assert should_create_new is True
    assert existing_job_id is None
    
    # Test case: no existing job
    mock_job_runner.find_resumable_job_by_output.return_value = None
    should_create_new, existing_job_id = handler.check_and_handle_resume(
        out_path="new_test.txt",
        resume=None,
        overwrite=False,
        is_tty=False
    )
    assert should_create_new is True
    assert existing_job_id is None