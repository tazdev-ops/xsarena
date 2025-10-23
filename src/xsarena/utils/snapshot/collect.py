"""File collection utilities for snapshot operations."""

import glob
import hashlib
import subprocess
from pathlib import Path
from typing import List, Sequence, Set, Tuple

# Import shared helpers
from .helpers import apply_redaction


# Optional redact
def _load_redact():
    try:
        from ...core.redact import redact as _redact

        return _redact
    except Exception:
        # Use the apply_redaction helper with default patterns
        return apply_redaction


REDACT = _load_redact()


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
    "src/xsarena/core/manifest.py",
    "src/xsarena/core/v2_orchestrator/orchestrator.py",
    "src/xsarena/core/v2_orchestrator/specs.py",
    "src/xsarena/core/jobs/model.py",
    "src/xsarena/core/jobs/executor_core.py",
    "src/xsarena/core/jobs/chunk_processor.py",
    "src/xsarena/core/jobs/scheduler.py",
    "src/xsarena/core/jobs/store.py",
    "src/xsarena/core/state.py",
    "src/xsarena/core/config.py",
    "src/xsarena/core/backends/bridge_v2.py",
    "src/xsarena/bridge_v2/api_server.py",
    "src/xsarena/bridge_v2/handlers.py",
    "src/xsarena/bridge_v2/websocket.py",
    "src/xsarena/bridge_v2/payload_converter.py",
    "src/xsarena/bridge_v2/streams.py",
    "src/xsarena/bridge_v2/formatters.py",
    "src/xsarena/bridge_v2/config_loaders.py",
    "src/xsarena/bridge_v2/cors.py",
    "src/xsarena/bridge_v2/app_lifecycle.py",
    "src/xsarena/bridge_v2/job_service.py",
    "src/xsarena/core/chunking.py",
    "src/xsarena/core/engine.py",
    "src/xsarena/utils/discovery.py",
    "src/xsarena/utils/project_paths.py",
    "src/xsarena/utils/helpers.py",
    "src/xsarena/utils/io.py",
    "src/xsarena/utils/density.py",
    "src/xsarena/core/jobs/helpers.py",
    "src/xsarena/core/jobs/errors.py",
    "src/xsarena/core/jobs/resume_handler.py",
    "src/xsarena/core/jobs/processing/extension_handler.py",
    "src/xsarena/core/jobs/processing/metrics_tracker.py",
]


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


def _git_ls_files(args: List[str]) -> Set[Path]:
    try:
        cp = subprocess.run(
            ["git"] + args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
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
            return (
                data.decode("utf-8", errors="replace") + "\n--- TRUNCATED ---\n",
                True,
            )
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


def _posix(path: Path) -> str:
    """Convert path to POSIX format (forward slashes)."""
    return "/".join(path.parts)


def _is_excluded(path: str, excludes: Sequence[str]) -> bool:
    """Check if a path matches any exclude pattern."""
    from fnmatch import fnmatch

    return any(fnmatch(path, pattern) for pattern in excludes)
