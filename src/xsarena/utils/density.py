# src/xsarena/utils/density.py
from __future__ import annotations

import re
from typing import Iterable

# Minimal, language-agnostic approximations; no heavy NLP deps
_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "for",
    "to",
    "of",
    "in",
    "on",
    "at",
    "by",
    "with",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "that",
    "this",
    "those",
    "these",
    "it",
    "its",
    "from",
    "into",
    "over",
    "under",
    "about",
    "above",
    "below",
    "up",
    "down",
    "out",
    "off",
}

# A compact set of hedges/fillers/adverbs worth suppressing
_FILLERS = {
    "actually",
    "basically",
    "clearly",
    "simply",
    "obviously",
    "literally",
    "just",
    "kind of",
    "sort of",
    "very",
    "really",
    "quite",
    "perhaps",
    "maybe",
    "likely",
    "possibly",
    "probably",
    "generally",
    "in fact",
    "indeed",
    "note that",
    "as you can see",
    "as we saw",
    "in summary",
}

_SENT_SPLIT = re.compile(r"[.!?]+\s+")
_WORD_SPLIT = re.compile(r"\b\w+\b", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return _WORD_SPLIT.findall(text or "")


def lexical_density(text: str) -> float:
    """Approximate ratio of content words to total tokens."""
    toks = _tokens(text)
    if not toks:
        return 0.0
    content = [t for t in toks if t.lower() not in _STOPWORDS and len(t) > 2]
    return len(content) / max(1, len(toks))


def filler_rate(text: str) -> float:
    """Estimated filler/hedge counts per 1000 words."""
    toks = _tokens(text)
    if not toks:
        return 0.0
    text_l = " " + (text or "").lower() + " "
    hits = 0
    for f in _FILTER_NORMALIZE(_FILLERS):
        if f in text_l:
            # rough count by split difference
            hits += max(0, text_l.count(f))
    per_k = hits * 1000.0 / max(1, len(toks))
    return per_k


def _FILTER_NORMALIZE(items: Iterable[str]) -> set[str]:
    return {(" " + i.lower().strip() + " ") for i in items if i and i.strip()}


def avg_sentence_len(text: str) -> float:
    """Average sentence length in words."""
    sents = _SENT_SPLIT.split(text or "")
    toks = [_tokens(s) for s in sents if s.strip()]
    if not toks:
        return 0.0
    lengths = [len(t) for t in toks if t]
    if not lengths:
        return 0.0
    return sum(lengths) / len(lengths)
