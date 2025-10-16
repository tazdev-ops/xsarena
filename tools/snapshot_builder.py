#!/usr/bin/env python3
"""
Minimal snapshot tool for XSArena.
Creates a single-file snapshot with only the most essential files (~400KB).
"""
import sys
from datetime import datetime
from pathlib import Path


def create_minimal_snapshot(output_path: Path = None):
    if output_path is None:
        output_path = Path.home() / "xsa_min_snapshot.txt"

    # Store the original working directory
    original_cwd = Path.cwd()

    # Open the output file for writing
    with open(output_path, "w", encoding="utf-8") as outfile:
        outfile.write("# XSArena Minimal Snapshot\n")
        outfile.write(f"# Generated on: {datetime.now().isoformat()}\n")
        outfile.write(f"# Project root: {original_cwd}\n\n")

        # Add project definition files
        essential_files = [
            "pyproject.toml",
            "README.md",
            "mypy.ini",
            "config.jsonc",
            "models.json",
            "model_endpoint_map.json",
        ]

        for file_path_str in essential_files:
            file_path = original_cwd / file_path_str
            if file_path.exists() and file_path.is_file():
                add_file_to_snapshot(outfile, file_path, original_cwd)

        # Add core source files
        core_dirs = ["src/xsarena/cli", "src/xsarena/core", "src/xsarena/bridge_v2"]
        for dir_name in core_dirs:
            dir_path = original_cwd / dir_name
            if dir_path.exists():
                for file_path in dir_path.rglob("*.py"):
                    if file_path.is_file():
                        add_file_to_snapshot(outfile, file_path, original_cwd)

        # Add bridge userscript
        bridge_script = original_cwd / "src/xsarena/bridge/userscript_example.js"
        if bridge_script.exists():
            add_file_to_snapshot(outfile, bridge_script, original_cwd)

        # Add essential test files
        test_dir = original_cwd / "tests"
        if test_dir.exists():
            for file_path in test_dir.rglob("*.py"):
                if file_path.is_file():
                    # Only include key test files
                    if (
                        "smoke" in str(file_path)
                        or "imports" in str(file_path)
                        or "backends" in str(file_path)
                    ):
                        add_file_to_snapshot(outfile, file_path, original_cwd)

        # Add key tool
        id_updater = original_cwd / "tools/id_updater.py"
        if id_updater.exists():
            add_file_to_snapshot(outfile, id_updater, original_cwd)

        # Add key scripts
        script_dir = original_cwd / "scripts"
        if script_dir.exists():
            for file_path in script_dir.rglob("*.sh"):
                if file_path.is_file():
                    add_file_to_snapshot(outfile, file_path, original_cwd)

        # Add rules files
        directives_dir = original_cwd / "directives"
        if directives_dir.exists():
            for file_path in directives_dir.rglob("*.md"):
                if file_path.is_file():
                    add_file_to_snapshot(outfile, file_path, original_cwd)

    print(f"Minimal snapshot created at: {output_path}")


def add_file_to_snapshot(outfile, file_path, project_root):
    """Helper function to add a single file to the snapshot"""
    if file_path.exists() and file_path.is_file():
        try:
            # Get the relative path from the project root
            relative_path = file_path.relative_to(project_root)
            # Skip if it's in an excluded directory
            rel_path_str = str(relative_path)
            if not any(
                excl in rel_path_str
                for excl in [
                    "/legacy/",
                    "/__pycache__/",
                    "/snapshot/",
                    "/gomobile-matsuri-src/",
                ]
            ):
                outfile.write(f"--- START OF FILE {relative_path} ---\n")
                content = file_path.read_text(encoding="utf-8")
                outfile.write(content)
                outfile.write("\n")
                outfile.write(f"--- END OF FILE {relative_path} ---\n\n")
        except ValueError:
            # If the file is not relative to the project root, skip it
            pass
        except Exception as e:
            outfile.write(f"# Error reading file {file_path}: {e}\n")


if __name__ == "__main__":
    output_path = None
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
    create_minimal_snapshot(output_path)
