"""
Simple snapshot utility for XSArena with minimal dependencies.

Zero dependencies; optional tomllib if present; otherwise default modes (minimal/standard/full).
Best-effort Git context and Jobs summary; never fatal.
Text or Zip output; truncates large files per max_size; optional redact.
"""

import hashlib
import json
import os
import platform
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Set, Tuple

try:
    import tomllib  # Python 3.11+
except ImportError:
    tomllib = None

ROOT = Path.cwd()


def ts_utc() -> str:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel_posix(path: Path) -> str:
    """Convert path to POSIX-style relative path."""
    return path.relative_to(ROOT).as_posix()


def is_binary_sample(b: bytes) -> bool:
    """Check if bytes look like binary content."""
    if not b:
        return False
    if b.count(0) > 0:
        return True
    # Heuristic: if too many non-text bytes
    text_chars = bytes(range(32, 127)) + b"\\n\\r\\t\\b\\f"
    non_text_ratio = sum(ch not in text_chars for ch in b) / len(b)
    return non_text_ratio > 0.30


def sha256_bytes(b: bytes) -> str:
    """Calculate SHA256 hash of bytes."""
    return hashlib.sha256(b).hexdigest()


def safe_read_bytes(p: Path, max_bytes: int) -> Tuple[bytes, bool]:
    """Safely read bytes from a file with size limit."""
    try:
        data = p.read_bytes()
    except Exception:
        return b"", False
    truncated = False
    if len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True
    return data, truncated


def safe_read_text(p: Path, max_bytes: int) -> Tuple[str, bool]:
    """Safely read text from a file with size limit."""
    try:
        text = p.read_text("utf-8", errors="replace")
    except Exception:
        return "[ERROR READING FILE]", False
    truncated = False
    if len(text) > max_bytes:
        text = text[:max_bytes]
        truncated = True
    return text, truncated


