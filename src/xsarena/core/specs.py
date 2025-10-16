from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

LENGTH_PRESETS = {
    "standard": {"min": 4200, "passes": 1},
    "long": {"min": 5800, "passes": 3},
    "very-long": {"min": 6200, "passes": 4},
    "max": {"min": 6800, "passes": 5},
}
SPAN_PRESETS = {"medium": 12, "long": 24, "book": 40}

DEFAULT_PROFILES = {
    "clinical-masters": {
        "overlays": ["narrative", "no_bs"],
        "extra": (
            "Clinical focus: teach‑before‑use; define clinical terms in plain English; "
            "cover models of psychopathology, assessment validity, case formulation, mechanisms, "
            "evidence‑based practice (evidence + expertise + patient values), outcomes/effect sizes; "
            "neutral narrative; avoid slogans/keywords; do not disclose protected test items."
        ),
    },
    "elections-focus": {
        "overlays": ["narrative", "no_bs"],
        "extra": (
            "Focus: treat elections as hinge points to explain coalitions, party systems, and institutional change; "
            "avoid seat lists unless they explain mechanism; dense narrative; no bullet walls."
        ),
    },
    "compressed-handbook": {
        "overlays": ["compressed", "no_bs"],
        "extra": "Compressed narrative handbook; minimal headings; no bullet walls; no slogans.",
    },
    "pop-explainer": {
        "overlays": ["no_bs"],
        "extra": "Accessible narrative explainer for general audiences; neutral tone; no hype.",
    },
    "bilingual-pairs": {
        "overlays": ["narrative", "no_bs", "bilingual"],
        "extra": "Output sections as EN/FA pairs with identical structure; translate labels only.",
    },
}


@dataclass
class RunSpec:
    subject: str
    length: str = "long"
    span: str = "book"
    overlays: List[str] = field(default_factory=lambda: ["narrative", "no_bs"])
    extra_note: str = ""
    extra_files: List[str] = field(default_factory=list)
    out_path: Optional[str] = None
    outline_scaffold: Optional[str] = None

    def resolved(self):
        L = LENGTH_PRESETS[self.length]
        chunks = SPAN_PRESETS[self.span]
        return L["min"], L["passes"], chunks
