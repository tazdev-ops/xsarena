#!/usr/bin/env python3
"""
Minimal snapshot (chunked):
- Includes only *.py and *.md
- From dirs: src, docs, directives, tests (override with --dirs)
- Writes chunked text files to .xsarena/snapshots/ (override with --out-dir)
- Nothing fancy.

Usage:
  python tools/snapshot_min_simple.py
  python tools/snapshot_min_simple.py --dirs src docs --chunk-bytes 120000 --out-dir .xsarena/snapshots --prefix simple_snapshot
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
from typing import Iterable, List

DEFAULT_DIRS = ["src", "docs", "directives", "tests"]
ALLOWED_EXTS = {".py", ".md"}

def find_files(dirs: Iterable[str]) -> List[Path]:
    files: List[Path] = []
    cwd = Path.cwd()
    for d in dirs:
        root = cwd / d
        if not root.exists() or not root.is_dir():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in ALLOWED_EXTS:
                try:
                    files.append(p.relative_to(cwd))
                except Exception:
                    files.append(p)
    files.sort(key=lambda p: str(p).lower())
    return files

def build_content(paths: List[Path]) -> str:
    parts: List[str] = []
    parts.append("==== SIMPLE SNAPSHOT (py+md only) ====\n")
    parts.append(f"Working dir: {os.getcwd()}\n")
    parts.append(f"Files: {len(paths)}\n\n")
    for p in paths:
        parts.append(f"----- BEGIN {p} -----\n")
        try:
            txt = Path(p).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            txt = f"[error reading file: {e}]"
        parts.append(txt.rstrip("\n") + "\n")
        parts.append(f"----- END {p} -----\n\n")
    return "".join(parts)

def write_chunks(data: bytes, out_dir: Path, prefix: str, chunk_bytes: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(data)
    if total == 0:
        # Still write an empty single chunk
        (out_dir / f"{prefix}__chunk1-of-1.txt").write_text("", encoding="utf-8")
        return
    n = (total + chunk_bytes - 1) // chunk_bytes
    for i in range(n):
        start = i * chunk_bytes
        end = min((i + 1) * chunk_bytes, total)
        part = data[start:end]
        # decode safely; it's fine to ignore a dangling partial UTF-8 at edges
        text = part.decode("utf-8", errors="ignore")
        (out_dir / f"{prefix}__chunk{i+1}-of-{n}.txt").write_text(text, encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Minimal snapshot (chunked) for *.py and *.md only.")
    ap.add_argument("--dirs", nargs="*", default=DEFAULT_DIRS, help="Dirs to include (default: src docs directives tests)")
    ap.add_argument("--out-dir", default=".xsarena/snapshots", help="Output directory")
    ap.add_argument("--prefix", default="simple_snapshot", help="Output filename prefix")
    ap.add_argument("--chunk-bytes", type=int, default=100_000, help="Chunk size in bytes")
    args = ap.parse_args()

    paths = find_files(args.dirs)
    content = build_content(paths)
    data = content.encode("utf-8")
    write_chunks(data, Path(args.out_dir), args.prefix, args.chunk_bytes)
    print(f"Wrote {len(paths)} files into chunked snapshot at {args.out_dir}/ (prefix: {args.prefix})")

if __name__ == "__main__":
    main()