def read_snapshot_config() -> Dict:
    """Read snapshot configuration from .snapshot.toml with fallbacks."""
    cfg = {
        "mode": "standard",
        "max_size": 262144,  # 256KB
        "redact": True,
        "context": {"git": True, "jobs": True, "manifest": True},
        "modes": {
            "minimal": {
                "include": [
                    ".snapshot.toml",
                    "README.md",
                    "COMMANDS_REFERENCE.md",
                    "pyproject.toml",
                    "src/xsarena/**",
                ],
                "exclude": [
                    ".git/**",
                    ".svn/**",
                    ".hg/**",
                    ".idea/**",
                    ".vscode/**",
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
            },
            "standard": {
                "include": [
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
                "exclude": [
                    ".git/**",
                    ".svn/**",
                    ".hg/**",
                    ".idea/**",
                    ".vscode/**",
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
                    # Explicitly omit non-architectural or generated content
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
            },
            "full": {
                "include": [
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
                "exclude": [
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
            },
        },
    }

    # Try to read .snapshot.toml
    config_path = ROOT / ".snapshot.toml"
    if config_path.exists() and tomllib:
        try:
            data = tomllib.loads(config_path.read_bytes())
            # Update modes separately since it's a nested structure
            if "modes" in data:
                cfg["modes"].update(data.pop("modes", {}))
            cfg.update({k: v for k, v in data.items() if k in cfg or k == "context"})
        except Exception:
            # If .snapshot.toml is invalid, use defaults
            pass

    return cfg


def _matches(rel: str, pattern: str) -> bool:
    """Check if a relative path matches a glob pattern."""
    # Use PurePosixPath.match for proper ** handling; strip leading '/'
    pat = pattern.lstrip("/")
    return PurePosixPath(rel).match(pat)


def _expand_patterns(root: Path, patterns: List[str]) -> Set[Path]:
    """Expand glob patterns to a set of files."""
    out: Set[Path] = set()
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file():
                out.add(p)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        out.add(f)
    return out


def _split_reinclude(patterns: List[str]) -> Tuple[List[str], List[str]]:
    """Split patterns into normal and re-include patterns."""
    normal, reincludes = [], []
    for p in patterns:
        if p.startswith("!"):
            reincludes.append(p[1:])
        else:
            normal.append(p)
    return normal, reincludes


def _apply_excludes(
    candidates: Set[Path], exclude_patterns: List[str], reincludes: List[str]
) -> Set[Path]:
    """Apply exclude patterns and re-include patterns to a set of candidate files."""
    rels = {rel_posix(p): p for p in candidates}
    keep: Dict[str, Path] = {}
    for rel, p in rels.items():
        if any(_matches(rel, ex) for ex in exclude_patterns):
            continue
        keep[rel] = p
    # Re-includes win: expand and add back even if excluded
    if reincludes:
        for p in _expand_patterns(ROOT, reincludes):
            if p.is_file():
                keep[rel_posix(p)] = p
    return set(keep.values())


def collect_paths(
    mode: str, include_git_tracked: bool = False, include_untracked: bool = False
) -> List[Path]:
    """Collect paths based on mode and git options."""
    cfg = read_snapshot_config()

    if include_git_tracked:
        return collect_git_files(
            include_untracked, cfg.get("modes", {}).get(mode, {}).get("exclude", [])
        )

    # Handle max mode differently - include everything except excludes
    if mode == "max":
        include_patterns = ["**/*"]
        exclude_patterns = []
    else:
        # Get mode-specific patterns
        mode_config = cfg.get("modes", {}).get(mode, {})
        include_patterns = mode_config.get("include", [])
        exclude_patterns = mode_config.get("exclude", [])

    # Add default excludes (these are always applied)
    default_excludes = [
        ".git/**",
        ".svn/**",
        ".hg/**",
        ".idea/**",
        ".vscode/**",
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
    ]

    all_excludes = exclude_patterns + default_excludes
    exclude_norm, reincludes = _split_reinclude(all_excludes)

    candidates = _expand_patterns(ROOT, include_patterns)
    files = _apply_excludes(candidates, exclude_norm, reincludes)
    return sorted(files)


def collect_git_files(
    include_untracked: bool, exclude_patterns: List[str]
) -> List[Path]:
    """Collect git-tracked files."""
    if not (ROOT / ".git").exists():
        return []

    files: Set[Path] = set()
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files"], cwd=ROOT, text=True
        ).splitlines()
        for rel in tracked:
            p = (ROOT / rel).resolve()
            if p.is_file():
                files.add(p)
        if include_untracked:
            others = subprocess.check_output(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=ROOT,
                text=True,
            ).splitlines()
            for rel in others:
                p = (ROOT / rel).resolve()
                if p.is_file():
                    files.add(p)
    except Exception:
        pass

    # Apply excludes
    exclude_norm, reincludes = _split_reinclude(exclude_patterns)
    files = _apply_excludes(files, exclude_norm, reincludes)
    return sorted(files)


def build_git_context() -> str:
    """Build git context information."""
    if not (ROOT / ".git").exists():
        return "Git: (Not a git repository)\\n"

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
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci"], cwd=ROOT, text=True
        ).strip()

        return f"Git Branch: {branch}\\nGit Commit: {commit}\\nGit Status: {status_summary}\\nGit Date: {date}\\n"
    except Exception as e:
        return f"Git: (Error gathering info: {e})\\n"


def build_jobs_summary() -> str:
    """Build jobs summary from .xsarena/jobs/."""
    jobs_dir = ROOT / ".xsarena" / "jobs"
    if not jobs_dir.exists():
        return "Jobs: (No jobs directory found)\\n"

    summaries = []
    job_dirs = sorted(jobs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    for job_dir in job_dirs[:10]:  # Top 10 recent jobs
        if not job_dir.is_dir():
            continue
        job_file = job_dir / "job.json"
        events_file = job_dir / "events.jsonl"

        if not job_file.exists():
            continue

        try:
            job_data = json.loads(job_file.read_text("utf-8", errors="replace"))
            state = job_data.get("state", "UNKNOWN")
            name = job_data.get("name", job_dir.name)
            created_at = job_data.get("created", "N/A")
            updated_at = job_data.get("updated", "N/A")

            # Count different event types
            event_counts = {
                "chunk_done": 0,
                "retry": 0,
                "error": 0,
                "watchdog": 0,
                "failover": 0,
            }
            if events_file.exists():
                for line in events_file.read_text(
                    "utf-8", errors="replace"
                ).splitlines():
                    if '"type": "chunk_done"' in line:
                        event_counts["chunk_done"] += 1
                    elif '"type": "retry"' in line:
                        event_counts["retry"] += 1
                    elif '"type": "error"' in line:
                        event_counts["error"] += 1
                    elif '"type": "watchdog"' in line:
                        event_counts["watchdog"] += 1
                    elif '"type": "failover"' in line:
                        event_counts["failover"] += 1

            summary = f"  - {job_dir.name[:12]}: {state:<10} | Created: {created_at} | Updated: {updated_at} | "
            summary += f"Chunks: {event_counts['chunk_done']:<3} | "
            summary += f"Retries: {event_counts['retry']:<2} | "
            summary += f"Errors: {event_counts['error']:<2} | "
            summary += f"Watchdog: {event_counts['watchdog']:<2} | "
            summary += f"Failovers: {event_counts['failover']:<2} | {name}"
            summaries.append(summary)
        except Exception as e:
            summaries.append(f"  - {job_dir.name[:12]}: (Error parsing job data: {e})")

    if not summaries:
        return "Jobs: (0 jobs found)\\n"

    return "Recent Jobs (top 10 most recent):\\n" + "\\n".join(summaries) + "\\n"


def build_manifest(files: List[Path]) -> str:
    """Build a manifest of files with their sizes and hashes."""
    manifest = ["Code Manifest (files included in snapshot):"]

    for file_path in files:
        try:
            content = file_path.read_bytes()
            digest = sha256_bytes(content)
            size = len(content)
            manifest.append(
                f"  {digest[:12]}  {size:>8} bytes  {file_path.relative_to(ROOT)}"
            )
        except Exception:
            manifest.append(
                f"  {'[ERROR]':<12}  {'ERROR':>8} bytes  {file_path.relative_to(ROOT)}"
            )

    return "\\n".join(manifest) + "\\n"


def build_system_info() -> str:
    """Build system information."""
    info = []
    info.append(f"System: {platform.system()}")
    info.append(f"Node: {platform.node()}")
    info.append(f"Release: {platform.release()}")
    info.append(f"Version: {platform.version()}")
    info.append(f"Machine: {platform.machine()}")
    info.append(f"Processor: {platform.processor()}")
    info.append(f"Python Version: {platform.python_version()}")
    info.append(f"Python Implementation: {platform.python_implementation()}")
    info.append(f"Working Directory: {os.getcwd()}")
    try:
        info.append(f"User: {os.getlogin()}")
    except OSError:
        info.append("User: N/A")
    info.append(f"Platform: {platform.platform()}")
    return "System Information:\\n" + "\\n".join(info) + "\\n"


def write_text_snapshot(
    out_path: Optional[str] = None,
    mode: str = "minimal",
    with_git: bool = False,
    with_jobs: bool = False,
    with_manifest: bool = False,
    git_tracked: bool = False,
    git_include_untracked: bool = False,
    include_system: bool = False,
    dry_run: bool = False,
    redact: bool = True,
    max_size: Optional[int] = None,
) -> None:
    """Write a text snapshot with optional context sections and file contents."""
    cfg = read_snapshot_config()
    if max_size is None:
        max_size = cfg.get("max_size", 262144)

    files = collect_paths(
        mode=mode,
        include_git_tracked=git_tracked,
        include_untracked=git_include_untracked,
    )

    if dry_run:
        print(f"Dry run: Would include {len(files)} files in snapshot")
        print(f"Mode: {mode}")
        print(f"Max file size: {max_size} bytes")
        print(f"With git: {with_git}")
        print(f"With jobs: {with_jobs}")
        print(f"With manifest: {with_manifest}")
        print(f"With system: {include_system}")
        print("Files that would be included:")
        for f in files[:20]:  # Show first 20 files
            print(f"  - {f}")
        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more files")
        return

    # Build context
    context_parts = [f"Generated on: {ts_utc()}"]
    if include_system:
        context_parts.append(build_system_info().rstrip())
    if with_git:
        context_parts.append(build_git_context().rstrip())
    if with_jobs:
        context_parts.append(build_jobs_summary().rstrip())
    if with_manifest:
        context_parts.append(build_manifest(files).rstrip())

    context_str = "\\n\\n".join([p for p in context_parts if p])

    # Write output
    output_path = Path(out_path) if out_path else Path("xsa_snapshot.txt")

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write("# XSArena Built-in Snapshot\\n")
        if context_str:
            f_out.write(context_str + "\\n\\n")

        # Write file contents
        for i, p in enumerate(files, 1):
            rp = rel_posix(p)
            f_out.write(f"--- START OF FILE {rp} ---\\n")
            try:
                b, truncated = safe_read_bytes(p, max_size)
                if is_binary_sample(b):
                    size = p.stat().st_size
                    digest = sha256_bytes(p.read_bytes())
                    f_out.write(f"[BINARY FILE] size={size} sha256={digest}\\n")
                else:
                    text = b.decode("utf-8", errors="replace")
                    if truncated:
                        text = f"[... FILE TRUNCATED to {max_size} bytes ...]\\n" + text
                    # Apply redaction if enabled
                    if redact and cfg.get("redact", True):
                        from ..core.redact import redact_snapshot_content

                        text = redact_snapshot_content(text)
                    f_out.write(text)
            except Exception as e:
                f_out.write(f"[ERROR READING FILE: {e}]")
            f_out.write(f"\\n--- END OF FILE {rp} ---\\n\\n")

    print(f"Text snapshot written to: {output_path}")


def write_zip_snapshot(
    out_path: Optional[str] = None,
    mode: str = "minimal",
    with_git: bool = False,
    with_jobs: bool = False,
    with_manifest: bool = False,
    git_tracked: bool = False,
    git_include_untracked: bool = False,
    include_system: bool = False,
    dry_run: bool = False,
    redact: bool = True,
    max_size: Optional[int] = None,
) -> None:
    """Write a zip snapshot with embedded files."""
    cfg = read_snapshot_config()
    if max_size is None:
        max_size = cfg.get("max_size", 262144)

    files = collect_paths(
        mode=mode,
        include_git_tracked=git_tracked,
        include_untracked=git_include_untracked,
    )

    if dry_run:
        print(f"Dry run: Would create zip with {len(files)} files")
        print(f"Mode: {mode}")
        print(f"Max file size: {max_size} bytes")
        print(f"With git: {with_git}")
        print(f"With jobs: {with_jobs}")
        print(f"With manifest: {with_manifest}")
        print(f"With system: {include_system}")
        return

    # Build context for snapshot.txt
    context_parts = [f"Generated on: {ts_utc()}"]
    if include_system:
        context_parts.append(build_system_info().rstrip())
    if with_git:
        context_parts.append(build_git_context().rstrip())
    if with_jobs:
        context_parts.append(build_jobs_summary().rstrip())
    if with_manifest:
        context_parts.append(build_manifest(files).rstrip())

    context_str = "\\n\\n".join([p for p in context_parts if p])

    output_path = Path(out_path) if out_path else Path("xsa_snapshot.zip")

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Create snapshot.txt manifest
        manifest = []
        manifest.append("# XSArena Built-in Snapshot")
        manifest.append(context_str)
        manifest.append(f"\\n--- MANIFEST ({len(files)} files) ---")
        for p in files:
            try:
                size = p.stat().st_size
                manifest.append(f"{size:>8} {rel_posix(p)}")
            except Exception:
                manifest.append(f"{'ERROR':>8} {rel_posix(p)}")
        manifest.append("\\n--- END OF SNAPSHOT ---")

        z.writestr("snapshot.txt", "\\n".join(manifest))

        # Add the selected files to the zip
        for i, p in enumerate(files, 1):
            rp = rel_posix(p)
            try:
                b, truncated = safe_read_bytes(p, max_size)
                if is_binary_sample(b):
                    # Store as binary file
                    z.writestr(rp, b)
                    # Also add metadata
                    meta_content = f"# BINARY FILE\\npath: {rp}\\nsize: {p.stat().st_size}\\nsha256: {sha256_bytes(p.read_bytes())}\\n"
                    z.writestr(rp + ".meta", meta_content)
                else:
                    # Store as text
                    text = b.decode("utf-8", errors="replace")
                    if truncated:
                        text = f"[... FILE TRUNCATED to {max_size} bytes ...]\\n" + text
                    # Apply redaction if enabled
                    if redact and cfg.get("redact", True):
                        from ..core.redact import redact_snapshot_content

                        text = redact_snapshot_content(text)
                    z.writestr(rp, text)
            except Exception as e:
                z.writestr(rp + ".error", f"[ERROR READING FILE: {e}]")

    print(f"Zip snapshot written to: {output_path}")


def write_pro_snapshot(
    out_path: Optional[str] = None,
    max_inline: int = 100000,
    include_system: bool = True,
    include_git: bool = True,
    include_jobs: bool = True,
    include_manifest: bool = True,
    include_rules: bool = True,
    include_reviews: bool = True,
    include_digest: bool = True,
    mode: str = "standard",
    dry_run: bool = False,
    redact: bool = True,
) -> None:
    """Write a pro snapshot with enhanced debugging capabilities."""

    cfg = read_snapshot_config()
    max_size = cfg.get("max_size", 262144)

    files = collect_paths(mode=mode)

    if dry_run:
        print(f"Dry run: Would create pro snapshot with {len(files)} files")
        print(f"Max inline: {max_inline} bytes")
        print(f"Include system: {include_system}")
        print(f"Include git: {include_git}")
        print(f"Include jobs: {include_jobs}")
        print(f"Include manifest: {include_manifest}")
        print(f"Include rules: {include_rules}")
        print(f"Include reviews: {include_reviews}")
        print(f"Include digest: {include_digest}")
        return

    # Build context
    context_parts = [f"Generated on: {ts_utc()}"]
    if include_system:
        context_parts.append(build_system_info().rstrip())
    if include_git:
        context_parts.append(build_git_context().rstrip())
    if include_jobs:
        context_parts.append(build_jobs_summary().rstrip())
    if include_manifest:
        context_parts.append(build_manifest(files).rstrip())

    # Additional pro-specific sections
    if include_rules:
        context_parts.append(get_rules_digest().rstrip())
    if include_reviews:
        context_parts.append(get_review_artifacts().rstrip())

    context_str = "\\n\\n".join([p for p in context_parts if p])

    # Prepare the content
    content_parts = ["# XSArena Pro Built-in Snapshot"]
    if context_str:
        content_parts.append(context_str)

    # Add file contents
    for i, p in enumerate(files, 1):
        rp = rel_posix(p)
        content_parts.append(f"--- START OF FILE {rp} ---")
        try:
            b, truncated = safe_read_bytes(p, max_size)
            if is_binary_sample(b):
                size = p.stat().st_size
                digest = sha256_bytes(p.read_bytes())
                content_parts.append(f"[BINARY FILE] size={size} sha256={digest}")
            else:
                text = b.decode("utf-8", errors="replace")
                if truncated:
                    text = f"[... FILE TRUNCATED to {max_size} bytes ...]\\n" + text
                # Apply redaction if enabled
                if redact and cfg.get("redact", True):
                    from ..core.redact import redact_snapshot_content

                    text = redact_snapshot_content(text)
                content_parts.append(text)
        except Exception as e:
            content_parts.append(f"[ERROR READING FILE: {e}]")
        content_parts.append(f"--- END OF FILE {rp} ---\\n")

    # Join all content
    full_content = "\\n".join(content_parts)

    # Add digest if required
    if include_digest:
        digest = sha256_bytes(full_content.encode("utf-8"))
        full_content += (
            f"\\nSnapshot Integrity Digest (SHA256 of entire snapshot): {digest}\\n"
        )

    # Write the output
    output_path = (
        Path(out_path) if out_path else Path("~/xsa_snapshot_pro.txt").expanduser()
    )

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write(full_content)

    print(f"Pro snapshot written to: {output_path}")


def get_rules_digest() -> str:
    """Get canonical rules digest."""
    rules_file = ROOT / "rules.merged.md"
    if not rules_file.exists():
        return "Rules Digest: (rules.merged.md not found)\\n"

    try:
        content, truncated = safe_read_text(rules_file, 10000)  # Read first 10000 chars
        lines = content.splitlines()
        first_200_lines = "\\n".join(lines[:200])
        digest = sha256_bytes(first_200_lines.encode("utf-8"))

        return f"Rules Digest (SHA256 of first 200 lines of rules.merged.md):\\n{digest}\\nFirst 200 lines preview:\\n{first_200_lines}\\n"
    except Exception as e:
        return f"Rules Digest: (Error reading rules.merged.md: {e})\\n"


def get_review_artifacts() -> str:
    """Get review artifacts if they exist."""
    review_dir = ROOT / "review"
    if not review_dir.exists():
        return "Review Artifacts: (review/ directory not found)\\n"

    artifacts = []
    for item in review_dir.iterdir():
        if item.is_file():
            try:
                content, truncated = safe_read_text(
                    item, 5000
                )  # Limit to first 5000 chars
                digest = sha256_bytes(content.encode("utf-8"))
                artifacts.append(f"  {digest[:12]}  {item.name} (first 5000 chars)")
            except Exception:
                artifacts.append(f"  {'[ERROR]':<12}  {item.name}")
        elif item.is_dir():
            artifacts.append(f"  [DIR]       {item.name}/")

    return "Review Artifacts:\\n" + "\\n".join(artifacts) + "\\n"


def get_snapshot_digest(output_content: str) -> str:
    """Get combined snapshot digest for integrity verification."""
    return f"Snapshot Integrity Digest (SHA256 of entire snapshot): {sha256_bytes(output_content.encode('utf-8'))}\\n"


def render_directory_tree(
    path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0
) -> str:
    """Render a directory tree up to a specified depth."""
    if current_depth > max_depth:
        return ""

    tree_lines = []
    if current_depth == 0:
        tree_lines.append(f"{path.name}/")
    else:
        tree_lines.append(f"{prefix}├── {path.name}/")

    if path.is_dir():
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "

            if item.is_dir():
                if current_depth < max_depth:
                    tree_lines.append(f"{prefix}{extension}{connector}{item.name}/")
                    tree_lines.append(
                        render_directory_tree(
                            item, prefix + extension, max_depth, current_depth + 1
                        )
                    )
            else:
                tree_lines.append(f"{prefix}{extension}{connector}{item.name}")

    return "\\n".join(line for line in tree_lines if line)


def get_directory_listings() -> str:
    """Get directory listings for important paths."""
    important_paths = [
        ROOT / "src",
        ROOT / "docs",
        ROOT / "directives",
        ROOT / "recipes",
        ROOT / "tools",
        ROOT / "data",
        ROOT / ".xsarena",
    ]

    listings = []
    for path in important_paths:
        if path.exists():
            listings.append(f"\\nDirectory listing for {path.name}/:")
            listings.append(render_directory_tree(path, max_depth=2))

    return "Directory Listings:\\n" + "\\n".join(listings) + "\\n"
