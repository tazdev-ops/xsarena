#!/usr/bin/env python3

from pathlib import Path


def build_maximal_snapshot():
    snapshot_content = []

    # Add Python files
    py_files = list(Path("src").rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f)]

    # Take first 40 Python files
    for file_path in py_files[:40]:
        snapshot_content.append(f"=== START FILE: {file_path} ===")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Take first 100 lines to keep reasonable size
                content = "".join(lines[:100])
                snapshot_content.append(content.rstrip())
        except Exception as e:
            snapshot_content.append(f"# Error reading file: {e}")
        snapshot_content.append(f"=== END FILE: {file_path} ===")
        snapshot_content.append("")

    # Add important non-Python files
    for file_path in [
        "pyproject.toml",
        "README.md",
        "COMMANDS_REFERENCE.md",
        "MODULES.md",
    ]:
        if Path(file_path).exists():
            snapshot_content.append(f"=== START FILE: {file_path} ===")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    content = "".join(lines[:100])  # First 100 lines
                    snapshot_content.append(content.rstrip())
            except Exception as e:
                snapshot_content.append(f"# Error reading file: {e}")
            snapshot_content.append(f"=== END FILE: {file_path} ===")
            snapshot_content.append("")

    # Write to snapshot file
    with open("xsa_maximal_snapshot.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(snapshot_content))

    print(f"Snapshot created with {len(snapshot_content)} entries")


if __name__ == "__main__":
    build_maximal_snapshot()
