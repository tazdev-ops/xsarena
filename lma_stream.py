#!/usr/bin/env python3
# lma_stream.py — shared parsing helpers for legacy CLI

import json
import re


# Extract streaming text chunks from LMArena a0/b0 protocol
def extract_text_chunks(buf: str):
    out = []
    while True:
        m = re.search(r'[ab]0:"', buf)
        if not m:
            break
        start = m.end()
        i = start
        while True:
            j = buf.find('"', i)
            if j == -1:
                return out, buf
            # count preceding backslashes
            bs = 0
            k = j - 1
            while k >= 0 and buf[k] == "\\":
                bs += 1
                k -= 1
            if bs % 2 == 0:
                esc = buf[start:j]
                try:
                    txt = json.loads('"' + esc + '"')
                    if txt:
                        out.append(txt)
                except Exception:
                    pass
                buf = buf[j + 1 :]
                break
            else:
                i = j + 1
    return out, buf


# NEXT: [...] detection
NEXT_RE = re.compile(r"^\s*NEXT:\s*(.+)\s*$", re.MULTILINE)


def strip_next_marker(text: str):
    hint = None
    last = None
    for m in NEXT_RE.finditer(text):
        last = m
    if last:
        hint = last.group(1).strip()
        text = text[: last.start()] + text[last.end() :]
    return text.rstrip(), hint


def anchor_from_text(txt: str, tail_chars: int) -> str:
    if not txt:
        return ""
    s = txt[-tail_chars:]
    p = max(s.rfind("."), s.rfind("!"), s.rfind("?"))
    if p != -1 and p >= len(s) - 120:
        s = s[: p + 1]
    return s.strip()


def jaccard_ngrams(a: str, b: str, n: int = 4) -> float:
    def ngrams(x):
        x = re.sub(r"\s+", " ", x.strip())
        return set([x[i : i + n] for i in range(0, max(0, len(x) - n + 1))])

    A, B = ngrams(a), ngrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def build_anchor_continue_prompt(anchor: str) -> str:
    return (
        "Continue exactly from after the following anchor. Do not repeat the anchor. "
        "Do not reintroduce the subject or previous headings; do not summarize; pick up mid-paragraph if needed.\n"
        "ANCHOR:\n<<<ANCHOR\n" + (anchor or "") + "\nANCHOR>>>\n"
        "Continue."
    )
