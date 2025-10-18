#!/usr/bin/env python3
"""
XSArena Advanced Snapshot Builder (v2)

Creates an intelligent, minimal, and configurable project snapshot.
- Uses .snapshotinclude and .snapshotignore files for git-like control.
- Whitelist-first approach ensures minimal size by default.
- Redacts sensitive information automatically.
- Includes optional sections for git status, job summaries, and code manifest.
"""
import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# --- Redaction Service (with fallback) ---
try:
    from xsarena.core.redact import redact as redact_text
except ImportError:
    print(
        "Warning: xsarena.core.redact not found. Using fallback redaction.",
        file=sys.stderr,
    )

    def _fallback_redact(text: str) -> str:
        pats = [
            (
                re.compile(
                    r'(?i)(api[_-]?key|secret|token|password|pwd|auth|bearer)[\s:=]+[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?'
                ),
                r'\1="[REDACTED]"',
            ),
            (
                re.compile(r"\b[A-Za-z0-9._%+-]+ @[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
                "[REDACTED_EMAIL]",
            ),
            (re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"), "[REDACTED_IP]"),
        ]
        for rgx, rep in pats:
            text = rgx.sub(rep, text)
        return text

    redact_text = _fallback_redact

# --- Context Gathering Functions ---


def get_git_info() -> str:
    """Gathers git branch, commit, and status information."""
    if not (Path.cwd() / ".git").exists():
        return "Git: (Not a git repository)\n"
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True
        ).strip()
        status_summary = (
            f"{len(status.splitlines())} changed file(s)" if status else "clean"
        )
        return f"Git Branch: {branch}\nGit Commit: {commit}\nGit Status: {status_summary}\n"
    except Exception as e:
        return f"Git: (Error gathering info: {e})\n"


def get_jobs_summary() -> str:
    """Generates a summary of recent jobs."""
    jobs_dir = Path.cwd() / ".xsarena" / "jobs"
    if not jobs_dir.exists():
        return "Jobs: (No jobs directory found)\n"
    summaries = []
    job_dirs = sorted(jobs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for job_dir in job_dirs[:5]:  # Limit to 5 most recent jobs
        if not job_dir.is_dir():
            continue
        job_file = job_dir / "job.json"
        events_file = job_dir / "events.jsonl"
        if not job_file.exists():
            continue
        try:
            job_data = json.loads(job_file.read_text("utf-8"))
            state = job_data.get("state", "UNKNOWN")
            name = job_data.get("name", job_dir.name)
            chunks, retries = 0, 0
            if events_file.exists():
                for line in events_file.read_text("utf-8").splitlines():
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
    """Generates a manifest of SHA256 hashes for all .py files under src/."""
    manifest = []
    src_root = Path.cwd() / "src"
    if not src_root.exists():
        return "Code Manifest: (src/ directory not found)\n"

    py_files = sorted(src_root.rglob("*.py"))
    for py_file in py_files:
        try:
            hasher = hashlib.sha256()
            hasher.update(py_file.read_bytes())
            digest = hasher.hexdigest()
            manifest.append(f"{digest[:12]}  {py_file.relative_to(Path.cwd())}")
        except Exception:
            manifest.append(f"{'[ERROR]':<12}  {py_file.relative_to(Path.cwd())}")
    return "Code Manifest (src/**/*.py):\n" + "\n".join(manifest) + "\n"


# --- File System and Rendering Logic ---


def load_patterns(filepath: Path) -> list[str]:
    if not filepath.exists():
        return []
    return [
        line.strip()
        for line in filepath.read_text("utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def collect_files(
    root: Path, include_patterns: list[str], ignore_patterns: list[str]
) -> list[Path]:
    files_to_include = set()
    for pattern in include_patterns:
        for path in root.glob(pattern):
            is_ignored = any(
                fnmatch.fnmatch(path, p)
                or any(fnmatch.fnmatch(parent, p) for parent in path.parents)
                for p in ignore_patterns
            )
            if not is_ignored:
                if path.is_file():
                    files_to_include.add(path)
                elif path.is_dir():
                    for sub_path in path.rglob("*"):
                        if sub_path.is_file() and not any(
                            fnmatch.fnmatch(sub_path, p)
                            or any(
                                fnmatch.fnmatch(parent, p)
                                for parent in sub_path.parents
                            )
                            for p in ignore_patterns
                        ):
                            files_to_include.add(sub_path)
    return sorted(list(files_to_include))


def generate_tree(files: list[Path], root: Path) -> str:
    tree = {}
    for file in files:
        parts = file.relative_to(root).parts
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    def render_node(node: dict, prefix: str = "") -> list[str]:
        lines = []
        items = sorted(node.keys())
        for i, name in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            lines.append(f"{prefix}{connector}{name}")
            if node[name]:
                extension = "    " if i == len(items) - 1 else "│   "
                lines.extend(render_node(node[name], prefix + extension))
        return lines

    return ".\n" + "\n".join(render_node(tree))


def main():
    parser = argparse.ArgumentParser(description="XSArena Advanced Snapshot Builder.")
    parser.add_argument(
        "output", nargs="?", default="xsa_min_snapshot.txt", help="Output file name."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print files to be included without creating the snapshot.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Additional glob patterns to include.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional glob patterns to exclude.",
    )
    parser.add_argument(
        "--no-redact",
        action="store_true",
        help="Disable redaction of sensitive information.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=200 * 1024,
        help="Max size in bytes for a single file's content (200KB default).",
    )
    parser.add_argument(
        "-q", "--silent", action="store_true", help="Suppress progress messages."
    )
    # New context flags
    parser.add_argument(
        "--with-git", action="store_true", help="Include git status information."
    )
    parser.add_argument(
        "--with-jobs", action="store_true", help="Include a summary of recent jobs."
    )
    parser.add_argument(
        "--with-manifest", action="store_true", help="Include a code manifest of src/."
    )

    args = parser.parse_args()

    project_root = Path.cwd()

    # Load patterns
    base_ignore = load_patterns(project_root / ".snapshotignore") + args.exclude
    base_include = load_patterns(project_root / ".snapshotinclude") + args.include

    if not base_include:
        print(
            "Error: .snapshotinclude is empty or not found. Cannot create a snapshot.",
            file=sys.stderr,
        )
        sys.exit(1)

    files = collect_files(project_root, base_include, base_ignore)
    tree_str = generate_tree(files, project_root)

    if args.dry_run:
        print("--- DRY RUN ---")
        if args.with_git:
            print("\n# Git Info:\n" + get_git_info())
        if args.with_jobs:
            print("\n# Jobs Summary:\n" + get_jobs_summary())
        if args.with_manifest:
            print("\n# Code Manifest:\n" + get_code_manifest())
        print("\n# Project Tree to be included:")
        print(tree_str)
        print("\n# Files to be included:")
        for f in files:
            print(f.relative_to(project_root))
        print(f"\nTotal files: {len(files)}")
        print("--- END DRY RUN ---")
        return

    total_size = 0
    with open(args.output, "w", encoding="utf-8") as f_out:
        f_out.write("# XSArena Advanced Snapshot\n")
        f_out.write(f"Generated on: {datetime.now(datetime.UTC).isoformat()}Z\n\n")

        f_out.write("--- START OF CONTEXT ---\n\n")
        if args.with_git:
            f_out.write(get_git_info() + "\n")
        if args.with_jobs:
            f_out.write(get_jobs_summary() + "\n")
        if args.with_manifest:
            f_out.write(get_code_manifest() + "\n")
        f_out.write("--- END OF CONTEXT ---\n\n")

        f_out.write("# Project Tree Structure\n\n")
        f_out.write(tree_str)
        f_out.write("\n\n")

        for i, file_path in enumerate(files):
            relative_path = file_path.relative_to(project_root)
            if not args.silent:
                print(f"[{i+1}/{len(files)}] Adding {relative_path}...")

            f_out.write(f"--- START OF FILE {relative_path} ---\n")
            try:
                content = file_path.read_text(encoding="utf-8")
                file_size = len(content.encode("utf-8"))
                total_size += file_size

                if file_size > args.max_size:
                    content = f"[... FILE TRUNCATED: Size ({file_size} bytes) > max ({args.max_size} bytes) ...]\n"

                if not args.no_redact:
                    content = redact_text(content)

                f_out.write(content)
            except Exception as e:
                f_out.write(f"[... ERROR READING FILE: {e} ...]")

            f_out.write(f"\n--- END OF FILE {relative_path} ---\n\n")

    if not args.silent:
        print("\n" + "=" * 30)
        print("Snapshot Generation Complete!")
        print(f"  Output file: {args.output}")
        print(f"  Files included: {len(files)}")
        print(f"  Total content size: {total_size / 1024:.2f} KB")
        print("=" * 30)


if __name__ == "__main__":
    main()
