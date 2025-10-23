#!/usr/bin/env python3
import fnmatch
import hashlib
import json
from pathlib import Path

ROOT = Path(".").resolve()
IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".mypy_cache",
    ".xsarena/jobs",
    ".xsarena/tmp",
}

CANDIDATE_REMOVE = [
    # Backup and duplicate patterns
    "src/**/pack_txt.py.backup",
    # Empty/placeholder modules: only if unused
    "src/xsarena/core/jobs/executor.py",
    # Streams module is duplicated functionality (handlers inline). Only if unused.
    "src/xsarena/bridge_v2/streams.py",
    # Generated help docs: keep generated, but not required to track in repo
    "docs/_help_*.txt",
]


def walk_files():
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        parts = set(p.parts)
        if parts & IGNORE_DIRS:
            continue
        yield p


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def match_any(path: Path, globs):
    rel = path.as_posix()
    return any(fnmatch.fnmatch(rel, pat) for pat in globs)


def referenced(relpath: str) -> bool:
    # Simple static greps to see if code references it anywhere; agent can augment
    # We check by filename stem too (import usage)
    import shlex
    import subprocess

    try:
        cmd = f"rg -n --hidden --glob '!{relpath}' '{relpath.split('/')[-1]}'"
        res = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        return bool(res.stdout.strip())
    except Exception:
        return True  # conservative


def main():
    total = 0
    largest = []
    for p in walk_files():
        total += p.stat().st_size
        largest.append((p.as_posix(), p.stat().st_size))
    largest.sort(key=lambda t: t[1], reverse=True)

    # Debloat candidates
    candidates = []
    for pat in CANDIDATE_REMOVE:
        for p in ROOT.glob(pat):
            if not p.exists() or not p.is_file():
                continue
            # Investigate references
            rel = p.as_posix()
            is_ref = referenced(rel)
            candidates.append(
                {"path": rel, "bytes": p.stat().st_size, "referenced": is_ref}
            )

    print(
        json.dumps(
            {
                "total_bytes": total,
                "top20_largest": largest[:20],
                "candidates": candidates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
