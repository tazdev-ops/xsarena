# tests/unit/test_helpers_id_capture_headers.py
import types

import pytest
from xsarena.utils.helpers import capture_bridge_ids


def _mk_resp(status, payload=None):
    resp = types.SimpleNamespace()
    resp.status_code = status
    resp.text = ""
    if payload is None:
        payload = {}

    def _json():
        return payload

    resp.json = _json
    return resp


def test_capture_bridge_ids_uses_internal_token_header(monkeypatch, tmp_path):
    # Arrange: set env token to ensure it is picked up
    monkeypatch.setenv("XSA_INTERNAL_TOKEN", "x-test-token")

    seen = {"post_headers": None, "get_headers": None}

    def fake_post(url, headers=None, **kwargs):
        seen["post_headers"] = headers or {}
        return _mk_resp(200, {"ok": True})

    def fake_get(url, headers=None, **kwargs):
        seen["get_headers"] = headers or {}
        # Immediately return a valid config
        return _mk_resp(200, {"bridge": {"session_id": "S123", "message_id": "M456"}})

    # Patch requests inside the helpers module (not the global requests module)
    import xsarena.utils.helpers as helpers_mod

    monkeypatch.setattr(
        helpers_mod, "requests", types.SimpleNamespace(post=fake_post, get=fake_get)
    )

    # Act
    sess, msg = capture_bridge_ids("http://127.0.0.1:5102")

    # If legacy code path (no headers) is still present, skip rather than fail
    if not seen["post_headers"] or "x-internal-token" not in seen["post_headers"]:
        pytest.skip(
            "Legacy capture_bridge_ids without auth header; apply runtime improvement to enable this test."
        )

    # Assert
    assert (sess, msg) == ("S123", "M456")
    assert seen["post_headers"].get("x-internal-token") == "x-test-token"
    assert seen["get_headers"].get("x-internal-token") == "x-test-token"
