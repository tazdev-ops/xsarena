#!/usr/bin/env python3
"""
XSArena Snapshot Utility

- Configuration-driven via .snapshot.toml with modes: minimal, standard, full
- Whitelist-first includes; excludes remove candidates
- Context sections: git, jobs, code manifest
- Redaction: uses xsarena.core.redact or a safe fallback
- Output: text (concatenated) or zip (redacted copies + manifest)

Usage:
  python tools/snapshot.py                # uses default_mode from .snapshot.toml
  python tools/snapshot.py --mode standard
  python tools/snapshot.py --mode full --zip snapshot.zip
  python tools/snapshot.py --dry-run --mode minimal
  python tools/snapshot.py out.txt --include 'directives/manifest.yml'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path.cwd()

# ----- Redaction -----
try:
    from xsarena.core.redact import redact as redact_text  # type: ignore
except Exception:

    def redact_text(text: str) -> str:
        pats = [
            # Generic secrets like API keys / tokens / passwords
            (
                re.compile(
                    r'(?i)\b(api[_-]?key|secret|token|password|pwd|auth|bearer|access[_-]?key|refresh[_-]?token)\b[\s:=]+["\']?([A-Za-z0-9._\-]{12,})["\']?'
                ),
                r'\1="[REDACTED]"',
            ),
            # .env style KEY=verylongvalue
            (
                re.compile(r'(?m)^\s*([A-Z0-9_]{3,})\s*=\s*(["\']?)[^\s#]{12,}\2\s*$'),
                r"\1=[REDACTED]",
            ),
            # JWT
            (
                re.compile(
                    r"\beyJ[0-9A-Za-z_\-]{10,}\.[0-9A-Za-z_\-]{10,}\.[0-9A-Za-z_\-]{10,}\b"
                ),
                "[REDACTED_JWT]",
            ),
            # Emails
            (
                re.compile(r"\b[A-Za-z0-9._%+-]+ @[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
                "[REDACTED_EMAIL]",
            ),
            # IPv4
            (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]"),
        ]
        for rgx, repl in pats:
            text = rgx.sub(repl, text)
        return text


# ----- Helpers -----


def ts_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel_posix(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def is_binary_sample(b: bytes) -> bool:
    if not b:
        return False
    if 0 in b:
        return True
    text_chars = bytes(range(32, 127)) + b"\n\r\t\b\f"
    non_text = sum(ch not in text_chars for ch in b)
    return non_text / max(1, len(b)) > 0.30


def safe_read_bytes(p: Path, cap: int) -> tuple[bytes, bool]:
    try:
        data = p.read_bytes()
    except Exception:
        return b"", False
    truncated = False
    if len(data) > cap:
        data = data[:cap]
        truncated = True
    return data, truncated


def render_tree(files: list[Path]) -> str:
    tree = {}
    for f in files:
        parts = rel_posix(f).split("/")
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    def walk(node: dict, prefix="") -> list[str]:
        lines = []
        names = sorted(node.keys())
        for i, name in enumerate(names):
            last = i == len(names) - 1
            conn = "└── " if last else "├── "
            lines.append(f"{prefix}{conn}{name}")
            if node[name]:
                ext = "    " if last else "│   "
                lines.extend(walk(node[name], prefix + ext))
        return lines

    return ".\n" + "\n".join(walk(tree))


def get_git_info() -> str:
    if not (ROOT / ".git").exists():
        return "Git: (Not a git repository)\n"
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).strip()
        status_summary = (
            f"{len(status.splitlines())} changed file(s)" if status else "clean"
        )
        return f"Git Branch: {branch}\nGit Commit: {commit}\nGit Status: {status_summary}\n"
    except Exception as e:
        return f"Git: (Error gathering info: {e})\n"


def get_jobs_summary() -> str:
    jobs_dir = ROOT / ".xsarena" / "jobs"
    if not jobs_dir.exists():
        return "Jobs: (No jobs directory found)\n"
    summaries = []
    job_dirs = sorted(
        [p for p in jobs_dir.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for job_dir in job_dirs[:5]:
        job_file = job_dir / "job.json"
        events_file = job_dir / "events.jsonl"
        if not job_file.exists():
            continue
        try:
            job = json.loads(job_file.read_text("utf-8", errors="replace"))
            state = job.get("state", "UNKNOWN")
            name = job.get("name", job_dir.name)
            chunks = 0
            retries = 0
            if events_file.exists():
                for line in events_file.read_text(
                    "utf-8", errors="replace"
                ).splitlines():
                    if '"type": "chunk_done"' in line:
                        chunks += 1
                    if '"type": "retry"' in line:
                        retries += 1
            summaries.append(
                f"  - {job_dir.name[:8]}: {state:<10} | Chunks: {chunks:<3} | Retries: {retries:<2} | {name}"
            )
        except Exception:
            summaries.append(f"  - {job_dir.name[:8]}: (Error parsing job data)")
    return "Recent Jobs:\n" + "\n".join(summaries) + "\n"


def get_code_manifest() -> str:
    src_root = ROOT / "src"
    if not src_root.exists():
        return "Code Manifest: (src/ directory not found)\n"
    lines = []
    for py in sorted(src_root.rglob("*.py")):
        try:
            h = sha256_bytes(py.read_bytes())
            lines.append(f"{h[:12]}  {py.relative_to(ROOT)}")
        except Exception:
            lines.append(f"{'[ERROR]':<12}  {py.relative_to(ROOT)}")
    return "Code Manifest (src/**/*.py):\n" + "\n".join(lines) + "\n"


# ----- Config (.snapshot.toml) -----
try:
    import tomllib  # Python 3.11+
except Exception:
    tomllib = None


@dataclass
class ModeConfig:
    include: list[str]
    exclude: list[str]


@dataclass
class SnapshotConfig:
    default_mode: str
    max_size: int
    redact: bool
    context_git: bool
    context_jobs: bool
    context_manifest: bool
    modes: dict[str, ModeConfig]


def load_config() -> SnapshotConfig:
    # Defaults align with your spec (minimal covers src/xsarena + key root files)
    default_modes = {
        "minimal": ModeConfig(
            include=[
                ".snapshot.toml",
                "README.md",
                "COMMANDS_REFERENCE.md",
                "pyproject.toml",
                "src/xsarena/**",
            ],
            exclude=[
                ".git/**",
                "venv/**",
                ".venv/**",
                "__pycache__/**",
                ".pytest_cache/**",
                ".mypy_cache/**",
                ".ruff_cache/**",
                ".cache/**",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                "*.o",
                "*.a",
                "*.so",
                "*.dll",
                "*.dylib",
                "*.log",
                "logs/**",
                ".xsarena/**",
                "*.egg-info/**",
                ".ipynb_checkpoints/**",
            ],
        ),
        "standard": ModeConfig(
            include=[
                ".snapshot.toml",
                "README.md",
                "COMMANDS_REFERENCE.md",
                "pyproject.toml",
                "src/xsarena/**",
                "docs/**",
                "data/schemas/**",
                "directives/manifest.yml",
                "directives/profiles/presets.yml",
                "directives/modes.catalog.json",
            ],
            exclude=[
                ".git/**",
                "venv/**",
                ".venv/**",
                "__pycache__/**",
                ".pytest_cache/**",
                ".mypy_cache/**",
                ".ruff_cache/**",
                ".cache/**",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                "*.o",
                "*.a",
                "*.so",
                "*.dll",
                "*.dylib",
                "*.log",
                "logs/**",
                ".xsarena/**",
                "*.egg-info/**",
                ".ipynb_checkpoints/**",
                "books/**",
                "review/**",
                "recipes/**",
                "tests/**",
                "packaging/**",
                "pipelines/**",
                "examples/**",
                "directives/_preview/**",
                "directives/_mixer/**",
                "directives/quickref/**",
                "directives/roles/**",
                "directives/prompt/**",
                "directives/style/**",
            ],
        ),
        "full": ModeConfig(
            include=[
                "README.md",
                "COMMANDS_REFERENCE.md",
                "pyproject.toml",
                "src/**",
                "docs/**",
                "directives/**",
                "data/**",
                "recipes/**",
                "tests/**",
                "tools/**",
                "scripts/**",
                "books/**",
                "packaging/**",
                "pipelines/**",
                "examples/**",
                "review/**",
            ],
            exclude=[
                ".git/**",
                "venv/**",
                ".venv/**",
                "__pycache__/**",
                ".pytest_cache/**",
                ".mypy_cache/**",
                ".ruff_cache/**",
                ".cache/**",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                "*.o",
                "*.a",
                "*.so",
                "*.dll",
                "*.dylib",
                "*.log",
                "logs/**",
                "*.egg-info/**",
                ".ipynb_checkpoints/**",
            ],
        ),
    }

    cfg = SnapshotConfig(
        default_mode="minimal",
        max_size=200 * 1024,
        redact=True,
        context_git=True,
        context_jobs=True,
        context_manifest=True,
        modes=default_modes,
    )

    tpath = ROOT / ".snapshot.toml"
    if tpath.exists() and tomllib:
        try:
            data = tomllib.loads(tpath.read_text("utf-8", errors="replace"))
            cfg.default_mode = data.get("default_mode", cfg.default_mode)
            cfg.max_size = int(data.get("max_size", cfg.max_size))
            cfg.redact = bool(data.get("redact", cfg.redact))
            ctx = data.get("context", {})
            cfg.context_git = bool(ctx.get("git", cfg.context_git))
            cfg.context_jobs = bool(ctx.get("jobs", cfg.context_jobs))
            cfg.context_manifest = bool(ctx.get("manifest", cfg.context_manifest))

            modes = data.get("modes", {})
            for name, sec in modes.items():
                inc = sec.get("include", [])
                exc = sec.get("exclude", [])
                if isinstance(inc, list) and isinstance(exc, list):
                    cfg.modes[name] = ModeConfig(include=inc, exclude=exc)
        except Exception:
            pass

    return cfg


# ----- Collection -----


def _expand_patterns(patterns: list[str]) -> set[Path]:
    out: set[Path] = set()
    for pat in patterns:
        for p in ROOT.glob(pat):
            if p.is_file():
                out.add(p)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        out.add(f)
    return out


def _matches(rel: str, pattern: str) -> bool:
    return PurePosixPath(rel).match(pattern.lstrip("/"))


def _apply_excludes(files: set[Path], exclude: list[str]) -> list[Path]:
    kept = []
    for p in files:
        rel = rel_posix(p)
        if any(_matches(rel, pat) for pat in exclude):
            continue
        kept.append(p)
    return sorted(kept)


def collect_files(includes: list[str], excludes: list[str]) -> list[Path]:
    candidates = _expand_patterns(includes)
    return _apply_excludes(candidates, excludes)


# ----- Main -----


def main():
    ap = argparse.ArgumentParser(description="XSArena Snapshot")
    ap.add_argument(
        "output",
        nargs="?",
        default="xsa_snapshot.txt",
        help="Output path (.txt or .zip).",
    )
    ap.add_argument(
        "--mode",
        choices=["minimal", "standard", "full"],
        help="Mode from .snapshot.toml (default: config.default_mode).",
    )
    ap.add_argument(
        "--include", action="append", default=[], help="Extra include glob(s)."
    )
    ap.add_argument(
        "--exclude", action="append", default=[], help="Extra exclude glob(s)."
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="List files only; do not write snapshot."
    )
    ap.add_argument(
        "--zip",
        action="store_true",
        help="Write a zip archive with redacted copies + snapshot_manifest.txt.",
    )
    ap.add_argument(
        "--max-size",
        type=int,
        help="Override max bytes per file (default from config).",
    )
    ap.add_argument(
        "--no-git", action="store_true", help="Disable git status in context."
    )
    ap.add_argument(
        "--no-jobs", action="store_true", help="Disable jobs summary in context."
    )
    ap.add_argument(
        "--no-manifest", action="store_true", help="Disable code manifest in context."
    )
    ap.add_argument(
        "--no-redact", action="store_true", help="Do not redact file contents."
    )
    ap.add_argument(
        "-q", "--silent", action="store_true", help="Suppress progress messages."
    )
    args = ap.parse_args()

    cfg = load_config()
    mode = args.mode or cfg.default_mode
    if mode not in cfg.modes:
        print(f"Error: mode '{mode}' not defined in config.", file=sys.stderr)
        sys.exit(1)

    includes = list(cfg.modes[mode].include) + list(args.include or [])
    excludes = list(cfg.modes[mode].exclude) + list(args.exclude or [])
    max_size = args.max_size or cfg.max_size
    do_redact = not args.no_redact if args.no_redact else cfg.redact

    files = collect_files(includes, excludes)
    tree = render_tree(files)

    if args.dry_run:
        print("--- DRY RUN ---")
        print(f"Mode: {mode}")
        print(f"Files: {len(files)}")
        print("\nTree:\n" + tree)
        print("\nList:")
        for p in files:
            print(rel_posix(p))
        print("--- END DRY RUN ---")
        return

    # Context
    context_parts = [f"Generated on: {ts_utc()}"]
    if not args.no_git and cfg.context_git:
        context_parts.append(get_git_info().rstrip())
    if not args.no_jobs and cfg.context_jobs:
        context_parts.append(get_jobs_summary().rstrip())
    if not args.no_manifest and cfg.context_manifest:
        context_parts.append(get_code_manifest().rstrip())
    context = "\n\n".join(context_parts)

    # Output writer
    out = args.output
    write_zip = args.zip or out.endswith(".zip")

    if write_zip:
        zip_path = out if out.endswith(".zip") else out + ".zip"
        if not args.silent:
            print(f"Writing zip snapshot: {zip_path} ({len(files)} files)")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            manifest = []
            manifest.append("# XSArena Snapshot")
            manifest.append(context)
            manifest.append("\n--- TREE ---\n")
            manifest.append(tree)
            z.writestr("snapshot_manifest.txt", "\n".join(manifest))

            for i, p in enumerate(files, 1):
                rp = rel_posix(p)
                if not args.silent:
                    print(f"[{i}/{len(files)}] Adding {rp}...")
                try:
                    b, truncated = safe_read_bytes(p, max_size)
                    if is_binary_sample(b):
                        # Store as text placeholder with metadata (safer than raw binary in a redacted bundle)
                        meta = f"[BINARY FILE] path={rp} size={p.stat().st_size} sha256={sha256_bytes(p.read_bytes())}\n"
                        z.writestr(rp, meta)
                    else:
                        text = b.decode("utf-8", errors="replace")
                        if do_redact:
                            text = redact_text(text)
                        if truncated:
                            text = (
                                f"[... FILE TRUNCATED to {max_size} bytes ...]\n" + text
                            )
                        z.writestr(rp, text)
                except Exception as e:
                    z.writestr(rp + ".error", f"[ERROR READING FILE: {e}]")
        if not args.silent:
            print("Done.")
        return

    # Text snapshot
    txt_path = out if out.endswith(".txt") else out + ".txt"
    if not args.silent:
        print(f"Writing text snapshot: {txt_path} ({len(files)} files)")
    with open(txt_path, "w", encoding="utf-8") as f_out:
        f_out.write("# XSArena Snapshot\n")
        f_out.write(context + "\n\n")
        f_out.write("--- TREE ---\n\n")
        f_out.write(tree + "\n\n")

        for i, p in enumerate(files, 1):
            rp = rel_posix(p)
            if not args.silent:
                print(f"[{i}/{len(files)}] Adding {rp}...")
            f_out.write(f"--- START OF FILE {rp} ---\n")
            try:
                b, truncated = safe_read_bytes(p, max_size)
                if is_binary_sample(b):
                    size = p.stat().st_size
                    digest = sha256_bytes(p.read_bytes())
                    f_out.write(f"[BINARY FILE] size={size} sha256={digest}\n")
                else:
                    text = b.decode("utf-8", errors="replace")
                    if do_redact:
                        text = redact_text(text)
                    if truncated:
                        text = f"[... FILE TRUNCATED to {max_size} bytes ...]\n" + text
                    f_out.write(text)
            except Exception as e:
                f_out.write(f"[ERROR READING FILE: {e}]")
            f_out.write(f"\n--- END OF FILE {rp} ---\n\n")

    if not args.silent:
        print("=" * 30)
        print("Snapshot Generation Complete!")
        print(f"  Output file: {txt_path}")
        print(f"  Files included: {len(files)}")
        print("=" * 30)


if __name__ == "__main__":
    main()
