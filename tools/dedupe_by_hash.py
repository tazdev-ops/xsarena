#!/usr/bin/env python3
"""
Portable deduplication by hash - removes duplicate files by keeping the newest one.
This is the Python equivalent of the old bash script for cross-platform compatibility.
"""

import sys
from pathlib import Path


def dedupe_by_hash(apply_changes=False):
    """
    Remove duplicate files by hash, keeping the newest file.

    Args:
        apply_changes (bool): If True, actually move files to archive. If False, dry-run.
    """
    # Check if required files exist
    dup_hashes_path = Path("review/dup_hashes.txt")
    books_sha256_path = Path("review/books_sha256.txt")

    if not dup_hashes_path.exists():
        print(f"Error: {dup_hashes_path} not found")
        sys.exit(1)

    if not books_sha256_path.exists():
        print(f"Error: {books_sha256_path} not found")
        sys.exit(1)

    # Read duplicate hashes
    with open(dup_hashes_path, "r", encoding="utf-8") as f:
        dup_hashes = [line.strip() for line in f if line.strip()]

    for hash_val in dup_hashes:
        # Get files for this hash using pure Python instead of grep
        lines_for_hash = []
        with open(books_sha256_path, "r", encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip().startswith(f"{hash_val} "):
                    lines_for_hash.append(ln.rstrip("\n"))

        if not lines_for_hash:
            continue

        files = []
        for ln in lines_for_hash:
            parts = ln.split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1])

        if len(files) < 2:
            continue  # Need at least 2 files to have duplicates

        # Find the file with the newest modification time using Path.stat()
        keep = ""
        newest_mtime = 0
        for f in files:
            try:
                mt = Path(f).stat().st_mtime
            except Exception:
                mt = 0

            if mt > newest_mtime:
                newest_mtime = mt
                keep = f

        # Archive duplicates
        for f in files:
            if f == keep:
                continue
            print(f"archive dup: {f} (keep: {keep})")
            if apply_changes:
                import os
                import shutil

                os.makedirs("books/archive", exist_ok=True)
                try:
                    # Try git mv first, then regular mv
                    import subprocess

                    result = subprocess.run(
                        ["git", "mv", f, f"books/archive/{os.path.basename(f)}"],
                        capture_output=True,
                    )
                    if result.returncode != 0:
                        # If git mv fails, use regular mv
                        shutil.move(f, f"books/archive/{os.path.basename(f)}")
                except Exception:
                    shutil.move(f, f"books/archive/{os.path.basename(f)}")

    if not apply_changes:
        print("Dry-run. Re-run with APPLY=1 to apply changes.")


if __name__ == "__main__":
    apply_changes = len(sys.argv) > 1 and sys.argv[1] == "APPLY=1"
    dedupe_by_hash(apply_changes)
