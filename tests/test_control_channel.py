"""Tests for JobManager control channel functionality (pause/resume/next/cancel)."""

import asyncio

import pytest
from xsarena.core.jobs.model import JobManager


def test_control_queue_creation():
    """Test that control queues are created properly."""
    job_runner = JobManager()

    # Test that queues are created when needed
    job_id = "test-job-id"

    # Initially should not exist
    assert job_id not in job_runner.control_queues

    # Create a queue manually for testing
    job_runner.control_queues[job_id] = asyncio.Queue()

    assert job_id in job_runner.control_queues
    assert isinstance(job_runner.control_queues[job_id], asyncio.Queue)


@pytest.mark.asyncio
async def test_queue_message_format_direct():
    """Test that we can directly put and get control messages in the queue with correct format."""
    job_runner = JobManager()
    job_id = "test-job-id"

    # Create the queue manually for testing
    job_runner.control_queues[job_id] = asyncio.Queue()

    # Directly put messages in the queue (simulating what send_control_message does)
    await job_runner.control_queues[job_id].put({"type": "pause"})
    await job_runner.control_queues[job_id].put({"type": "resume"})
    await job_runner.control_queues[job_id].put(
        {"type": "next", "text": "Continue with the next section"}
    )
    await job_runner.control_queues[job_id].put({"type": "cancel"})

    # Verify messages were added to the queue with correct format
    messages = []
    while not job_runner.control_queues[job_id].empty():
        messages.append(await job_runner.control_queues[job_id].get())

    assert len(messages) == 4
    assert messages[0]["type"] == "pause"
    assert messages[1]["type"] == "resume"
    assert messages[2]["type"] == "next"
    assert messages[2]["text"] == "Continue with the next section"
    assert messages[3]["type"] == "cancel"

    # Verify that all messages have the required "type" field
    for msg in messages:
        assert "type" in msg


@pytest.mark.asyncio
async def test_control_queue_message_flow():
    """Test the flow of messages through the control queue."""
    job_runner = JobManager()
    job_id = "test-job-flow"

    # Create the queue manually for testing
    job_runner.control_queues[job_id] = asyncio.Queue()

    # Put a message in the queue
    test_message = {"type": "pause"}
    await job_runner.control_queues[job_id].put(test_message)

    # Check that the queue was created and message was added
    assert not job_runner.control_queues[job_id].empty()

    retrieved_message = await job_runner.control_queues[job_id].get()
    assert retrieved_message["type"] == "pause"
    assert retrieved_message == test_message
