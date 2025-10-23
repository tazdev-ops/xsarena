# tests/unit/test_openrouter_default_base_url.py
from xsarena.core.backends.bridge_v2 import OpenRouterTransport


def test_openrouter_default_base_url(monkeypatch):
    # Ensure env override is absent
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)

    tr = OpenRouterTransport(api_key="dummy", model="openai/gpt-4o", timeout=1)
    # If you have not applied the default change yet, adjust/skip this assertion.
    assert tr.base_url == "https://openrouter.ai/api/v1"
