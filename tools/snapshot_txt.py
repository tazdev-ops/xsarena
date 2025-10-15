#!/usr/bin/env python3
"""
XSArena Snapshot Utility (single-file, read-only)

Creates a comprehensive, text-only, redacted snapshot of the project suitable for
debugging/sharing with higher AI systems.

Features:
- System info (Python, platform, cwd)
- Git status/branch/commit (if available)
- Directory trees and file listings
- Code/config manifest with file hashes (SHA256)
- Inline important configuration/doc files
- Canonical rules digest (first 200 lines of directives/_rules/rules.merged.md)
- Snapshot health checks
- Sensitive info redaction (API keys, emails, IPs, URLs, long tokens)
- Chunked output (default: 120KB per chunk) with footer: "Answer received. Do nothing else"
- Combined snapshot digest and per-chunk digests

Safety:
- Read-only operations on project files; writes only the snapshot .txt files.

Designed to be run from the project root of XSArena.

Usage:
  python tools/snapshot_txt.py
  python tools/snapshot_txt.py --output .xsarena/snapshots/snapshot.txt --max-chunk-bytes 120000
"""

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# ------------ Configuration (tweak as needed) ------------

# Directories we care about for tree + manifest
DEFAULT_INCLUDE_DIRS = [
    "src",
    "directives",
    "recipes",
    "scripts",
    "docs",
    "data",
    "examples",
    "packaging",
    "pipelines",
    "review",
    ".xsarena",  # but exclude checkpoints and jobs subdirs
    "tools",
    "tests",
]

# Common junk/caches/artifacts to exclude from tree + manifest
EXCLUDE_DIR_NAMES = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".tox",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".DS_Store",
}
EXCLUDE_FILE_GLOBS = {
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.lock",
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.gz",
    "*.bz2",
    "*.7z",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.pdf",
    "*.sqlite3",
    "*.db",
}

# Important config/docs to inline
IMPORTANT_FILES = [
    "pyproject.toml",
    "README.md",
    "mypy.ini",
    "models.json",
    ".pre-commit-config.yaml",
    "CHANGELOG.md",
    "CHANGES_SUMMARY.md",
    "CONFIG_REFERENCE.md",
    "CONTRIBUTING.md",
    "MODULES.md",
    "ROADMAP.md",
    "SUPPORT.md",
    "DEPRECATIONS.md",
    "FINAL_SUMMARY.md",
    "FINAL_SYNTHESIS.md",
    "IMPORTANT_FILES_LIST.md",
    "LICENSE",
    "lmarena_bridge.user.js",
    "healthcheck_script.sh",
    "recipe.example.yml",
    "install_deps.sh",
    "hygiene_pass.sh",
    "docs/HIGHER_AI_COMM_PROTOCOL.md",
    "docs/SNAPSHOT_POLICY.md",
    "docs/SAFE_COMMANDS.md",
    ".xsarena/config.yml",
    ".xsarena/session_state.json",
    ".xsarena/project.yml",
    ".xsarena/cleanup.yml",
    # Include key source files to increase snapshot size appropriately
    "src/xsarena/__init__.py",
    "src/xsarena/cli/main.py",
    "src/xsarena/cli/context.py",
    "src/xsarena/core/__init__.py",
    "src/xsarena/core/engine.py",
    "src/xsarena/core/prompt.py",
    "src/xsarena/core/jobs.py",
    "src/xsarena/core/config.py",
    "src/xsarena/bridge/__init__.py",
    "src/xsarena/bridge/server.py",
    "src/xsarena/modes/__init__.py",
    "src/xsarena/utils/__init__.py",
    # Include large important files
    "src/xsarena/interactive.py",
    "directives/_rules/rules.merged.md",
    "directives/_rules/sources/CLI_AGENT_RULES.md",
]

# Rules digest file + number of lines
RULES_MERGED_PATH = "directives/_rules/rules.merged.md"
RULES_MERGED_DIGEST_LINES = 200

# Allowed file types for manifest hashing (text/code/config)
MANIFEST_EXTS = {
    ".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".ini", ".cfg",
    ".sh", ".bat", ".ps1", ".csv", ".tsv",
}

