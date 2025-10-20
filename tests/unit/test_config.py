"""Tests for configuration loading and validation."""
import pytest
from xsarena.core.config import Config

def test_config_defaults():
    config = Config()
    assert config.backend == "bridge"
    assert config.model == "default"
    assert config.window_size == 100

def test_config_validation():
    with pytest.raises(ValueError):
        Config(window_size=0)  # Should fail validation
    
    with pytest.raises(ValueError):
        Config(repetition_threshold=1.5)  # Should fail validation

def test_base_url_normalization():
    config = Config(base_url="http://localhost:5102")
    assert config.base_url.endswith("/v1")