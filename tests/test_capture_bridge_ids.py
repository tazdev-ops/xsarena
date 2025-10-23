"""Tests for capture_bridge_ids auth header and fallbacks."""
from __future__ import annotations

import types
from pathlib import Path

from xsarena.utils.helpers import capture_bridge_ids


def _mk_resp(status: int, payload: dict | None = None):
    resp = types.SimpleNamespace()
    resp.status_code = status
    payload = payload or {}

    def _json():
        return payload

    resp.json = _json
    return resp


def test_capture_bridge_ids_sends_token_header(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Env token set
    monkeypatch.setenv("XSA_INTERNAL_TOKEN", "env-token")
    seen = {"post": None, "get": None}

    def fake_post(url, headers=None, **kwargs):
        seen["post"] = headers or {}
        return _mk_resp(200, {"ok": True})

    def fake_get(url, headers=None, **kwargs):
        seen["get"] = headers or {}
        return _mk_resp(200, {"bridge": {"session_id": "S1", "message_id": "M1"}})

    import xsarena.utils.helpers as helpers_mod

    monkeypatch.setattr(
        helpers_mod, "requests", types.SimpleNamespace(post=fake_post, get=fake_get)
    )

    s, m = capture_bridge_ids("http://127.0.0.1:5102")
    assert (s, m) == ("S1", "M1")
    assert seen["post"].get("x-internal-token") == "env-token"
    assert seen["get"].get("x-internal-token") == "env-token"


def test_capture_bridge_ids_uses_config_fallback(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # No env; config fallback
    monkeypatch.delenv("XSA_INTERNAL_TOKEN", raising=False)
    cfg = Path(".xsarena/config.yml")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("bridge:\n  internal_api_token: cfg-token\n", encoding="utf-8")

    seen = {"post": None, "get": None}

    def fake_post(url, headers=None, **kwargs):
        seen["post"] = headers or {}
        return _mk_resp(200, {"ok": True})

    def fake_get(url, headers=None, **kwargs):
        seen["get"] = headers or {}
        return _mk_resp(200, {"bridge": {"session_id": "S2", "message_id": "M2"}})

    import xsarena.utils.helpers as helpers_mod

    monkeypatch.setattr(
        helpers_mod, "requests", types.SimpleNamespace(post=fake_post, get=fake_get)
    )

    s, m = capture_bridge_ids("http://127.0.0.1:5102")
    assert (s, m) == ("S2", "M2")
    assert seen["post"].get("x-internal-token") == "cfg-token"
    assert seen["get"].get("x-internal-token") == "cfg-token"


def test_capture_bridge_ids_uses_default_fallback(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Neither env nor config → default token
    monkeypatch.delenv("XSA_INTERNAL_TOKEN", raising=False)

    seen = {"post": None, "get": None}

    def fake_post(url, headers=None, **kwargs):
        seen["post"] = headers or {}
        return _mk_resp(200, {"ok": True})

    def fake_get(url, headers=None, **kwargs):
        seen["get"] = headers or {}
        return _mk_resp(200, {"bridge": {"session_id": "S3", "message_id": "M3"}})

    import xsarena.utils.helpers as helpers_mod

    monkeypatch.setattr(
        helpers_mod, "requests", types.SimpleNamespace(post=fake_post, get=fake_get)
    )

    s, m = capture_bridge_ids("http://127.0.0.1:5102")
    assert (s, m) == ("S3", "M3")
    assert seen["post"].get("x-internal-token") == "dev-token-change-me"
    assert seen["get"].get("x-internal-token") == "dev-token-change-me"
