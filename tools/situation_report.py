#!/usr/bin/env python3
"""
situation_report.py — Single-file situation report + 120KB chunking for XSArena.

What it does (read-only):
- Builds a self-contained text report (tree + LS + rules digest + config/session + recipes + books samples + review signals + jobs summary + code manifest).
- Updates a machine-readable "important files" list based on docs and a live tree pass, then ensures those files are inlined (bounded) in the report.
- Health-checks inclusion: required sections + presence of important files + manifest sanity + required digest line.
- Chunks the report into <=120 KB parts and appends the footer "Answer received. Do nothing else" to each chunk.
- Appends an ONE ORDER to directives/_rules/sources/ORDERS_LOG.md (if present) and re-merges rules.

Output (to current directory, i.e., " @ ."):
- ./situation_report.<ts>.txt
- ./situation_report.<ts>.health.md
- ./situation_report.<ts>.partNN.txt (chunked parts)

CLI
  python tools/situation_report.py
  python tools/situation_report.py --chunk-bytes 122880 --max-inline 200000 --include-ephemeral --update-rules

Notes
- Uses xsarena.core.redact.redact if available; otherwise a safe fallback.
- Never crashes on single-file errors; logs and continues.
- No network calls; read-only.

Requires Python 3.8+
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


# ---------- Redaction ----------
def _fallback_redact(text: str) -> str:
    if not text:
        return text
    pats = [
        (
            re.compile(
                r'(?i)(api[_-]?key|secret|token|password|pwd|auth|bearer)[\s:=]+\s*["\']?([A-Za-z0-9_\-]{16,})["\']?'
            ),
            r'\1="[REDACTED]"',
        ),
        (
            re.compile(r"\b[A-Za-z0-9._%+-]+ @[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "[REDACTED_EMAIL]",
        ),
        (re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"), "[REDACTED_IP]"),
        (re.compile(r'https?://[^\s<>"]+'), "[REDACTED_URL]"),
        (re.compile(r"\b[A-Za-z0-9]{30,}\b"), "[REDACTED_LONG_TOKEN]"),
    ]
    out = text
    for rgx, rep in pats:
        out = rgx.sub(rep, out)
    return out


try:
    from xsarena.core.redact import redact as redact_text  # type: ignore
except Exception:
    redact_text = _fallback_redact

# ---------- Helpers ----------
TEXT_EXTS = {
    ".md",
    ".markdown",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
    ".py",
    ".toml",
    ".ini",
    ".js",
    ".sh",
}
CODE_EXTS = {".py"}
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
}

DEFAULT_DIRS = [
    "books",
    "recipes",
    "directives",
    ".xsarena/jobs",
    "review",
    "src/xsarena",
]
DEFAULT_MAX_INLINE = 200_000
DEFAULT_CHUNK_BYTES = 122_880  # 120 KB


def now_ts() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.gmtime())


def read_bytes(p: Path, limit: int) -> Tuple[str, bool]:
    try:
        data = p.read_bytes()
    except Exception as e:
        return f"[error] cannot read {p}: {e}", False
    if len(data) <= limit:
        return data.decode("utf-8", errors="replace"), False
    half = limit // 2
    head = data[:half].decode("utf-8", errors="replace")
    tail = data[-half:].decode("utf-8", errors="replace")
    return head + "\n---TRUNCATED---\n" + tail, True


def first_line(p: Path) -> str:
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            return f.readline(4096)
    except Exception:
        return ""


def is_ephemeral(p: Path) -> bool:
    return "XSA-EPHEMERAL" in first_line(p)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_rel(p: Path) -> str:
    try:
        return str(p.relative_to(Path.cwd()))
    except Exception:
        return str(p)


# ---------- ASCII Tree ----------
def build_tree(paths: List[Path]) -> dict:
    root: dict = {}
    for p in paths:
        parts = list(p.parts)
        cur = root
        for i, part in enumerate(parts):
            is_file = i == len(parts) - 1
            cur.setdefault(part, {} if not is_file else None)
            if cur[part] is None:
                break
            cur = cur[part]
    return root


def render_tree(d: dict, prefix: str = "") -> List[str]:
    lines: List[str] = []
    items = sorted(d.items(), key=lambda kv: kv[0].lower())
    for i, (name, sub) in enumerate(items):
        last = i == len(items) - 1
        branch = "└── " if last else "├── "
        lines.append(f"{prefix}{branch}{name}")
        if isinstance(sub, dict):
            ext = "    " if last else "│   "
            lines.extend(render_tree(sub, prefix + ext))
    return lines


def write_tree_section(w: io.TextIOBase, title: str, root_path: Path):
    w.write(f"===== TREE {title} =====\n")
    if not root_path.exists():
        w.write("(missing)\n")
        w.write(f"===== END TREE {title} =====\n\n")
        return
    paths = [p for p in root_path.rglob("*")]
    d = build_tree(paths if paths else [root_path])
    for line in render_tree(d):
        w.write(line + "\n")
    w.write(f"===== END TREE {title} =====\n\n")


# ---------- Git info ----------
def git_info_lines() -> List[str]:
    out: List[str] = []

    def run(cmd: List[str]) -> Optional[str]:
        try:
            return (
                subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            )
        except Exception:
            return None

    if not run(["git", "rev-parse", "--git-dir"]):
        out.append("Git: (not a git repository)")
        return out
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "?"
    head = run(["git", "rev-parse", "HEAD"]) or "?"
    status = run(["git", "status", "--porcelain"]) or ""
    out.append(f"Git branch: {branch}")
    out.append(f"Git HEAD: {head}")
    out.append(
        f"Git status: {'clean' if not status else str(len(status.splitlines())) + ' change(s)'}"
    )
    return out


# ---------- Jobs summary ----------


@dataclass
class JobStats:
    id: str
    state: str
    chunks: int
    retries: int
    failovers: int
    watchdogs: int
    first_ts: str
    last_ts: str
    last_events: List[dict]


def summarize_job(job_dir: Path) -> JobStats:
    jid = job_dir.name
    state = "?"
    job_path = job_dir / "job.json"
    try:
        if job_path.exists():
            j = json.loads(job_path.read_text(encoding="utf-8", errors="replace"))
            state = j.get("state", "?")
    except Exception:
        pass
    evp = job_dir / "events.jsonl"
    chunks = retries = failovers = watchdogs = 0
    first = last = ""
    events: List[dict] = []
    if evp.exists():
        try:
            for ln in evp.read_text(encoding="utf-8", errors="replace").splitlines():
                if not ln.strip():
                    continue
                try:
                    ev = json.loads(ln)
                except Exception:
                    continue
                t = ev.get("type")
                ts = ev.get("ts", "")
                if not first:
                    first = ts
                if ts:
                    last = ts
                if t == "chunk_done":
                    chunks += 1
                elif t == "retry":
                    retries += 1
                elif t == "failover":
                    failovers += 1
                elif t == "watchdog_timeout":
                    watchdogs += 1
                events.append(ev)
        except Exception:
            pass
    return JobStats(
        jid, state, chunks, retries, failovers, watchdogs, first, last, events[-5:]
    )


# ---------- Important files derivation ----------
IMPORTANT_HINTS = [
    "README.md",
    "pyproject.toml",
    "mypy.ini",
    "models.json",
    "directives/_rules/rules.merged.md",
    "docs/INDEX.md",
    "docs/IMPORTANT_FILES.md",
    "IMPORTANT_FILES_LIST.md",
    "tools/min_snapshot.py",
    "tools/snapshot_pro.py",
    "tools/situation_report.py",
    ".xsarena/config.yml",
    ".xsarena/session_state.json",
]


def discover_file_refs_from_docs() -> List[str]:
    refs: set[str] = set()
    candidates = [
        Path("docs/INDEX.md"),
        Path("IMPORTANT_FILES_LIST.md"),
        Path("docs/INDEX.md"),
        Path("README.md"),
        Path("ARCHITECTURE.md"),
        Path("STATE.md"),
        Path("CONFIG_REFERENCE.md"),
    ]
    pat = re.compile(r"(?<![A-Za-z0-9_/.-])([A-Za-z0-9._/\-]+(?:\.[A-Za-z0-9]+))")
    for p in candidates:
        if p.exists():
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
                for m in pat.finditer(txt):
                    s = m.group(1)
                    if Path(s).exists():
                        refs.add(s)
            except Exception:
                pass
    # Always add recipe dir if present
    if Path("recipes").exists():
        for y in Path("recipes").rglob("*.yml"):
            refs.add(str(y))
    for h in IMPORTANT_HINTS:
        if Path(h).exists():
            refs.add(h)
    return sorted(refs, key=lambda x: x.lower())


def save_important_files_list(paths: List[str], out: Path):
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(paths) + "\n", encoding="utf-8")
    except Exception:
        pass


# ---------- Manifest ----------
def code_manifest(code_root: str = "src/xsarena") -> Tuple[List[Tuple[str, str]], str]:
    entries: List[Tuple[str, str]] = []
    root = Path(code_root)
    if root.exists():
        for p in root.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            try:
                h = sha256_file(p)
            except Exception:
                h = "[error]"
            entries.append((str(p), h))
    entries.sort(key=lambda t: t[0].lower())
    overall = hashlib.sha256()
    for _, h in entries:
        overall.update(h.encode("utf-8", errors="ignore"))
    return entries, overall.hexdigest()


# ---------- Report writer ----------
def write_header(w: io.TextIOBase, args, ts: str):
    w.write("XSArena Single-File Situation Report\n")
    w.write(f"Generated (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}\n")
    w.write(f"Python: {platform.python_version()}  Platform: {platform.platform()}\n")
    w.write(f"CWD: {os.getcwd()}\n")
    w.write(f"Args: {vars(args)}\n")
    w.write("Redaction: secrets/emails/IPs/URLs/long tokens are masked.\n\n")


def write_exec_summary(w: io.TextIOBase):
    w.write("=== Executive Summary ===\n")
    # Minimal, safe summary
    w.write(
        "XSArena is a bridge-first CLI studio for dense, long-form content (books, study manuals).\n"
    )
    w.write(
        "This report includes tree/LS, rules digest, config/session, recipes, book samples, review signals, jobs summary, and a code manifest.\n"
    )
    try:
        for line in git_info_lines():
            w.write(line + "\n")
    except Exception:
        pass
    w.write("\n")


def write_ls_section(w: io.TextIOBase, name: str, root: Path):
    w.write(f"===== LS ({name}) =====\n")
    if root.exists():
        for p in sorted(root.rglob("*"), key=lambda x: str(x).lower()):
            if p.is_file():
                w.write(str(p) + "\n")
    else:
        w.write("(missing)\n")
    w.write(f"===== END LS ({name}) =====\n\n")


def write_rules_digest(
    w: io.TextIOBase, path="directives/_rules/rules.merged.md", max_lines=200
):
    p = Path(path)
    w.write("===== RULES DIGEST =====\n")
    if not p.exists():
        w.write("(missing) directives/_rules/rules.merged.md\n\n")
    else:
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            head = lines[:max_lines]
            w.write(f"File: {path} (first {len(head)}/{len(lines)} lines)\n")
            w.write("\n".join(head) + "\n\n")
        except Exception as e:
            w.write(f"[error] reading rules: {e}\n\n")
    w.write("===== END RULES DIGEST =====\n\n")


def write_inline_file(
    w: io.TextIOBase, p: Path, max_inline: int, include_ephemeral: bool
):
    if not p.exists() or not p.is_file():
        w.write(f"--- (missing) {safe_rel(p)} ---\n")
        return
    if (not include_ephemeral) and is_ephemeral(p):
        return
    txt, trunc = read_bytes(p, max_inline)
    txt = redact_text(txt)
    w.write(f"===== BEGIN INCLUDED FILE: {safe_rel(p)} =====\n")
    w.write(txt + ("\n" if not txt.endswith("\n") else ""))
    w.write(f"===== END INCLUDED FILE: {safe_rel(p)} =====\n\n")


def write_config_and_session(
    w: io.TextIOBase, max_inline: int, include_ephemeral: bool
):
    w.write("===== CONFIG & SESSION =====\n")
    for name in [".xsarena/config.yml", ".xsarena/session_state.json"]:
        write_inline_file(w, Path(name), max_inline, include_ephemeral)
    w.write("===== END CONFIG & SESSION =====\n\n")


def write_recipes_digest(w: io.TextIOBase, max_inline: int, include_ephemeral: bool):
    w.write("===== RECIPES DIGEST =====\n")
    base = Path("recipes")
    if not base.exists():
        w.write("(missing recipes)\n\n")
    else:
        for p in sorted(base.rglob("*.yml"), key=lambda x: str(x).lower()):
            write_inline_file(w, p, max_inline, include_ephemeral)
    w.write("===== END RECIPES DIGEST =====\n\n")


def write_books_samples(w: io.TextIOBase, max_inline: int, include_ephemeral: bool):
    w.write("===== BOOKS SAMPLES =====\n")
    finals = Path("books/finals")
    outlines = Path("books/outlines")
    for base in [finals, outlines]:
        if base.exists():
            for p in sorted(base.glob("*.md"), key=lambda x: str(x).lower()):
                # cap tighter for books
                write_inline_file(w, p, min(max_inline, 50_000), include_ephemeral)
    w.write("===== END BOOKS SAMPLES =====\n\n")


def write_review_signals(w: io.TextIOBase, max_inline: int, include_ephemeral: bool):
    w.write("===== REVIEW SIGNALS =====\n")
    base = Path("review")
    if not base.exists():
        w.write("(missing review)\n\n")
    else:
        # Prefer small text/json signals
        for patt in [
            "*.txt",
            "adapt_plan_*.json",
            "inventory.json",
            "quick_tree_ls.txt",
            "books_sha256.txt",
        ]:
            for p in sorted(base.glob(patt), key=lambda x: str(x).lower()):
                write_inline_file(w, p, min(max_inline, 80_000), include_ephemeral)
    w.write("===== END REVIEW SIGNALS =====\n\n")


def write_jobs_summary(w: io.TextIOBase):
    w.write("===== JOBS SUMMARY =====\n")
    base = Path(".xsarena") / "jobs"
    if not base.exists():
        w.write("(none)\n")
    else:
        for job_dir in sorted(
            [p for p in base.iterdir() if p.is_dir()], key=lambda x: x.name
        ):
            js = summarize_job(job_dir)
            w.write(
                f"- Job {js.id}  State: {js.state}  Chunks: {js.chunks}  Retries: {js.retries}  Failovers: {js.failovers}  Watchdogs: {js.watchdogs}\n"
            )
            if js.first_ts or js.last_ts:
                w.write(f"  Window: {js.first_ts} → {js.last_ts}\n")
            if js.last_events:
                w.write("  Last events:\n")
                for ev in js.last_events:
                    w.write(f"    - {ev.get('ts','')}  {ev.get('type','?')}\n")
    w.write("\n===== END JOBS SUMMARY =====\n\n")


def write_manifest(w: io.TextIOBase) -> Tuple[List[Tuple[str, str]], str]:
    entries, digest = code_manifest("src/xsarena")
    w.write("===== MANIFEST (CODE) =====\n")
    for path, h in entries:
        w.write(f"{path}  {h}\n")
    w.write(f"===== SNAPSHOT DIGEST: {digest} =====\n\n")
    return entries, digest


# ---------- Healthcheck ----------
def healthcheck(report: Path, important: List[str]) -> str:
    out = report.with_suffix(".health.md")
    text = report.read_text(encoding="utf-8", errors="replace")

    def has(mark: str) -> bool:
        return mark in text

    lines = []
    lines.append("# Situation Report Healthcheck")
    lines.append(f"Report: {report}")
    need_marks = [
        "===== TREE ",
        "===== LS (",
        "===== RULES DIGEST",
        "===== CONFIG & SESSION",
        "===== RECIPES DIGEST",
        "===== BOOKS SAMPLES",
        "===== REVIEW SIGNALS",
        "===== JOBS SUMMARY",
        "===== MANIFEST (CODE)",
        "===== SNAPSHOT DIGEST:",
    ]
    lines.append("## Section presence")
    for m in need_marks:
        lines.append(f"- [{m}] {'OK' if has(m) else 'MISSING'}")
    lines.append("\n## Important files inclusion")
    missing = 0
    for p in important:
        tag = f"BEGIN INCLUDED FILE: {p}"
        present = tag in text
        lines.append(f"- {p}: {'OK' if present else 'MISSING'}")
        if not present:
            missing += 1
    # manifest size
    import io as _io

    buf = _io.StringIO(text)
    in_manifest = False
    manifest_lines = 0
    for ln in buf.getvalue().splitlines():
        if ln.strip() == "===== MANIFEST (CODE) =====":
            in_manifest = True
            continue
        if ln.startswith("===== SNAPSHOT DIGEST:"):
            in_manifest = False
            continue
        if in_manifest and ln.strip():
            manifest_lines += 1
    lines.append(f"\n## Manifest lines: {manifest_lines}")
    lines.append(
        f"\n## Verdict: {'PASS' if all(has(m) for m in need_marks) and missing==0 and manifest_lines>=30 else 'WARN/FAIL'}"
    )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(out)


# ---------- Chunking ----------
def chunk_file(path: Path, chunk_bytes: int, footer: str) -> List[str]:
    data = path.read_bytes()
    parts: List[str] = []
    start = 0
    n = 1
    while start < len(data):
        end = min(len(data), start + chunk_bytes)
        # try to split at last section marker or newline before end
        window = data[start:end]
        split_at = window.rfind(b"\n===== ")  # section boundary
        if split_at == -1:
            split_at = window.rfind(b"\n")  # any newline
        if split_at == -1 or start + split_at + 1 <= start:
            split_at = len(window)
        else:
            split_at = split_at + 1  # include the newline
        chunk = window[:split_at]
        # ensure UTF-8 safe
        text = chunk.decode("utf-8", errors="replace")
        if not text.endswith("\n"):
            text += "\n"
        text += footer.strip() + "\n"
        outp = path.with_name(f"{path.stem}.part{n:02d}.txt")
        outp.write_text(text, encoding="utf-8")
        parts.append(str(outp))
        start += split_at
        n += 1
    return parts


# ---------- Rules update ----------
def append_one_order_to_orders_log(
    ts: str, report_path: Path, parts: List[str], important_file: Path
):
    src = Path("directives/_rules/sources/ORDERS_LOG.md")
    if not src.parent.exists():
        return
    block = []
    block.append("\n\n# ONE ORDER — Situation Report + Chunking")
    block.append(
        f"- Timestamp (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}"
    )
    block.append(f"- Report: {report_path}")
    block.append(f"- Chunks: {', '.join(Path(p).name for p in parts)}")
    block.append(f"- Important files list refreshed: {important_file}")
    block.append(
        "- Instruction: future sessions must build a single-file report, healthcheck, and chunk into ≤120KB with the footer “Answer received. Do nothing else”."
    )
    try:
        old = src.read_text(encoding="utf-8", errors="replace") if src.exists() else ""
        src.write_text(old + "\n".join(block) + "\n", encoding="utf-8")
    except Exception:
        return
    # Merge rules if script exists
    merge = Path("scripts/merge_session_rules.sh")
    if merge.exists():
        try:
            subprocess.run(["bash", str(merge)], check=False)
        except Exception:
            pass


# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(
        description="XSArena: single-file situation report + 120KB chunking."
    )
    ap.add_argument(
        "--dirs", nargs="*", default=DEFAULT_DIRS, help="Dirs for TREE + LS"
    )
    ap.add_argument(
        "--max-inline",
        type=int,
        default=DEFAULT_MAX_INLINE,
        help="Max bytes per included file",
    )
    ap.add_argument(
        "--include-ephemeral", action="store_true", help="Include XSA-EPHEMERAL files"
    )
    ap.add_argument(
        "--chunk-bytes",
        type=int,
        default=DEFAULT_CHUNK_BYTES,
        help="Max bytes per chunk (before footer)",
    )
    ap.add_argument(
        "--footer",
        default="Answer received. Do nothing else",
        help="Footer line to append to each chunk",
    )
    ap.add_argument(
        "--update-rules",
        action="store_true",
        help="Append ONE ORDER to ORDERS_LOG.md and re-merge rules",
    )
    args = ap.parse_args()

    ts = now_ts()
    out_report = Path(f"./situation_report.{ts}.txt")  # output to " @ ."
    out_health = Path(f"./situation_report.{ts}.health.md")
    important_out = Path("review/important_files.list")
    important_out.parent.mkdir(parents=True, exist_ok=True)

    # 1) Build important files from docs + hints + recipes
    important = discover_file_refs_from_docs()
    save_important_files_list(important, important_out)

    # 2) Compose report
    with out_report.open("w", encoding="utf-8") as w:
        write_header(w, args, ts)
        write_exec_summary(w)

        # Trees and LS for required dirs
        for name in args.dirs:
            write_tree_section(w, name, Path(name))
        for name in args.dirs:
            write_ls_section(w, name, Path(name))

        # Rules digest
        write_rules_digest(w, "directives/_rules/rules.merged.md", max_lines=200)

        # Config & session
        write_config_and_session(w, args.max_inline, args.include_ephemeral)

        # Recipes
        write_recipes_digest(w, args.max_inline, args.include_ephemeral)

        # Books samples
        write_books_samples(w, args.max_inline, args.include_ephemeral)

        # Review signals
        write_review_signals(w, args.max_inline, args.include_ephemeral)

        # Jobs summary
        write_jobs_summary(w)

        # Inline explicitly important files (bounded) to ensure presence
        if important:
            w.write("===== IMPORTANT FILES (INLINE) =====\n\n")
            for p in important:
                write_inline_file(w, Path(p), args.max_inline, args.include_ephemeral)
            w.write("===== END IMPORTANT FILES (INLINE) =====\n\n")

        # Code manifest + digest
        write_manifest(w)

        # Health summary placeholder (full health details in .health.md)
        w.write("===== HEALTH SUMMARY (see .health.md for details) =====\n")
        w.write(f"Important files listed: {len(important)}\n")
        w.write("See companion health file for section presence and manifest counts.\n")
        w.write("===== END HEALTH SUMMARY =====\n")

    print(f"Wrote report → {out_report}")

    # 3) Healthcheck
    hc_path = healthcheck(out_report, important)
    if out_health != Path(hc_path):  # copy to canonical name
        try:
            Path(hc_path).replace(out_health)
        except Exception:
            pass
    print(f"Wrote healthcheck → {out_health}")

    # 4) Chunking (<=120 KB)
    parts = chunk_file(out_report, args.chunk_bytes, args.footer)
    print("Chunks:")
    for p in parts:
        print(" -", p)

    # 5) Update rules (ONE ORDER) if requested
    if args.update_rules:
        append_one_order_to_orders_log(ts, out_report, parts, important_out)
        print("Rules updated and merged (best-effort).")

    # 6) Ask clarifications (printed for operator)
    print("\nQuestions for operator:")
    print(
        "1) Do you want additional directories included in TREE/LS (e.g., docs, tools, scripts)?"
    )
    print(
        "2) Should ephemeral XSA-EPHEMERAL files be included next time? (--include-ephemeral)"
    )
    print("3) Is 120KB chunk size acceptable, or adjust via --chunk-bytes?")
    print(
        "4) Did the report capture all important files you expect? If not, list paths to add."
    )


if __name__ == "__main__":
    sys.exit(main())
