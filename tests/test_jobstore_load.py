#!/usr/bin/env python3
"""
Minimal test stub to catch regressions: jobstore load.
"""

import json
import tempfile
from pathlib import Path


def test_jobstore_load():
    """Test that JobStore can load a valid job.json file."""
    from xsarena.core.jobs.model import JobV3
    from xsarena.core.jobs.store import JobStore

    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        job_dir = Path(tmpdir) / "test_job"
        job_dir.mkdir()

        # Create a minimal valid job.json
        job_data = {
            "id": "test_job_123",
            "name": "Test Job",
            "run_spec": {
                "subject": "Test Subject",
                "length": "STANDARD",
                "span": "MEDIUM",
                "backend": "bridge",
                "model": "default",
            },
            "backend": "bridge",
            "state": "PENDING",
            "retries": 0,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "artifacts": {},
            "meta": {},
            "progress": {},
        }

        job_file = job_dir / "job.json"
        job_file.write_text(json.dumps(job_data), encoding="utf-8")

        # Test loading
        store = JobStore()
        job = store.load("test_job")

        # Verify it's a JobV3 instance
        assert isinstance(job, JobV3)
        assert job.id == "test_job_123"
        assert job.name == "Test Job"
