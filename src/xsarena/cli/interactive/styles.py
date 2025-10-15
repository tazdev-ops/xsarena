#!/usr/bin/env python3
"""
Style functions extracted from interactive.py
"""

import os
from typing import Dict


def _apply_style_overlays(
    sys_text: str, styles: list[str] | None, style_file: str | None
) -> str:
    """Apply style overlays to system text."""
    text = sys_text
    if styles:
        for s in styles:
            sv = s.strip().lower()
            if sv in ("no-bs", "nobs", "no_bs", "no-bullshit"):
                from lma_templates import NO_BS_ADDENDUM

                text = text.strip() + "\n\n" + NO_BS_ADDENDUM
            elif sv == "chad":
                from lma_templates import CHAD_TEMPLATE

                text = text.strip() + "\n\n" + CHAD_TEMPLATE
        if style_file and os.path.exists(style_file):
            with open(style_file, "r", encoding="utf-8") as f:
                style = f.read()
            text = (
                text.strip() + "\n\nSTYLE OVERLAY:\n<<<STYLE\n" + style + "\nSTYLE>>>"
            )
        return text
    return text


def set_system(text: str, state: Dict):
    """
    Args:
        text: system prompt text
        state: dict containing shared state (SYSTEM_PROMPT)
    """
    state["SYSTEM_PROMPT"] = text or ""


def set_window(n: int, state: Dict):
    """
    Args:
        n: window size
        state: dict containing shared state (HISTORY_WINDOW)
    """
    state["HISTORY_WINDOW"] = max(0, int(n))
