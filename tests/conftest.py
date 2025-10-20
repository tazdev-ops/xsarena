"""Pytest configuration for XSArena tests."""
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    from xsarena.core.config import Config

    return Config(
        backend="bridge",
        model="default",
        window_size=100,
        anchor_length=300,
        continuation_mode="anchor",
        repetition_threshold=0.35,
        max_retries=3,
        base_url="http://127.0.0.1:5102/v1",
        timeout=300,
        redaction_enabled=False,
    )
