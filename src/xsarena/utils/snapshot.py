"""
Pure-Python snapshot utility to replicate snapshot.sh functionality without bash dependencies.
This allows XSArena to work on Windows and other platforms without shell requirements.
"""

import os
from pathlib import Path
from typing import Dict


def create_snapshot(project_root: str, chunk: bool = False, chunk_size: int = 100_000) -> Dict[str, int]:
    """
    Create a project snapshot replicating snapshot.sh functionality in pure Python.

    Args:
        project_root: Root directory of the project
        chunk: Whether to chunk the output into multiple files
        chunk_size: Maximum size of each chunk in characters

    Returns:
        Dict with summary: {"files": N, "dirs": M, "chunks": K}
    """
    project_path = Path(project_root)

    # Define exclusions to match the shell script
    EXCLUDE_DIRS = {
        ".git",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        ".pytest_cache",
        ".vscode",
        "venv",
        "env",
        ".env",
        ".ruff_cache",
        "books",
        "tests",
        "snapshot_chunks",
        ".lint",
        ".lmastudio",
        "packaging",
    }

    EXCLUDE_PATHS = {"nexus.txt", "available_models.json", "snapshot.txt", "snapshot_chunks", "snapshot_part_*"}

    RELEVANT_EXTS = {".py", ".sh", ".json", ".toml", ".md", ".txt", ".yaml", ".yml"}

    # Collect directories
    all_dirs = set()
    all_files = []

    for root, dirs, files in os.walk(project_path):
        # Remove excluded directories in-place to avoid traversing them
        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDE_DIRS and not any(part in EXCLUDE_DIRS for part in Path(root).joinpath(d).parts)
        ]

        for file in files:
            file_path = Path(root).joinpath(file)

            # Check if file path or any parent directory is in exclusions
            if any(part in EXCLUDE_DIRS for part in file_path.parts) or file_path.name in EXCLUDE_PATHS:
                continue

            all_files.append(str(file_path.relative_to(project_path)))
            all_dirs.update([str(parent.relative_to(project_path)) for parent in file_path.parents])

    collect_dirs = sorted(list(all_dirs))
    collect_files = sorted(all_files)
    collect_relevant = [f for f in collect_files if Path(f).suffix.lower() in RELEVANT_EXTS]

    # Build the snapshot content
    snapshot_content = []

    # Directory structure section
    snapshot_content.append("Project Directory Structure:\n")
    snapshot_content.append("=" * 50 + "\n")
    for directory in collect_dirs:
        snapshot_content.append(f"{directory}/\n")

    # Project files section
    snapshot_content.append("\n\nProject Files:\n")
    snapshot_content.append("=" * 50 + "\n")
    for file_path in collect_files:
        snapshot_content.append(f"{file_path}\n")

    # Relevant code files section with content
    snapshot_content.append("\n\nRelevant Code Files:\n")
    snapshot_content.append("=" * 50 + "\n")

    for file_path in collect_relevant:
        full_path = project_path.joinpath(file_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                try:
                    content = f.read()
                except UnicodeDecodeError:
                    # If there's an issue reading as UTF-8, try with error handling
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

            snapshot_content.append(f"\n--- {file_path} ---\n")
            snapshot_content.append(content)
            snapshot_content.append("\n--- End of content ---\n")
        except Exception:
            # Skip files that can't be read
            continue

    full_content = "".join(snapshot_content)

    if chunk:
        # Create snapshot_chunks directory if it doesn't exist
        chunks_dir = project_path.joinpath("snapshot_chunks")
        chunks_dir.mkdir(exist_ok=True)

        # Clear existing chunks
        for chunk_file in chunks_dir.glob("snapshot_part_*"):
            chunk_file.unlink()

        # Split content into chunks
        chunks = []
        for i in range(0, len(full_content), chunk_size):
            chunk = full_content[i : i + chunk_size]
            chunks.append(chunk)

        # Write chunks with the requested message
        for i, chunk in enumerate(chunks):
            chunk_filename = f"snapshot_part_{i:02d}"
            chunk_path = chunks_dir.joinpath(chunk_filename)
            with open(chunk_path, "w", encoding="utf-8") as f:
                f.write(chunk)
                # Add the required message to each chunk
                f.write('\nSay "received." after this message. DO nothing else.')

        # Write main snapshot.txt as well
        with open(project_path.joinpath("snapshot.txt"), "w", encoding="utf-8") as f:
            f.write(full_content)

        result = {"files": len(collect_files), "dirs": len(collect_dirs), "chunks": len(chunks)}
    else:
        # Write single snapshot file
        with open(project_path.joinpath("snapshot.txt"), "w", encoding="utf-8") as f:
            f.write(full_content)

        result = {"files": len(collect_files), "dirs": len(collect_dirs), "chunks": 1 if chunk else 0}

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create a project snapshot")
    parser.add_argument("--chunk", "-c", action="store_true", help="Create chunked output")
    parser.add_argument("--chunk-size", type=int, default=100000, help="Size of each chunk")
    parser.add_argument("--project-root", default=".", help="Project root directory")

    args = parser.parse_args()

    result = create_snapshot(project_root=args.project_root, chunk=args.chunk, chunk_size=args.chunk_size)

    print("Snapshot created: snapshot.txt")
    if args.chunk:
        print(f"Chunks created: {result['chunks']} files in snapshot_chunks/")
    print(f"Summary: {result['files']} files, {result['dirs']} directories")
