"""Tests for config base_url normalization and validation."""
import pytest
from xsarena.core.config import Config


def test_base_url_normalization():
    """Test that base_url is properly normalized to include /v1 suffix."""
    # Test that /v1 is appended when missing
    config = Config(base_url="http://example.com")
    assert config.base_url == "http://example.com/v1"

    # Test that /v1 is preserved when already present
    config = Config(base_url="http://example.com/v1")
    assert config.base_url == "http://example.com/v1"

    # Test that trailing slashes are handled correctly
    config = Config(base_url="http://example.com/")
    assert config.base_url == "http://example.com/v1"


def test_base_url_validation():
    """Test that base_url validation accepts http/https URLs."""
    # Valid URLs should pass
    Config(base_url="http://127.0.0.1:5102/v1")  # Should not raise
    Config(base_url="https://openrouter.ai/api/v1")  # Should not raise

    # Invalid formats should raise validation error
    with pytest.raises(ValueError, match="Invalid base_url format"):
        Config(base_url="[REDACTED_URL]")

    with pytest.raises(ValueError, match="Invalid base_url format"):
        Config(base_url="ftp://invalid.com")
