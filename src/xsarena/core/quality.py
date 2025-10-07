#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class Rubric:
    teach_before_use: float = 0.35
    quick_checks: float = 0.20
    pitfalls: float = 0.15
    narrative_flow: float = 0.20
    next_marker: float = 0.10


DEFAULT_RUBRIC = Rubric()


def _first_use_defs_ok(text: str) -> bool:
    # naive: look for **Term** (short parenthetical) at first occurrence
    # pass if we see at least N patterns
    return bool(re.search(r"\*\*[A-Za-z0-9 \-]+\*\*\s*\([^)]+\)", text))


def _has_quick_checks(text: str) -> bool:
    return "Quick check" in text or re.search(r"(?im)^- \s*Q\d?\:", text) is not None


def _has_pitfalls(text: str) -> bool:
    return "Pitfalls" in text or re.search(r"(?im)^- \s*Pitfall", text) is not None


def _narrative_ok(text: str) -> bool:
    # naive: penalize bullet-wall ratio
    lines = text.splitlines()
    if not lines:
        return False
    bullets = sum(1 for l in lines if l.strip().startswith(("-", "*", "•")))
    return bullets / max(1, len(lines)) < 0.35


def _has_next(text: str) -> bool:
    return re.search(r"(?im)^\s*NEXT:\s*\[.*\]\s*$", text) is not None


def score_section(text: str, rubric: Rubric = DEFAULT_RUBRIC) -> Tuple[float, Dict[str, float]]:
    s = 0.0
    breakdown = {}
    tb = 1.0 if _first_use_defs_ok(text) else 0.0
    qc = 1.0 if _has_quick_checks(text) else 0.0
    pf = 1.0 if _has_pitfalls(text) else 0.0
    nf = 1.0 if _narrative_ok(text) else 0.0
    nx = 1.0 if _has_next(text) else 0.0
    s = (
        tb * rubric.teach_before_use
        + qc * rubric.quick_checks
        + pf * rubric.pitfalls
        + nf * rubric.narrative_flow
        + nx * rubric.next_marker
    )
    breakdown = {"teach_before_use": tb, "quick_checks": qc, "pitfalls": pf, "narrative": nf, "next": nx}
    return s, breakdown
