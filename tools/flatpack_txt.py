#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import glob
import hashlib
import io
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Tuple

# Optional redact
def _load_redact():
    try:
        from xsarena.core.redact import redact as _redact  # if running inside the project
        return _redact
    except Exception:
        import re
        patterns = [
            (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]"), r"\1=\"[REDACTED]\""),
            (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
            (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]"),
        ]
        def _fallback(text: str) -> str:
            out = text or ""
            for rx, repl in patterns:
                out = rx.sub(repl, out)
            return out
        return _fallback

REDACT = _load_redact()

DEFAULT_INCLUDE = [
    "README.md",
    "COMMANDS_REFERENCE.md",
    "pyproject.toml",
    "src/xsarena/**",
]
DEFAULT_EXCLUDE = [
    ".git/**", "venv/**", ".venv/**", "__pycache__/**", ".pytest_cache/**",
    ".mypy_cache/**", ".ruff_cache/**", ".cache/**", "*.pyc", "logs/**",
    ".xsarena/tmp/**", "*.egg-info/**", ".ipynb_checkpoints/**",
]
# XSArena-specific priority ordering (tune as needed)
PINNED_FIRST = [
    "README.md",
    "COMMANDS_REFERENCE.md",
    "pyproject.toml",
    "src/xsarena/cli/main.py",
    "src/xsarena/cli/registry.py",
    "src/xsarena/cli/context.py",
    "src/xsarena/core/prompt.py",
    "src/xsarena/core/prompt_runtime.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/v2_orchestrator/specs.py",
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/executor.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/jobs/store.py",
    "src/xsarena/core/config.py",
    "src/xsarena/core/state.py",
    "src/xsarena/bridge_v2/api_server.py",
]

def _posix(p: Path) -> str:
    try:
        return p.as_posix()
    except Exception:
        return str(p)

def _expand_includes(includes: Sequence[str]) -> Set[Path]:
    files: Set[Path] = set()
    for pattern in includes:
        if any(ch in pattern for ch in ["*", "?", "["]):
            for match in glob.glob(pattern, recursive=True):
                mp = Path(match)
                if mp.is_file():
                    files.add(mp.resolve())
                elif mp.is_dir():
                    for f in mp.rglob("*"):
                        if f.is_file():
                            files.add(f.resolve())
        else:
            p = Path(pattern)
            if p.is_file():
                files.add(p.resolve())
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        files.add(f.resolve())
    return files

def _is_excluded(path: str, exclude_patterns: Sequence[str]) -> bool:
    p = path.replace("\\", "/")
    for pat in exclude_patterns:
        if fnmatch.fnmatch(p, pat):
            return True
    return False

