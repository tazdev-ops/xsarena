#!/usr/bin/env python3
"""
Simple snapshot generator that walks the repo tree and concatenates text/code files.
This is the default method for producing snapshots as per the rulebook.
"""
import os
import sys
from pathlib import Path


def is_text_file(filepath):
    """Check if a file is likely a text file based on extension."""
    text_extensions = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".cfg",
        ".ini",
        ".txt",
        ".md",
        ".rst",
        ".xml",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".kts",
        ".scala",
        ".pl",
        ".pm",
        ".t",
        ".r",
        ".jl",
        ".lua",
        ".vim",
        ".el",
        ".coffee",
        ".dart",
        ".ex",
        ".exs",
        ".clj",
        ".cljs",
        ".edn",
        ".erl",
        ".hrl",
        ".hs",
        ".lhs",
        ".ml",
        ".mli",
        ".f",
        ".f90",
        ".jl",
        ".m",
        ".mm",
        ".proto",
        ".thrift",
        ".graphql",
        ".gql",
        ".sql",
        ".log",
        ".conf",
        ".config",
        ".lock",
        ".template",
        ".jinja",
        ".j2",
        ".mustache",
        ".handlebars",
        ".hbs",
        ".twig",
        ".phtml",
        ".ctp",
        ".haml",
        ".slim",
        ".ejs",
        ".asp",
        ".aspx",
        ".cs",
        ".vb",
        ".fs",
        ".fsi",
        ".fsx",
        ".v",
        ".sv",
        ".svh",
        ".svelte",
        ".vue",
        ".astro",
        ".ipynb",
        ".csv",
        ".tsv",
    }

    return filepath.suffix.lower() in text_extensions


def is_binary_file(filepath, sample_size=8192):
    """Check if a file is binary by examining its content."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(min(sample_size, os.path.getsize(str(filepath))))
            if b"\x00" in chunk:
                return True
            # Check for high-byte characters that indicate binary
            text_chars = bytes(range(32, 127)) + b"\n\r\t\b\f"
            non_text_ratio = (
                sum(ch not in text_chars for ch in chunk) / len(chunk) if chunk else 0
            )
            return non_text_ratio > 0.30
    except (OSError, IOError):
        return True  # If we can't read it, assume it's binary


def should_skip_path(path):
    """Check if a path should be skipped."""
    skip_patterns = [
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
        "node_modules",
        ".venv",
        "venv",
        ".tox",
        ".eggs",
        ".coverage",
        "coverage.xml",
        "htmlcov",
        ".DS_Store",
        "*.pyc",
        "*.pyo",
        "*.so",
        "*.dll",
        "*.exe",
        "*.bin",
        "*.o",
        "*.obj",
        "*.class",
        "*.jar",
        "*.war",
        "*.zip",
        "*.tar",
        "*.gz",
        "*.rar",
        "*.7z",
        "*.dmg",
        "*.iso",
        "*.so",
        "*.dylib",
        "*.a",
        "*.lib",
        "*.pdf",
        "*.jpg",
        "*.jpeg",
        "*.png",
        "*.gif",
        "*.bmp",
        "*.svg",
        "*.ico",
        "*.webp",
        "*.mp3",
        "*.mp4",
        "*.avi",
        "*.mov",
        "*.wmv",
        "*.flv",
        "*.webm",
        "*.mkv",
        "*.m4a",
        "*.wav",
        "*.flac",
        "*.ogg",
        "*.ttf",
        "*.otf",
        "*.woff",
        "*.woff2",
        "*.eot",
        "*.npy",
        "*.npz",
        "logs",
        "dist",
        "build",
        "target",
        "*.log",
        "books",
        "review",
        ".xsarena",
        "tools",
        "scripts",
        "tests",
        "examples",
        "packaging",
        "pipelines",
        "snapshot_chunks",
        "*.egg-info",
        ".ipynb_checkpoints",
        "repo_flat.txt",
        "xsa_snapshot*.txt",
        "xsa_snapshot*.zip",
        "xsa_debug_report*.txt",
    ]

    path_str = str(path)
    for pattern in skip_patterns:
        if pattern.startswith("."):
            # Directory pattern
            if pattern.lstrip(".") in path.parts or pattern in path.parts:
                return True
        elif pattern.endswith("/"):
            # Directory pattern
            if pattern.rstrip("/") in path.parts:
                return True
        elif pattern.startswith("*."):
            # Glob pattern for files
            if path.match(pattern):
                return True
        elif pattern in path_str:
            return True

    return False


def simple_snapshot(output_file="snapshot.txt"):
    """Generate a simple snapshot by walking the repo tree and concatenating text files."""
    root = Path(".").resolve()
    output_path = Path(output_file)

    print(f"Generating snapshot to {output_path}...")

    with open(output_path, "w", encoding="utf-8", newline="") as out_file:
        # Write header
        out_file.write("# Repo Flat Pack\n\n")
        out_file.write("Instructions for assistant:\n")
        out_file.write(
            "- Treat '=== START FILE: path ===' boundaries as file delimiters.\n"
        )
        out_file.write("- Do not summarize early; ask for next files if needed.\n")
        out_file.write("- Keep references by path for follow-ups.\n\n")

        # Walk the directory tree
        file_count = 0
        total_size = 0

        for root_path, dirs, files in os.walk(".", topdown=True):
            # Filter out directories to skip
            dirs[:] = [d for d in dirs if not should_skip_path(Path(root_path) / d)]

            for file in files:
                filepath = Path(root_path) / file

                # Skip if path should be ignored
                if should_skip_path(filepath):
                    continue

                # Check if it's a text file by extension
                if not is_text_file(filepath):
                    continue

                # Check if it's actually a binary file
                if is_binary_file(filepath):
                    continue

                # Read the file content
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue  # Skip files that can't be read

                # Write the header
                out_file.write(
                    f"=== START FILE: {filepath.relative_to(Path('.').resolve())} ===\n"
                )

                # Write the content
                out_file.write(content)

                # Write the footer
                out_file.write(
                    f"\n=== END FILE: {filepath.relative_to(Path('.').resolve())} ===\n\n"
                )

                file_count += 1
                total_size += len(content.encode("utf-8"))

                if file_count % 100 == 0:
                    print(f"Processed {file_count} files...")

        print(f"Snapshot complete! {file_count} files, {total_size} bytes total.")
        print(f"Output written to {output_path}")


if __name__ == "__main__":
    output_file = sys.argv[1] if len(sys.argv) > 1 else "snapshot.txt"
    simple_snapshot(output_file)
