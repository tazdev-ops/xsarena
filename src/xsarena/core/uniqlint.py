#!/usr/bin/env python3
import pathlib
import re


def _ngrams(s: str, n: int = 5):
    s = re.sub(r"\s+", " ", s.strip())
    return set(s[i : i + n] for i in range(0, max(0, len(s) - n + 1)))


def overlap(a: str, b: str, n: int = 5) -> float:
    A, B = _ngrams(a, n), _ngrams(b, n)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def scan(job_id: str, n: int = 5, thresh: float = 0.22):
    base = pathlib.Path(".xsarena") / "jobs" / job_id / "sections"
    files = [p for p in base.glob("**/*.md")]
    texts = {p: p.read_text(encoding="utf-8") for p in files}
    pairs = []
    for i, pi in enumerate(files):
        for pj in files[i + 1 :]:
            ov = overlap(texts[pi], texts[pj], n=n)
            if ov >= thresh:
                pairs.append({"a": str(pi), "b": str(pj), "overlap": round(ov, 3)})
    return pairs