# Redaction patterns
RE_EMAIL = re.compile(r'(?<![\w.])([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})', re.I)
RE_URL = re.compile(r'\b(?:https?|ssh|git)://[^\s\]\)>"\'`]+', re.I)
RE_IPV4 = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|1?\d{1,2})\b'
)
RE_IPV6 = re.compile(r'\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b')

RE_AWS_KEY = re.compile(r'\bAKIA[0-9A-Z]{16}\b')
RE_AWS_SECRET = re.compile(
    r'(?i)\baws[^:\n]{0,40}[:=]\s*([A-Za-z0-9/+=]{40})\b'
)
RE_OPENAI = re.compile(r'\bsk-[A-Za-z0-9]{20,}\b')
RE_GH = re.compile(r'\bgh[pousr]_[A-Za-z0-9]{36}\b')
RE_SLACK = re.compile(r'\bxox[a-z]-[A-Za-z0-9-]{10,}\b')
RE_BEARER = re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_\-\.=+/]{10,}\b')

# Generic long token (min len 24)
RE_LONG_TOKEN = re.compile(
    r'\b(?=[A-Za-z0-9_\-]*[0-9])(?=[A-Za-z0-9_\-]*[A-Z])(?=[A-Za-z0-9_\-]*[a-z])[A-Za-z0-9_\-]{32,}\b'
)

RE_ENV_STYLE_SECRET = re.compile(
    r'(?im)^\s*(?:SECRET|TOKEN|API[_-]?KEY|PASSWORD|PASS|AUTH|PRIVATE[_-]?KEY)\s*[:=]\s*([^\s#]+)'
)

RE_SSH_PRIVATE_HEADER = re.compile(r'-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----')

# Chunking
DEFAULT_MAX_CHUNK_BYTES = 120_000

# ------------ Helpers ------------

