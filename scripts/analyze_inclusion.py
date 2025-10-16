#!/usr/bin/env python3
"""
File inclusion methodology for XSArena snapshot utility.

This script analyzes the project and creates a list of files that should be
included in a ~400KB snapshot, focusing on source code, configuration,
documentation, and important project state without generated outputs.
"""

from pathlib import Path


def analyze_project():
    root = Path(".")

    # Categories of files to include
    important_categories = {
        "source_code": [],
        "config": [],
        "docs": [],
        "recipes": [],
        "scripts": [],
        "directives": [],
        "tools": [],
        "tests": [],
        "root_files": [],
        "xsarena_config": [],
    }

    # Source code
    for p in (root / "src").rglob("*"):
        if p.is_file() and p.suffix in [".py", ".md", ".txt"]:
            important_categories["source_code"].append(str(p))

    # Configuration files
    config_patterns = ["*.toml", "*.yml", "*.yaml", "*.json", "*.ini", "*.cfg"]
    for pattern in config_patterns:
        for p in root.glob(pattern):
            if p.is_file():
                important_categories["config"].append(str(p))

    # Root documentation files
    doc_patterns = ["*.md"]
    for pattern in doc_patterns:
        for p in root.glob(pattern):
            if p.is_file() and p.name not in [
                "snapshot_*.txt",
                "situation_report*.txt",
            ]:
                important_categories["root_files"].append(str(p))

    # Docs directory
    for p in (root / "docs").rglob("*"):
        if p.is_file() and p.suffix in [".md", ".txt"]:
            important_categories["docs"].append(str(p))

    # Recipes
    for p in (root / "recipes").rglob("*.yml"):
        if p.is_file():
            important_categories["recipes"].append(str(p))

    # Scripts
    for p in (root / "scripts").rglob("*.sh"):
        if p.is_file():
            important_categories["scripts"].append(str(p))
    for p in (root / "scripts").rglob("*.py"):
        if p.is_file():
            important_categories["scripts"].append(str(p))

    # Directives
    for p in (root / "directives").rglob("*"):
        if p.is_file() and p.suffix in [".md", ".txt", ".json.md"]:
            # Skip output directories within directives
            if "checkpoints" not in str(p) and "jobs" not in str(p):
                important_categories["directives"].append(str(p))

    # Tools
    for p in (root / "tools").rglob("*.py"):
        if p.is_file():
            important_categories["tools"].append(str(p))

    # Tests
    for p in (root / "tests").rglob("*.py"):
        if p.is_file():
            important_categories["tests"].append(str(p))

    # .xsarena config files (not checkpoints or jobs)
    xsarena_dir = root / ".xsarena"
    if xsarena_dir.exists():
        for p in xsarena_dir.iterdir():
            if p.is_file() or (
                p.is_dir() and p.name not in ["checkpoints", "jobs", "snapshots"]
            ):
                if p.is_file():
                    important_categories["xsarena_config"].append(str(p))
                elif p.is_dir():
                    for sub_p in p.rglob("*"):
                        if sub_p.is_file() and sub_p.name not in [
                            "checkpoints",
                            "jobs",
                            "snapshots",
                        ]:
                            important_categories["xsarena_config"].append(str(sub_p))

    # Calculate total size
    total_size = 0
    all_files = []
    for category, files in important_categories.items():
        for file_path in files:
            try:
                size = Path(file_path).stat().st_size
                total_size += size
                all_files.append((file_path, size))
            except:
                continue  # Skip files that can't be accessed

    print(f"Estimated total size: {total_size / 1024:.1f} KB")
    print(f"Total files to include: {len(all_files)}")

    # Sort by size to see largest files
    largest_files = sorted(all_files, key=lambda x: x[1], reverse=True)[:20]
    print("\nLargest files to include:")
    for path, size in largest_files:
        print(f"  {path}: {size/1024:.1f}KB")

    return important_categories, total_size, all_files


if __name__ == "__main__":
    categories, total_size, all_files = analyze_project()
