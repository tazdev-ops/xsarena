"""Unit tests for bridge v2 health endpoint without WebSocket."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the bridge_v2 module to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import the app from bridge_v2.api_server
from xsarena.bridge_v2.api_server import app

client = TestClient(app)


def test_health_endpoint():
    """Test the health endpoint without requiring WebSocket connection."""
    with patch('xsarena.bridge_v2.api_server.browser_ws', None):
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "ts" in data
        assert "ws_connected" in data
        assert data["status"] == "ok"
        assert data["ws_connected"] is False  # Since we patched to None


def test_health_endpoint_with_mock_ws():
    """Test the health endpoint with a mock WebSocket connection."""
    mock_ws = MagicMock()
    
    with patch('xsarena.bridge_v2.api_server.browser_ws', mock_ws):
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "ts" in data
        assert "ws_connected" in data
        assert data["status"] == "ok"
        assert data["ws_connected"] is True  # Since we have a mock WebSocket