def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def human_size(n: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024.0:
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024.0
    return f"{n:.1f}PB"

def is_hidden(p: Path) -> bool:
    name = p.name
    return name.startswith(".")

def matches_globs(name: str, globs: Iterable[str]) -> bool:
    from fnmatch import fnmatch
    return any(fnmatch(name, g) for g in globs)

def is_excluded(path: Path) -> bool:
    # Exclude directories by name and files by glob
    parts = set(path.parts)
    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return True
    # Also exclude specific subdirectories that contain outputs
    path_str = str(path)
    if any(subdir in path_str for subdir in ["/checkpoints/", "/jobs/", "/finals/", "/outlines/", "/flashcards/", "/archive/", "/.lmastudio/"]):
        return True
    if path.is_file() and matches_globs(path.name, EXCLUDE_FILE_GLOBS):
        return True
    return False

def safe_read_text(path: Path, max_bytes: Optional[int] = None) -> str:
    try:
        if max_bytes is None:
            return path.read_text(encoding="utf-8", errors="replace")
        else:
            with path.open("rb") as f:
                data = f.read(max_bytes)
            return data.decode("utf-8", errors="replace")
    except Exception as e:
        return f"<<ERROR READING {path}: {e}>>"

def redact(text: str) -> str:
    # order matters: coarser patterns last
    t = text

    # Remove SSH private key blocks fast
    if RE_SSH_PRIVATE_HEADER.search(t):
        return "[REDACTED_SSH_PRIVATE_KEY_BLOCK]"

    t = RE_BEARER.sub("Bearer [REDACTED_BEARER]", t)
    t = RE_AWS_KEY.sub("[REDACTED_AWS_KEY]", t)
    t = RE_AWS_SECRET.sub("[REDACTED_AWS_SECRET]", t)
    t = RE_OPENAI.sub("[REDACTED_OPENAI_KEY]", t)
    t = RE_GH.sub("[REDACTED_GITHUB_TOKEN]", t)
    t = RE_SLACK.sub("[REDACTED_SLACK_TOKEN]", t)
    t = RE_ENV_STYLE_SECRET.sub(lambda m: t[m.start():m.start(1)] + "[REDACTED_SECRET]", t)

    t = RE_EMAIL.sub("[REDACTED_EMAIL]", t)
    t = RE_URL.sub("[REDACTED_URL]", t)
    t = RE_IPV4.sub("[REDACTED_IP]", t)
    t = RE_IPV6.sub("[REDACTED_IP]", t)

    # generic tokens last to reduce over-redaction of code
    t = RE_LONG_TOKEN.sub("[REDACTED_TOKEN]", t)
    return t

def run_cmd(cmd: Sequence[str], cwd: Optional[Path] = None, timeout: float = 5.0) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", f"{type(e).__name__}: {e}"

def gather_git_info(root: Path) -> str:
    lines = []
    rc, out, _ = run_cmd(["git", "rev-parse", "--is-inside-work-tree"], cwd=root)
    if rc != 0 or out.strip().lower() != "true":
        return "Git: not a repository or git not available"
    # Branch
    _, branch, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    # Commit
    _, commit, _ = run_cmd(["git", "rev-parse", "HEAD"], cwd=root)
    # Status
    _, status, _ = run_cmd(["git", "status", "--porcelain=v1"], cwd=root)
    # Describe
    _, describe, _ = run_cmd(["git", "describe", "--tags", "--always", "--dirty"], cwd=root)
    # Remotes
    _, remotes, _ = run_cmd(["git", "remote", "-v"], cwd=root)

    lines.append(f"Git branch: {redact(branch)}")
    lines.append(f"Git commit: {redact(commit)}")
    lines.append(f"Git describe: {redact(describe)}")
    if remotes:
        lines.append("Git remotes (redacted):")
        for ln in remotes.splitlines():
            # redacts URLs or embedded creds
            lines.append(f"  {redact(ln)}")
    if status:
        lines.append("Git status (porcelain):")
        for ln in status.splitlines():
            lines.append(f"  {ln}")
    else:
        lines.append("Git status: clean")
    return "\n".join(lines)

def render_tree_for(root: Path, rel: Path) -> str:
    base = root / rel
    if not base.exists():
        return f"{rel}/ (missing)"
    # In-order traversal with visual tree
    lines = [f"{rel}/"]
    def walk(dir_path: Path, prefix: str) -> None:
        try:
            entries = [p for p in dir_path.iterdir() if not is_excluded(p)]
        except Exception as e:
            lines.append(prefix + f"<<ERROR listing {dir_path}: {e}>>")
            return
        entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
        for i, p in enumerate(entries):
            is_last = i == len(entries) - 1
            branch = "└── " if is_last else "├── "
            cont = "    " if is_last else "│   "
            name = p.name + ("/" if p.is_dir() else "")
            info = ""
            try:
                st = p.stat()
                if p.is_file():
                    info = f" ({human_size(st.st_size)})"
            except Exception:
                info = " (unstatable)"
            lines.append(prefix + branch + name + info)
            if p.is_dir():
                walk(p, prefix + cont)
    if base.is_dir():
        walk(base, "")
    else:
        # single file
        try:
            st = base.stat()
            lines[0] = f"{rel} ({human_size(st.st_size)})"
        except Exception:
            lines[0] = f"{rel} (unstatable)"
    return "\n".join(lines)

def build_project_tree(root: Path, include_dirs: Sequence[str]) -> str:
    sections = []
    # Top-level files of interest - just list them, don't try to render as tree since they're files
    top_level_targets = set(IMPORTANT_FILES)
    # plus any top-level files from the spec that might exist
    extra_top = [
        "pyproject.toml", "README.md", "mypy.ini", "models.json", ".pre-commit-config.yaml",
        "CHANGELOG.md", "CONFIG_REFERENCE.md", "CONTRIBUTING.md", "MODULES.md", "ROADMAP.md",
        "SUPPORT.md", "DEPRECATIONS.md", "recipe.example.yml", "install_deps.sh",
        "hygiene_pass.sh",
    ]
    top_files = []
    for f in sorted(set(extra_top)):
        p = root / f
        if p.exists() and not is_excluded(p):
            try:
                st = p.stat()
                top_files.append(f"{f} ({human_size(st.st_size)})")
            except Exception:
                top_files.append(f"{f} (unstatable)")
    if top_files:
        sections.append("Top-level files:\n" + "\n".join(top_files))
    
    # Directories - render full tree structure
    for d in include_dirs:
        sections.append(render_tree_for(root, Path(d)))
    return "\n\n".join(sections)

def collect_manifest(root: Path, include_dirs: Sequence[str]) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    """
    Returns:
      - manifest list of dicts: {path, size, mtime, mode, sha256?}
      - summary counts: files_scanned, dirs_scanned, bytes_total
    """
    manifest: List[Dict[str, str]] = []
    files_scanned = 0
    dirs_scanned = 0
    bytes_total = 0

    def should_hash_file(p: Path) -> bool:
        if p.suffix.lower() in MANIFEST_EXTS:
            return True
        # for others, only hash small files (<1MB) to avoid overhead
        try:
            return p.stat().st_size <= 1_000_000
        except Exception:
            return False

    for inc in include_dirs:
        base = root / inc
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dpath = Path(dirpath)
            # mutate dirnames in-place to skip excluded
            dirnames[:] = [dn for dn in dirnames if not is_excluded(dpath / dn)]
            dirs_scanned += 1
            for fn in filenames:
                p = dpath / fn
                if is_excluded(p):
                    continue
                try:
                    st = p.stat()
                except Exception:
                    continue
                # Skip very large binary-like files from manifest
                size = st.st_size
                rel = str(p.relative_to(root))
                entry: Dict[str, str] = {
                    "path": rel,
                    "size": str(size),
                    "mtime": str(int(st.st_mtime)),
                    "mode": oct(st.st_mode & 0o777),
                }
                if should_hash_file(p):
                    try:
                        entry["sha256"] = sha256_file(p)
                    except Exception:
                        entry["sha256"] = "<<ERROR>>"
                else:
                    entry["sha256"] = "<<SKIPPED>>"
                manifest.append(entry)
                files_scanned += 1
                bytes_total += size
    summary = {
        "files_scanned": files_scanned,
        "dirs_scanned": dirs_scanned,
        "bytes_total": bytes_total,
    }
    return manifest, summary

def manifest_digest(manifest: List[Dict[str, str]]) -> str:
    # stable order by path
    lines = []
    for entry in sorted(manifest, key=lambda e: e["path"]):
        lines.append("{path}|{size}|{mtime}|{mode}|{sha256}".format(**entry))
    data = ("\n".join(lines)).encode("utf-8")
    return sha256_bytes(data)

def inline_file(root: Path, rel_path: str, max_bytes: Optional[int] = None) -> str:
    p = root / rel_path
    if not p.exists():
        return f"[missing] {rel_path}"
    content = safe_read_text(p, max_bytes=max_bytes)
    red = redact(content)
    return f"----- BEGIN {rel_path} -----\n{red}\n----- END {rel_path} -----"

def canonical_rules_digest(root: Path, rel_path: str, max_lines: int) -> str:
    p = root / rel_path
    if not p.exists():
        return f"[missing] {rel_path}"
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            lines = []
            for i, ln in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(ln.rstrip("\n"))
        red = redact("\n".join(lines))
        return f"----- BEGIN DIGEST {rel_path} (first {max_lines} lines) -----\n{red}\n----- END DIGEST {rel_path} -----"
    except Exception as e:
        return f"<<ERROR reading {rel_path}: {e}>>"

def find_job_summaries(root: Path) -> List[Tuple[str, str]]:
    """
    Collects small-to-medium job/report artifacts for quick situational awareness.
    Sources:
      - .xsarena/ (existing)
      - review/report_*/ (job_summary.json, report.md, config.yml, rules.merged.md, session_state.json)
      - a few tiny review helper files (*.list, *SUMMARY*.md, *HEALTHCHECK*.md)
    Caps:
      - 256KB per file
      - Up to 20 files total
    """
    results: List[Tuple[str, str]] = []
    MAX_BYTES = 256_000
    MAX_FILES = 20

    def add_if_ok(p: Path) -> None:
        nonlocal results
        if len(results) >= MAX_FILES:
            return
        try:
            if not p.exists() or not p.is_file():
                return
            size = p.stat().st_size
            if size > MAX_BYTES:
                return
            rel = str(p.relative_to(root))
            content = safe_read_text(p, max_bytes=MAX_BYTES)
            results.append((rel, redact(content)))
        except Exception:
            pass

    # .xsarena pass (existing behavior)
    xs = root / ".xsarena"
    if xs.exists():
        for dirpath, dirnames, filenames in os.walk(xs):
            dpath = Path(dirpath)
            dirnames[:] = [dn for dn in dirnames if dn not in {".git", "__pycache__", ".mypy_cache", ".ruff_cache"}]
            for fn in filenames:
                name = fn.lower()
                if any(k in name for k in ("job", "summary", "report", "run", "task")):
                    add_if_ok(dpath / fn)

    # review/report_* artifacts
    review = root / "review"
    if review.exists():
        for child in sorted(review.iterdir()):
            if child.is_dir() and child.name.startswith("report_"):
                for candidate in ("job_summary.json", "report.md", "config.yml", "rules.merged.md", "session_state.json"):
                    add_if_ok(child / candidate)
        # a few small review helpers if tiny
        for helper in ("PROJECT_MAP_SUMMARY.md", "final_verification.txt", "SNAPSHOT_HEALTHCHECK.md"):
            for p in review.glob(f"*{helper}*"):
                add_if_ok(p)

    return results

def health_checks(root: Path, manifest_summary: Dict[str, int]) -> str:
    required_paths = [
        "pyproject.toml",
        "src/xsarena",
        "src/xsarena/cli/cmds_snapshot.py",
        "directives/_rules/rules.merged.md",
        "books",
        "docs",
        "review",
        "data",
        "recipes",
        "tools",
        "tests",
    ]
    lines = []
    missing = []
    for rp in required_paths:
        exists = (root / rp).exists()
        lines.append(f"[{'OK' if exists else 'MISS'}] {rp}")
        if not exists:
            missing.append(rp)

    # Rules digest completeness
    rules_p = root / RULES_MERGED_PATH
    if rules_p.exists():
        try:
            with rules_p.open("r", encoding="utf-8", errors="replace") as f:
                for i, _ in enumerate(f, 1):
                    if i >= RULES_MERGED_DIGEST_LINES:
                        break
            if i >= RULES_MERGED_DIGEST_LINES:
                lines.append("[OK] rules.merged.md has >= 200 lines")
            else:
                lines.append("[WARN] rules.merged.md has < 200 lines")
        except Exception as e:
            lines.append(f"[WARN] rules.merged.md read error: {e}")
    else:
        lines.append("[MISS] rules.merged.md not found")

    # Warn on empty-but-present modules that look intentional
    for maybe_empty in ["src/xsarena/router", "src/xsarena/coder"]:
        p = root / maybe_empty
        if p.exists() and p.is_dir():
            try:
                has_files = any((p / name).is_file() for name in os.listdir(p))
            except Exception:
                has_files = False
            if not has_files:
                lines.append(f"[WARN] {maybe_empty} present but empty (confirm intent or remove)")

    # Manifest summary
    lines.append(f"Scanned dirs: {manifest_summary.get('dirs_scanned', 0)}")
    lines.append(f"Scanned files: {manifest_summary.get('files_scanned', 0)}")
    lines.append(f"Total bytes (on disk): {human_size(manifest_summary.get('bytes_total', 0))}")

    lines.append("Overall health: OK" if not missing else "Overall health: DEGRADED")
    return "\n".join(lines)

def system_info(root: Path) -> str:
    def tool_ver(cmd: Sequence[str]) -> str:
        rc, out, err = run_cmd(cmd, cwd=root)
        return out or err or "unavailable"

    info = {
        "timestamp": now_iso(),
        "cwd": str(root.resolve()),
        "python": sys.version.replace("\n", " "),
        "python_exe": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "n/a",
        "py_impl": platform.python_implementation(),
        "git_version": tool_ver(["git", "--version"]),
        "node_version": tool_ver(["node", "-v"]),
        "npm_version": tool_ver(["npm", "-v"]),
        "poetry_version": tool_ver(["poetry", "--version"]),
        "pip_version": tool_ver([sys.executable, "-m", "pip", "--version"]),
    }
    return "\n".join(f"{k}: {v}" for k, v in info.items())

def inclusion_exclusion_criteria() -> str:
    lines = []
    lines.append("Inclusion:")
    lines.append(f"- Directories: {', '.join(DEFAULT_INCLUDE_DIRS)}")
    lines.append("- Important top-level files listed under IMPORTANT_FILES")
    lines.append("Exclusion:")
    lines.append(f"- Directory names: {', '.join(sorted(EXCLUDE_DIR_NAMES))}")
    lines.append(f"- File globs: {', '.join(sorted(EXCLUDE_FILE_GLOBS))}")
    lines.append("Rationale: keep bridge-first CLI structure, configs/docs inline, code listed via manifest with hashes.")
    return "\n".join(lines)

def build_snapshot_text(root: Path, max_inline_bytes_per_file: int = 750_000) -> str:
    sections: List[str] = []

    sections.append("==== XSArena Snapshot ====")
    sections.append(system_info(root))
    sections.append("")
    sections.append("==== Communication Protocol (summary) ====")
    sections.append("- Use clear, structured commands")
    sections.append("- Provide context about the project structure")
    sections.append("- Reference rules under directives/_rules/")
    sections.append("- Be explicit about inclusion/exclusion criteria")
    sections.append("- Respect bridge-first architecture")
    sections.append("- Keep consistency with existing CLI patterns")
    sections.append("")
    sections.append("==== Git Information ====")
    sections.append(gather_git_info(root))
    sections.append("")
    sections.append("==== Inclusion/Exclusion Criteria ====")
    sections.append(inclusion_exclusion_criteria())
    sections.append("")
    sections.append("==== Directory Trees ====")
    sections.append(build_project_tree(root, DEFAULT_INCLUDE_DIRS))
    sections.append("")
    sections.append("==== Code/Config Manifest (with SHA256) ====")
    manifest, summary = collect_manifest(root, DEFAULT_INCLUDE_DIRS)

    # Ensure top-level IMPORTANT_FILES are in the manifest too
    extra_entries = []
    for rel in IMPORTANT_FILES:
        p = root / rel
        if p.exists() and p.is_file() and not is_excluded(p):
            try:
                st = p.stat()
                entry = {
                    "path": str(p.relative_to(root)),
                    "size": str(st.st_size),
                    "mtime": str(int(st.st_mtime)),
                    "mode": oct(st.st_mode & 0o777),
                    "sha256": sha256_file(p),
                }
                # avoid duplicates
                if all(e["path"] != entry["path"] for e in manifest):
                    extra_entries.append(entry)
            except Exception:
                pass
    if extra_entries:
        manifest.extend(extra_entries)
        summary["files_scanned"] = summary.get("files_scanned", 0) + len(extra_entries)
        summary["bytes_total"] = summary.get("bytes_total", 0) + sum(int(e["size"]) for e in extra_entries)

    # Render manifest
    sections.append("path | size | mtime | mode | sha256")
    for entry in sorted(manifest, key=lambda e: e["path"]):
        sections.append("{path} | {size} | {mtime} | {mode} | {sha256}".format(**entry))
    sections.append("")
    sections.append("==== Manifest Summary ====")
    sections.append(json.dumps(summary, indent=2))
    sections.append(f"Manifest digest (SHA256 over canonical entries): {manifest_digest(manifest)}")
    sections.append("")
    sections.append("==== Canonical Rules Digest ====")
    sections.append(canonical_rules_digest(root, RULES_MERGED_PATH, RULES_MERGED_DIGEST_LINES))
    sections.append("")
    sections.append("==== Inlined Important Files (redacted) ====")
    for rel in IMPORTANT_FILES:
        sections.append(inline_file(root, rel, max_bytes=max_inline_bytes_per_file))
    sections.append("")
    sections.append("==== Job Summaries (if present) ====")
    jobs = find_job_summaries(root)
    if not jobs:
        sections.append("[none found]")
    else:
        for rel, content in jobs:
            sections.append(f"----- BEGIN {rel} -----\n{content}\n----- END {rel} -----")
    sections.append("")
    sections.append("==== Health Checks ====")
    sections.append(health_checks(root, summary))
    sections.append("")
    # Combine raw text then apply a final redaction pass for safety
    raw = "\n".join(sections)
    red = redact(raw)
    return red

def chunk_by_bytes(text: str, max_bytes: int) -> List[str]:
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return [text]
    # Chunk on line boundaries
    lines = text.splitlines(keepends=True)
    chunks: List[str] = []
    buf: List[str] = []
    size = 0
    for ln in lines:
        b = len(ln.encode("utf-8"))
        if size + b > max_bytes and buf:
            chunks.append("".join(buf))
            buf = [ln]
            size = b
        else:
            buf.append(ln)
            size += b
    if buf:
        chunks.append("".join(buf))
    return chunks

def write_chunks(text: str, out_path: Path, max_chunk_bytes: int) -> List[Path]:
    chunks = chunk_by_bytes(text, max_chunk_bytes)
    full_digest = sha256_bytes(text.encode("utf-8"))
    out_files: List[Path] = []
    if len(chunks) == 1:
        # Single file
        chunk = chunks[0]
        chunk_digest = sha256_bytes(chunk.encode("utf-8"))
        body = []
        body.append(f"=== SNAPSHOT CHUNK 1/1 ===")
        body.append(f"Full snapshot digest: {full_digest}")
        body.append(f"Chunk digest: {chunk_digest}")
        body.append("")
        body.append(chunk.rstrip("\n"))
        body.append("")
        body.append("Answer received. Do nothing else")
        payload = "\n".join(body)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        out_files.append(out_path)
        return out_files

    # Multiple chunks: write suffixed files
    stem = out_path
    if stem.suffix.lower() == ".txt":
        stem = stem.with_suffix("")
    total = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        chunk_digest = sha256_bytes(chunk.encode("utf-8"))
        body = []
        body.append(f"=== SNAPSHOT CHUNK {i}/{total} ===")
        body.append(f"Full snapshot digest: {full_digest}")
        body.append(f"Chunk digest: {chunk_digest}")
        body.append("")
        body.append(chunk.rstrip("\n"))
        body.append("")
        body.append("Answer received. Do nothing else")
        payload = "\n".join(body)
        fn = stem.with_name(f"{stem.name}__chunk{i}-of-{total}.txt")
        fn.parent.mkdir(parents=True, exist_ok=True)
        fn.write_text(payload, encoding="utf-8")
        out_files.append(fn)
    return out_files

def default_output_path(root: Path) -> Path:
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    xs_dir = root / ".xsarena" / "snapshots"
    base_dir = xs_dir if xs_dir.parent.exists() else root
    return base_dir / f"snapshot_{ts}.txt"

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a comprehensive, redacted text snapshot of the XSArena project."
    )
    parser.add_argument(
        "--root", default=".", help="Project root (default: current directory)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output path (.txt). If chunked, suffixed files are created. Default: .xsarena/snapshots/snapshot_*.txt (or project root if .xsarena missing).",
    )
    parser.add_argument(
        "--max-chunk-bytes",
        type=int,
        default=DEFAULT_MAX_CHUNK_BYTES,
        help=f"Max bytes per output chunk (default: {DEFAULT_MAX_CHUNK_BYTES})",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Disable git introspection (useful if git is unavailable).",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root does not exist: {root}", file=sys.stderr)
        return 2
    out = Path(args.output) if args.output else default_output_path(root)

    # Optionally disable git by monkey-patching gather_git_info
    global gather_git_info
    if args.no_git:
        def _no_git(_root: Path) -> str:
            return "Git: disabled by --no-git"
        gather_git_info = _no_git  # type: ignore

    snapshot_text = build_snapshot_text(root)
    out_files = write_chunks(snapshot_text, out, args.max_chunk_bytes)

    print("Snapshot written:")
    for p in out_files:
        try:
            sz = p.stat().st_size
        except Exception:
            sz = 0
        print(f" - {p} ({human_size(sz)})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())