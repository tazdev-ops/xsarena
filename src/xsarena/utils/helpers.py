"""Helper utilities for XSArena snapshot and file operations."""

import json
from pathlib import Path
from typing import Tuple, Any, Optional


def is_binary_sample(data: bytes, sample_size: int = 8192) -> bool:
    """
    Heuristic check if bytes appear to be binary.
    
    Args:
        data: Bytes to check
        sample_size: Number of bytes to sample
        
    Returns:
        True if data appears binary, False if text
    """
    if not data:
        return False
    
    sample = data[:sample_size]
    
    # Null byte is strong indicator of binary
    if b'\x00' in sample:
        return True
    
    # Check ratio of non-text characters
    text_chars = bytes(range(32, 127)) + b'\n\r\t\b\f'
    non_text_count = sum(1 for byte in sample if byte not in text_chars)
    
    return (non_text_count / len(sample)) > 0.30


def safe_read_bytes(path: Path, max_bytes: int) -> Tuple[bytes, bool]:
    """
    Read file bytes with size limit.
    
    Args:
        path: File path to read
        max_bytes: Maximum bytes to read
        
    Returns:
        Tuple of (bytes_data, was_truncated)
    """
    try:
        file_size = path.stat().st_size
        
        if file_size <= max_bytes:
            return path.read_bytes(), False
        else:
            with open(path, 'rb') as f:
                return f.read(max_bytes), True
                
    except Exception as e:
        return f"[ERROR READING FILE: {e}]".encode('utf-8'), False


def safe_read_text(path: Path, max_chars: int) -> Tuple[str, bool]:
    """
    Read file text with character limit.
    
    Args:
        path: File path to read
        max_chars: Maximum characters to read
        
    Returns:
        Tuple of (text_content, was_truncated)
    """
    try:
        content = path.read_text(encoding='utf-8', errors='replace')
        
        if len(content) <= max_chars:
            return content, False
        else:
            return content[:max_chars], True
            
    except Exception as e:
        return f"[ERROR READING FILE: {e}]", False


def load_json_with_error_handling(path: Path) -> Any:
    """
    Load JSON from file with error handling.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If JSON is invalid
        Exception: For other errors
    """
    content = path.read_text(encoding='utf-8')
    data = json.loads(content)
    return data


def load_yaml_or_json(path: Path) -> Any:
    """
    Load YAML or JSON from file with error handling.
    
    Args:
        path: Path to YAML or JSON file
        
    Returns:
        Parsed data
        
    Raises:
        ImportError: If PyYAML is not available
        json.JSONDecodeError: If JSON is invalid
        Exception: For other errors
    """
    import yaml
    content = path.read_text(encoding='utf-8')
    
    # Determine format based on file extension
    if path.suffix.lower() in ['.yaml', '.yml']:
        data = yaml.safe_load(content)
    else:
        data = json.loads(content)
    
    return data


def capture_bridge_ids(base_url: str) -> tuple[str, str]:
    """
    Capture bridge session and message IDs by POSTing to /internal/start_id_capture,
    polling GET /internal/config until bridge.session_id/message_id appear (timeout ~90s),
    and return the captured IDs.
    
    Args:
        base_url: Base URL without /v1 suffix
        
    Returns:
        Tuple of (session_id, message_id)
        
    Raises:
        Exception: If IDs cannot be captured within timeout
    """
    import time
    import requests

    start_url = f"{base_url}/internal/start_id_capture"
    cfg_url = f"{base_url}/internal/config"
    
    # POST /internal/start_id_capture
    try:
        response = requests.post(start_url)
        if response.status_code != 200:
            raise Exception(f"Failed to start ID capture: {response.status_code}")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Could not connect to bridge server at {base_url}")

    # Poll GET /internal/config until bridge.session_id/message_id appear (timeout ~90s)
    timeout = 90  # seconds
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(cfg_url)
            if response.status_code == 200:
                config_data = response.json()
                bridge_config = config_data.get("bridge", {})
                session_id = bridge_config.get("session_id")
                message_id = bridge_config.get("message_id")

                if session_id and message_id:
                    return session_id, message_id
        except requests.exceptions.ConnectionError:
            pass  # Continue polling
        except Exception:
            pass  # Continue polling

        time.sleep(2)  # Wait 2 seconds before next poll

    raise Exception("Timeout: Failed to capture IDs within 90 seconds.")