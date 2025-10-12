#!/usr/bin/env python3
"""
Ingestion functions extracted from interactive.py
"""

from typing import Dict

# Ingestion constants
INGEST_SYSTEM_ACK = (
    "You are in ingestion ACK mode. You will receive CHUNK i/N.\n"
    "Reply with exactly: OK i/N. Do not echo content. Do not add any other text."
)

INGEST_SYSTEM_SYNTH = (
    "You are a synthesis engine. You will receive the previous Synthesis and a new CHUNK.\n"
    "Update the Synthesis to incorporate the new material. Keep it compact but complete:\n"
    "structured outline of topics, key claims, procedures, defaults, signature heuristics, and stylistic guidance.\n"
    "Preserve earlier coverage; merge or refactor as needed.\n"
    "Return ONLY the updated Synthesis (Markdown), no commentary, no code fences."
)

INGEST_SYSTEM_STYLE = (
    "You are a style profiler. Given an existing STYLE PROFILE and a new CHUNK, update the profile.\n"
    "Capture: tone, rhythm, sentence length, vocabulary, structure, devices, typical openings/closings, formatting, and no-goes.\n"
    "Return ONLY the updated STYLE PROFILE (Markdown), no commentary, no code fences."
)


def chunks_by_bytes(text: str, max_bytes: int):
    """Split text into chunks by byte size, respecting line boundaries."""
    b = text.encode("utf-8")
    out = []
    i = 0
    n = len(b)
    while i < n:
        j = min(i + max_bytes, n)
        if j < n:
            k = b.rfind(b"\n", i, j)
            if k == -1:
                k = b.rfind(b" ", i, j)
            if k != -1 and (j - k) < 2048:
                j = k
        part = b[i:j]
        while True:
            try:
                s = part.decode("utf-8")
                break
            except UnicodeDecodeError:
                part = part[:-1]
        out.append(s)
        i = j
    return out


def ingest_user_ack(i, n, chunk):
    return f"INGEST CHUNK {i}/{n}\n<BEGIN_CHUNK>\n{chunk}\n<END_CHUNK>\nReply with exactly: OK {i}/{n}\n"


def ingest_user_synth(i, n, synth_text, chunk, limit_chars):
    synth_excerpt = (
        synth_text[-limit_chars:] if len(synth_text) > limit_chars else synth_text
    )
    return (
        f"INGEST CHUNK {i}/{n}\n\n"
        f"PREVIOUS SYNTHESIS (<= {limit_chars} chars):\n<<<SYNTHESIS\n{synth_excerpt}\nSYNTHESIS>>>\n\n"
        f"NEW CHUNK:\n<<<CHUNK\n{chunk}\nCHUNK>>>\n\n"
        f"TASK:\n"
        f"- Update the Synthesis above to fully include the NEW CHUNK's information.\n"
        f"- Keep the updated Synthesis within ~{limit_chars} characters (short, dense).\n"
        f"- Return ONLY the updated Synthesis (Markdown), no commentary.\n"
    )


def style_user_profile(i, n, style_text, chunk, limit_chars):
    excerpt = style_text[-limit_chars:] if len(style_text) > limit_chars else style_text
    return (
        f"STYLE CAPTURE CHUNK {i}/{n}\n\n"
        f"CURRENT STYLE PROFILE (<= {limit_chars} chars):\n<<<STYLE\n{excerpt}\nSTYLE>>>\n\n"
        f"NEW CHUNK:\n<<<CHUNK\n{chunk}\nCHUNK>>>\n\n"
        f"TASK:\n- Update the STYLE PROFILE to capture the author voice precisely.\n"
        f"- Keep within ~{limit_chars} characters.\n- Return ONLY the STYLE PROFILE."
    )


