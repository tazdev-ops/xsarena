#!/usr/bin/env python3
"""
Recipe functions extracted from interactive.py
"""

import asyncio
import json
import os
from typing import Dict

try:
    import yaml
except ImportError:
    yaml = None


def _load_yaml_or_json(path: str):
    """Load YAML or JSON file."""
    try:
        if yaml:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def slugify(s: str) -> str:
    """Convert string to URL-safe slug."""
    import re

    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "book"


def next_available_path(base_path: str) -> str:
    """Get next available filename if file exists."""
    from datetime import datetime

    if not os.path.exists(base_path):
        return base_path
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root, ext = os.path.splitext(base_path)
    return f"{root}-{stamp}{ext or '.md'}"


async def run_recipe_file(path: str, state: Dict):
    """Run recipe from file."""
    rec = _load_yaml_or_json(path)
    await run_recipe(rec, state)


async def z2h_run(
    subject: str,
    state: Dict,
    out_path: str | None = None,
    max_chunks: int = 8,
    min_chars: int = 3000,
):
    """Run zero-to-hero recipe."""
    rec = {
        "task": "book.zero2hero",
        "subject": subject,
        "styles": ["no-bs"],
        "system_text": (
            "PEDAGOGY & NARRATIVE OVERLAY\n"
            "- English only. Smooth explanatory narrative; avoid “bullet walls” except checklists/pitfalls.\n"
            "- Teach-before-use: define every new term at first mention (bold term + 1-line).\n"
            "- Section pattern: Orientation → Key terms → Stepwise explanation → Short vignette → Quick check (2–3) → Pitfalls (1–3).\n"
            "- No early wrap-up; continue exactly where you left off.\n"
            "OUTLINE-FIRST SCAFFOLD\n"
            "- First chunk: produce a chapter-by-chapter outline (goal + 4–8 subtopics). End with: NEXT: [Begin Chapter 1].\n"
            "- Subsequent chunks: follow the outline; teach-before-use; keep narrative flow; short vignettes; quick checks.\n"
        ),
        "hammer": True,
        "continuation": {
            "mode": "anchor",
            "minChars": int(min_chars),
            "pushPasses": 1,
            "repeatWarn": True,
        },
        "io": {
            "output": "file",
            "outPath": out_path or f"./books/{slugify(subject)}.manual.en.md",
        },
        "max_chunks": int(max_chunks),
    }
    await run_recipe(rec, state)


async def run_recipe(rec: dict, state: Dict):
    """
    Args:
        rec: recipe dictionary
        state: dict containing shared state and functions
    """
    # Expected fields (all optional except task):
    # task, subject, styles[], style_file, hammer, continuation{}, io{}, custom_system_file, backend, model, max_chunks
    task = rec.get("task")
    subject = rec.get("subject")
    styles = rec.get("styles") or rec.get("style") or []
    style_file = rec.get("style_file")
    hammer = bool(rec.get("hammer", True))
    cont = rec.get("continuation", {}) or {}
    io = rec.get("io", {}) or {}
    custom_system_file = rec.get("custom_system_file")
    backend = rec.get("backend")
    model = rec.get("model")
    max_chunks = rec.get("max_chunks")
    out_path = io.get("outPath") or io.get("out") or None

    # Functions from state
    ok = state.get("ok", print)
    repo_render = state["repo_render"]
    _apply_style_overlays = state["_apply_style_overlays"]
    _handle_command = state["_handle_command"]
    set_system = state["set_system"]
    set_window = state["set_window"]
    ensure_dir = state["ensure_dir"]
    next_available_path = state["next_available_path"]
    autorun_loop = state["autorun_loop"]

    # backend/model switches
    if backend in ("bridge", "openrouter"):
        state["BACKEND"] = backend
        ok(f"Backend set via recipe: {backend}")
    if model:
        state["MODEL_ID"] = model
        ok(f"Model set via recipe: {model}")

    # configure continuation knobs
    if "mode" in cont:
        state["CONT_MODE"] = cont["mode"]
    if "anchorLen" in cont:
        state["CONT_ANCHOR_CHARS"] = int(cont["anchorLen"])
    if "minChars" in cont:
        state["OUTPUT_MIN_CHARS"] = int(cont["minChars"])
    if "pushPasses" in cont:
        state["OUTPUT_PUSH_MAX_PASSES"] = int(cont["pushPasses"])
    if "repeatWarn" in cont:
        state["REPEAT_WARN"] = bool(cont["repeatWarn"])

    # hammer (coverage anti-wrap)
    state["COVERAGE_HAMMER_ON"] = bool(hammer)

    # base system from task
    if task in (
        "book.zero2hero",
        "book.reference",
        "book.pop",
        "exam.cram",
        "book.nobs",
    ):
        sys_text = repo_render(task, subject=subject or "Subject")
    elif task == "book.bilingual":
        sys_text = repo_render(
            "book.bilingual", subject=subject or "Subject", lang=rec.get("lang", "")
        )
    elif task == "lossless.rewrite":
        from lma_templates import PROMPT_REPO

        sys_text = PROMPT_REPO["book.lossless.rewrite"]["system"]
    elif task == "translate":
        from lma_templates import PROMPT_REPO

        sys_text = PROMPT_REPO["translate"]["system"].replace(
            "{lang}", rec.get("lang", "")
        )
    elif task == "answer.chad":
        from lma_templates import CHAD_TEMPLATE

        sys_text = CHAD_TEMPLATE
    else:
        # default generic book/system
        from lma_templates import PROMPT_REPO

        sys_text = PROMPT_REPO.get(task, {}).get("system") or PROMPT_REPO[
            "book.zero2hero"
        ]["system"].replace("{subject}", subject or "Subject")

    # apply overlays
    sys_text = _apply_style_overlays(sys_text, styles, style_file)

    # custom system tail
    if custom_system_file and os.path.exists(custom_system_file):
        with open(custom_system_file, "r", encoding="utf-8") as f:
            tail = f.read()
        sys_text = sys_text.strip() + "\n\n" + tail

    # inline system text overlay
    if rec.get("system_text"):
        sys_text = sys_text.strip() + "\n\n" + rec["system_text"].strip()

    state["SAVE_SYSTEM_STACK"].append(state.get("SYSTEM_PROMPT", ""))
    set_system(sys_text.strip(), state)
    # run prelude commands (if any)
    for cmd in rec.get("prelude") or []:
        if isinstance(cmd, str) and cmd.strip():
            await _handle_command(cmd, state)
    if out_path:
        ensure_dir(os.path.dirname(out_path) or ".")
        state["AUTO_OUT"] = next_available_path(out_path)
    else:
        state["AUTO_OUT"] = None

    state["AUTO_ON"] = True
    state["AUTO_COUNT"] = 0
    state["LAST_NEXT_HINT"] = None
    state["AUTO_MAX"] = None if not max_chunks else int(max_chunks)
    ok(f"Recipe run started. Output → {state['AUTO_OUT'] or '(none)'}")
    if state.get("AUTO_TASK") and not state["AUTO_TASK"].done():
        state["AUTO_TASK"].cancel()
    state["AUTO_TASK"] = asyncio.create_task(autorun_loop(state))
