"""Test config model functionality."""
import tempfile
from pathlib import Path
import yaml

def test_config_model():
    """Test config model load/save and URL normalization."""
    from xsarena.core.config import Config
    
    # Test basic instantiation
    config = Config()
    assert config.backend == "bridge"
    assert config.model == "default"
    assert config.base_url == "http://127.0.0.1:5102/v1"
    
    # Test URL normalization (should add /v1 if missing)
    # Note: The validator normalizes the URL when the field is set
    config = Config(base_url="http://127.0.0.1:5102")
    assert config.base_url == "http://127.0.0.1:5102/v1"
    
    # Test with /v1 already present (should not duplicate)
    config_with_v1 = Config(base_url="http://127.0.0.1:5102/v1")
    assert config_with_v1.base_url == "http://127.0.0.1:5102/v1"
    
    # Test save/load roundtrip
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "config.yml"
        
        # Modify some values
        config.backend = "openrouter"
        config.model = "openrouter/auto"
        config.base_url = "https://openrouter.ai/api/v1"
        
        # Save config
        config.save_to_file(str(config_path))
        
        # Verify file was created
        assert config_path.exists()
        
        # Load config back
        loaded_config = Config.load_from_file(str(config_path))
        
        # Verify values match
        assert loaded_config.backend == "openrouter"
        assert loaded_config.model == "openrouter/auto"
        assert loaded_config.base_url == "https://openrouter.ai/api/v1"
        
        print("✓ Config model test passed")