async def ingest_ack_loop(path: str, chunk_kb: int, state: Dict):
    """
    Args:
        path: path to file to ingest
        chunk_kb: chunk size in KB
        state: dict containing shared state (functions like send_and_collect, build_payload, etc.)
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    chunk_bytes = max(8_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, chunk_bytes)
    ok = state.get("ok", print)
    send_and_collect = state["send_and_collect"]
    build_payload = state["build_payload"]
    set_system = state["set_system"]
    set_window = state["set_window"]
    now = state["now"]
    save_sys = state.get("SYSTEM_PROMPT", "")
    save_win = state.get("HISTORY_WINDOW", 80)

    ok(f"Ingest ACK mode: {len(parts)} chunks (~{chunk_kb} KB each)")
    set_system(INGEST_SYSTEM_ACK)
    set_window(0)

    try:
        for idx, chunk in enumerate(parts, start=1):
            msg = ingest_user_ack(idx, len(parts), chunk)
            reply = await send_and_collect(build_payload(msg), silent=True)
            print(f"[{now()}] Chunk {idx}/{len(parts)} ack: {reply.strip()[:50]}")
    finally:
        set_system(save_sys)
        set_window(save_win)


async def ingest_synth_loop(
    path: str, synth_out: str, chunk_kb: int, synth_chars: int, state: Dict
):
    """
    Args:
        path: path to file to ingest
        synth_out: output path for synthesis
        chunk_kb: chunk size in KB
        synth_chars: max chars for synthesis
        state: dict containing shared state
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    synth_limit = max(3000, int(synth_chars))
    chunk_bytes = max(10_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, chunk_bytes)
    synth_text = ""
    ok = state.get("ok", print)
    send_and_collect = state["send_and_collect"]
    build_payload = state["build_payload"]
    set_system = state["set_system"]
    set_window = state["set_window"]
    now = state["now"]
    save_sys = state.get("SYSTEM_PROMPT", "")
    save_win = state.get("HISTORY_WINDOW", 80)

    ok(
        f"Ingest SYNTH mode: {len(parts)} chunks (~{chunk_kb} KB each); synth limit ~{synth_limit} chars"
    )

    set_system(INGEST_SYSTEM_SYNTH)
    set_window(0)

    try:
        for idx, chunk in enumerate(parts, start=1):
            msg = ingest_user_synth(idx, len(parts), synth_text, chunk, synth_limit)
            reply = await send_and_collect(build_payload(msg), silent=True)
            synth_text = reply.strip()
            with open(synth_out, "w", encoding="utf-8") as f:
                f.write(synth_text)
            print(
                f"[{now()}] Synth updated {idx}/{len(parts)} — {len(synth_text)} chars"
            )
    finally:
        set_system(save_sys)
        set_window(save_win)
        ok(f"Synthesis saved to: {synth_out}")


async def ingest_style_loop(
    path: str, out_path: str, chunk_kb: int, style_chars: int, state: Dict
):
    """
    Args:
        path: path to file to ingest for style
        out_path: output path for style profile
        chunk_kb: chunk size in KB
        style_chars: max chars for style profile
        state: dict containing shared state
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    chunk_bytes = max(10_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, chunk_bytes)
    style_profile = ""
    ok = state.get("ok", print)
    send_and_collect = state["send_and_collect"]
    build_payload = state["build_payload"]
    set_system = state["set_system"]
    set_window = state["set_window"]
    now = state["now"]
    save_sys = state.get("SYSTEM_PROMPT", "")
    save_win = state.get("HISTORY_WINDOW", 80)

    set_system(INGEST_SYSTEM_STYLE)
    set_window(0)

    try:
        for idx, chunk in enumerate(parts, start=1):
            msg = style_user_profile(idx, len(parts), style_profile, chunk, style_chars)
            reply = await send_and_collect(build_payload(msg), silent=True)
            style_profile = reply.strip()
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(style_profile)
            print(
                f"[{now()}] Style updated {idx}/{len(parts)} — {len(style_profile)} chars"
            )
    finally:
        set_system(save_sys)
        set_window(save_win)
        ok(f"Style profile saved to: {out_path}")
