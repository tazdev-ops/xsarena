"""Tests for secrets scanner."""
import tempfile
from pathlib import Path
from xsarena.utils.secrets_scanner import SecretsScanner


def test_secrets_scanner_basic():
    """Test basic secrets scanning functionality."""
    scanner = SecretsScanner()
    
    # Create a temporary file with some test content
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('api_key = "test_1234567890abcdef"')
        temp_file = Path(f.name)
    
    try:
        findings = scanner.scan_file(temp_file)
        assert len(findings) >= 1  # Should find the API key
        assert any(f['type'] == 'api_key' for f in findings)
    finally:
        temp_file.unlink()


def test_secrets_scanner_whitelist():
    """Test secrets scanning with whitelist."""
    # Create a temporary whitelist file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('test_1234567890abcdef')  # Whitelist just the value part
        whitelist_file = Path(f.name)
    
    try:
        # Create a scanner with whitelist
        scanner = SecretsScanner(whitelist_file=str(whitelist_file))
        
        # Create a temporary file with content that contains the whitelisted value
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('some_content = "test_1234567890abcdef"')  # Not an API key pattern
            temp_file = Path(f.name)
        
        try:
            findings = scanner.scan_file(temp_file)
            # Should not find anything since it doesn't match API key pattern
            assert len(findings) == 0
        finally:
            temp_file.unlink()
    finally:
        whitelist_file.unlink()