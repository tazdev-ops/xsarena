#!/usr/bin/env python3
# scripts/snapshot_py_only.py
# Minimal snapshot: concat all .py files from given dirs into one file.
# Usage:
#   python scripts/snapshot_py_only.py                # defaults: src legacy contrib scripts
#   python scripts/snapshot_py_only.py DIR... -o out.txt

import sys
from pathlib import Path

DEFAULT_DIRS = ["src", "legacy", "contrib", "scripts"]
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".xsarena",
    "books",
    "snapshot_chunks",
    "dist",
    "build",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}


def parse_args(argv):
    out = "snapshot_py.txt"
    dirs = []
    i = 0
    while i < len(argv):
        if argv[i] == "-o" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 2
        else:
            dirs.append(argv[i])
            i += 1
    if not dirs:
        dirs = DEFAULT_DIRS[:]
    return dirs, out


def should_skip(path: Path) -> bool:
    # Skip if any parent directory is in SKIP_DIRS
    return any(part in SKIP_DIRS for part in path.parts)


def collect_py_files(root: Path, dirs):
    files = set()
    for d in dirs:
        p = (root / d).resolve()
        if not p.exists():
            continue
        if p.is_file() and p.suffix == ".py" and not should_skip(p):
            files.add(p)
            continue
        if p.is_dir():
            # Walk with simple filter using rglob; filter by SKIP_DIRS
            for f in p.rglob("*.py"):
                if f.is_file() and not should_skip(f):
                    files.add(f.resolve())
    # Also include top-level .py if user passed "."
    return sorted(files, key=lambda x: x.as_posix())


def main():
    root = Path(".").resolve()
    dirs, out_path = parse_args(sys.argv[1:])
    files = collect_py_files(root, dirs)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8", errors="replace", newline="\n") as w:
        w.write("=== PY SNAPSHOT ===\n")
        w.write(f"ROOT: {root}\n")
        w.write(f"DIRS: {', '.join(dirs)}\n")
        w.write(f"FILES: {len(files)}\n\n")
        for f in files:
            rel = f.relative_to(root)
            w.write(f"--- BEGIN FILE {rel} ---\n")
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                txt = f"[Error reading {rel}: {e}]\n"
            w.write(txt)
            if not txt.endswith("\n"):
                w.write("\n")
            w.write(f"--- END FILE {rel} ---\n\n")

    print(f"✅ Wrote → {out}  (files: {len(files)})")


if __name__ == "__main__":
    main()
