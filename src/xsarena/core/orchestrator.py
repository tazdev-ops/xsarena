from __future__ import annotations
from pathlib import Path
from typing import Optional
from .prompt import compose_prompt
from .specs import RunSpec
from .chunking import anchor_from_text

def _slugify(s: str) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "book"

def build_system_text(spec: RunSpec) -> str:
    min_chars, passes, chunks = spec.resolved()
    comp = compose_prompt(
        subject=spec.subject,
        base="zero2hero",
        overlays=spec.overlays,
        extra_notes=spec.extra_note,
        min_chars=min_chars,
        passes=passes,
        max_chunks=chunks,
    )
    system = comp.system_text
    if spec.outline_scaffold:
        system += "\n\nOUTLINE-FIRST SCAFFOLD\n" + spec.outline_scaffold
    for ef in spec.extra_files:
        p = Path(ef)
        if p.exists() and p.is_file():
            try:
                system += "\n\n" + p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
    return system

def build_recipe(spec: RunSpec, system_text: str) -> dict:
    min_chars, passes, chunks = spec.resolved()
    out = spec.out_path or f"./books/finals/{_slugify(spec.subject)}.final.md"
    return {
        "task": "book.zero2hero",
        "subject": spec.subject,
        "system_text": system_text,
        "max_chunks": chunks,
        "continuation": {"mode": "anchor", "minChars": min_chars, "pushPasses": passes, "repeatWarn": True},
        "io": {"output": "file", "outPath": out},
    }

async def seed_continue(engine, book_path: Path, system_text: str, min_chars: int, passes: int, chunks: Optional[int]):
    st = engine.state
    st.session_mode = "zero2hero"
    st.output_min_chars = min_chars
    st.output_push_max_passes = passes
    st.output_budget_snippet_on = True

    tail = anchor_from_text(book_path.read_text(encoding="utf-8", errors="ignore"), st.anchor_length)
    seed = await engine.build_anchor_continue_prompt(tail) if tail else "Continue."
    first = await engine.send_and_collect(seed, system_prompt=system_text)
    with book_path.open("a", encoding="utf-8") as f:
        if not first.startswith("\n"):
            f.write("\n\n")
        f.write(first.strip())
    if chunks is None:
        await engine.autopilot_run(initial_prompt="BEGIN", max_chunks=None)
    else:
        remain = max(0, chunks - 1)
        if remain > 0:
            await engine.autopilot_run(initial_prompt="BEGIN", max_chunks=remain)