def _git_ls_files(args: List[str]) -> Set[Path]:
    try:
        cp = subprocess.run(["git"] + args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if cp.returncode != 0:
            return set()
        out = set()
        for line in (cp.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            p = Path(line)
            if p.exists() and p.is_file():
                out.add(p.resolve())
        return out
    except Exception:
        return set()

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

def _read_truncated(path: Path, max_bytes: int) -> Tuple[str, bool]:
    try:
        size = path.stat().st_size
        limit = max(0, max_bytes)
        if size <= limit:
            data = path.read_bytes()
            return data.decode("utf-8", errors="replace"), False
        else:
            data = path.read_bytes()[:limit]
            return data.decode("utf-8", errors="replace") + "\n--- TRUNCATED ---\n", True
    except Exception as e:
        return f"\n--- READ ERROR: {e} ---\n", False

def _language_tag(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".py": "python",
        ".md": "markdown",
        ".toml": "toml",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
    }.get(ext, "")

def flatten_txt(
    out_path: Path,
    include: Sequence[str],
    exclude: Sequence[str],
    max_bytes_per_file: int,
    total_max_bytes: int,
    use_git_tracked: bool,
    include_untracked: bool,
    redact: bool,
    add_repo_map: bool,
) -> Tuple[Path, List[str]]:
    notes: List[str] = []
    # Base file set
    if use_git_tracked:
        files = _git_ls_files(["ls-files"])
        if include_untracked:
            files |= _git_ls_files(["ls-files", "--others", "--exclude-standard"])
        if not files:
            notes.append("git: no files (or not a repo); falling back to globs")
            files = _expand_includes(include)
    else:
        files = _expand_includes(include)

    # Filter excludes
    base = Path(".").resolve()
    filtered = []
    for f in files:
        rel = _posix(f.relative_to(base)) if f.is_absolute() else _posix(f)
        if not _is_excluded(rel, exclude):
            filtered.append(f)

    # Priority order: pinned first, then rest by path
    pinned = []
    rest = []
    pinned_set = set(PINNED_FIRST)
    for f in filtered:
        rel = _posix(f.relative_to(base)) if f.is_absolute() else _posix(f)
        if rel in pinned_set:
            pinned.append(f)
        else:
            rest.append(f)
    rest.sort(key=lambda p: _posix(p.relative_to(base)) if p.is_absolute() else _posix(p))
    ordered = []
    # Add pinned in declared order if present
    for pth in PINNED_FIRST:
        p = base / pth
        if p.exists() and p.is_file():
            ordered.append(p.resolve())
    # Then add the rest (dedup)
    seen = {x for x in ordered}
    for f in rest:
        if f not in seen:
            ordered.append(f)
            seen.add(f)

    # Flatten to buffer with budget
    buf = io.StringIO()
    # Header with simple instructions for the chatbot
    buf.write("# Repo Flat Pack\n\n")
    buf.write("Instructions for assistant:\n")
    buf.write("- Treat '=== START FILE: path ===' boundaries as file delimiters.\n")
    buf.write("- Do not summarize early; ask for next files if needed.\n")
    buf.write("- Keep references by path for follow-ups.\n\n")

    # Optional repo map
    if add_repo_map:
        buf.write("## Repo Map (selected files)\n\n")
        for f in ordered[:200]:
            rel = _posix(f.relative_to(base)) if f.is_absolute() else _posix(f)
            size = f.stat().st_size if f.exists() else -1
            buf.write(f"- {rel}  ({size} bytes, sha256:{_sha256(f)[:10]})\n")
        buf.write("\n")

    # Content
    written = 0
    for f in ordered:
        if written >= total_max_bytes:
            notes.append("total budget reached; remaining files omitted")
            break
        rel = _posix(f.relative_to(base)) if f.is_absolute() else _posix(f)
        lang = _language_tag(f)
        header = f"=== START FILE: {rel} ===\n"
        footer = f"=== END FILE: {rel} ===\n\n"
        body, truncated = _read_truncated(f, max_bytes_per_file)
        if redact:
            try:
                body = REDACT(body)
            except Exception:
                pass
        section = []
        section.append(header)
        if lang:
            section.append(f"```{lang}\n")
        section.append(body)
        if lang:
            section.append("\n```")
        section.append("\n")
        section.append(footer)
        chunk = "".join(section)
        buf.write(chunk)
        written += len(chunk.encode("utf-8"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(buf.getvalue(), encoding="utf-8")
    return out_path, notes

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Flatten a repo into a single LLM-friendly .txt file.")
    ap.add_argument("--out", "-o", default="repo_flat.txt")
    ap.add_argument("--include", "-I", action="append", default=None, help="Glob to include (repeatable)")
    ap.add_argument("--exclude", "-X", action="append", default=None, help="Glob to exclude (repeatable)")
    ap.add_argument("--max-per-file", type=int, default=220_000, help="Max bytes per file")
    ap.add_argument("--total-max", type=int, default=5_000_000, help="Total max bytes")
    ap.add_argument("--git-tracked", action="store_true", help="Use git ls-files as baseline")
    ap.add_argument("--git-include-untracked", action="store_true", help="Include git untracked files")
    ap.add_argument("--no-redact", action="store_true", help="Disable redaction")
    ap.add_argument("--no-repo-map", action="store_true", help="Omit repo map header")
    ns = ap.parse_args(argv)

    include = ns.include or DEFAULT_INCLUDE
    exclude = ns.exclude or DEFAULT_EXCLUDE
    redact = not ns.no_redact
    add_map = not ns.no_repo_map

    out, notes = flatten_txt(
        out_path=Path(ns.out),
        include=include,
        exclude=exclude,
        max_bytes_per_file=ns.max_per_file,
        total_max_bytes=ns.total_max,
        use_git_tracked=bool(ns.git_tracked),
        include_untracked=bool(ns.git_include_untracked),
        redact=redact,
        add_repo_map=add_map,
    )
    for n in notes:
        print(f"[note] {n}")
    print(f"[flatpack] wrote → {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())