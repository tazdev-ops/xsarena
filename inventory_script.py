#!/usr/bin/env python3
"""
Script to inventory repository files and capture metrics
"""
import os
from collections import Counter
from pathlib import Path


def main():
    # Read the tracked files list
    with open("tracked_files.txt", "r") as f:
        tracked_files = [line.strip() for line in f.readlines()]

    # Filter to only files that actually exist
    existing_files = [f for f in tracked_files if os.path.isfile(f)]

    # Calculate total size
    total_size = sum(os.path.getsize(f) for f in existing_files)

    # Get top 20 largest files
    files_with_sizes = [(f, os.path.getsize(f)) for f in existing_files]
    largest_files = sorted(files_with_sizes, key=lambda x: x[1], reverse=True)[:20]

    # Count files by extension
    extensions = Counter()
    for file_path in existing_files:
        ext = Path(file_path).suffix.lower()
        extensions[ext] += 1

    # Write inventory summary
    with open("inventory_summary.txt", "w") as f:
        f.write(f"Total file count: {len(existing_files)}\n")
        f.write(
            f"Total size: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)\n\n"
        )

        f.write("Top 20 largest files:\n")
        for file_path, size in largest_files:
            f.write(f"  {size} bytes: {file_path}\n")

        f.write("\nFile counts by extension:\n")
        for ext, count in extensions.most_common():
            f.write(f"  {ext}: {count}\n")

    print(f"Total file count: {len(existing_files)}")
    print(f"Total size: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)")
    print("\nTop 20 largest files:")
    for _, (file_path, size) in enumerate(largest_files[:10]):  # Show top 10
        print(f"  {size} bytes: {file_path}")
    print("\nFile counts by extension (top 10):")
    for ext, count in list(extensions.most_common(10)):
        print(f"  {ext}: {count}")


if __name__ == "__main__":
    main()
