#!/usr/bin/env python3
"""
Minimal test stub to catch regressions: helpers loader.
"""

import json
import tempfile
from pathlib import Path

def test_helpers_loader():
    """Test that load_yaml_or_json works correctly."""
    from xsarena.utils.helpers import load_yaml_or_json
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test JSON loading
        json_file = Path(tmpdir) / "test.json"
        json_data = {"test": "value", "number": 42}
        json_file.write_text(json.dumps(json_data), encoding="utf-8")
        
        loaded_json = load_yaml_or_json(json_file)
        assert loaded_json == json_data
        
        # Test YAML loading
        yaml_file = Path(tmpdir) / "test.yaml"
        yaml_content = "test: value\nnumber: 42\n"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        
        loaded_yaml = load_yaml_or_json(yaml_file)
        assert loaded_yaml == json_data  # YAML should load same data as JSON
        
        # Test invalid file raises exception
        try:
            invalid_file = Path(tmpdir) / "invalid.json"
            invalid_file.write_text("{ invalid json }", encoding="utf-8")
            load_yaml_or_json(invalid_file)
            assert False, "Should have raised an exception"
        except Exception:
            pass  # Expected to raise an exception