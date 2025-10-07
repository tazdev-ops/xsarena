#!/usr/bin/env python3
# This is a utility that creates a snapshot of the current codebase,
# including project structure, file contents, and relevant metadata.
# It's useful for debugging, sharing code states, and creating documentation.
import hashlib
import os
import pathlib
import re
import subprocess
import sys
import tarfile
from datetime import datetime


def create_snapshot(
    project_root=".",
    output_file="snapshot.txt",
    max_file_size=10000,
    include_tree=True,
    include_files=True,
    include_git=True,
    include_pip=True,
    chunk=False,
    chunk_size=100000,
    redact=True,
    tar=False,
    include_env=True,
):
    """
    Create a snapshot of the current project with enhanced features.
    """
    project_path = pathlib.Path(project_root)
    snapshot_parts = []

    # Add timestamp and environment info
    snapshot_parts.append(f"Snapshot created: {datetime.now()}")
    snapshot_parts.append(f"System: {sys.platform}")
    snapshot_parts.append(f"Python: {sys.version}")
    snapshot_parts.append(f"Working directory: {os.getcwd()}")

    # Environment information
    if include_env:
        snapshot_parts.append("\nENVIRONMENT:")
        snapshot_parts.append("-" * 15)
        snapshot_parts.append(f"OPENROUTER_API_KEY set: {'yes' if os.environ.get('OPENROUTER_API_KEY') else 'no'}")
        snapshot_parts.append(f"XSA_USE_PTK: {os.environ.get('XSA_USE_PTK', 'not set')}")
        # Show first 3 PATH directories
        path_parts = os.environ.get("PATH", "").split(os.pathsep)[:3]
        snapshot_parts.append(f"PATH prefixes: {path_parts}")
        snapshot_parts.append("")

    snapshot_parts.append("=" * 50)
    snapshot_parts.append("")

    # Add project structure tree
    if include_tree:
        snapshot_parts.append("PROJECT STRUCTURE:")
        snapshot_parts.append("-" * 20)
        tree_output = generate_tree(project_path)
        snapshot_parts.append(tree_output)
        snapshot_parts.append("")

    # Add project files content
    if include_files:
        snapshot_parts.append("PROJECT FILES:")
        snapshot_parts.append("-" * 15)
        files_output = collect_project_files(project_path, max_file_size)
        snapshot_parts.append(files_output)
        snapshot_parts.append("")

    # Add git status if available
    if include_git:
        snapshot_parts.append("GIT STATUS:")
        snapshot_parts.append("-" * 12)
        git_output = get_git_info(project_path)
        snapshot_parts.append(git_output)
        snapshot_parts.append("")

    # Add pip freeze if available
    if include_pip:
        snapshot_parts.append("PIP FREEZE (top 200 lines):")
        snapshot_parts.append("-" * 30)
        pip_output = get_pip_freeze()
        snapshot_parts.append(pip_output)
        snapshot_parts.append("")

    # Add file heads for key files
    snapshot_parts.append("KEY FILE HEADS (first 50 lines each):")
    snapshot_parts.append("-" * 40)
    key_files = [
        "pyproject.toml",
        "src/xsarena/core/engine.py",
        "xsarena_cli.py",
        "src/xsarena/cli/main.py",
        "README.md",
        "requirements.txt",
    ]
    for key_file in key_files:
        file_path = project_path / key_file
        if file_path.exists():
            snapshot_parts.append(f"\nFILE HEAD: {key_file}")
            snapshot_parts.append("-" * len(f"FILE HEAD: {key_file}"))
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    # Take first 50 lines
                    head_lines = lines[:50]
                    snapshot_parts.append("".join(head_lines))
                    if len(lines) > 50:
                        snapshot_parts.append("\n... [truncated]\n")
            except Exception as e:
                snapshot_parts.append(f"Error reading {key_file}: {str(e)}\n")
    snapshot_parts.append("")

    # Combine everything
    full_snapshot = "\n".join(snapshot_parts)

    # Apply redaction if requested
    if redact:
        full_snapshot = redact_sensitive_info(full_snapshot)

    # Handle chunking or regular output
    if chunk:
        chunk_snapshot(full_snapshot, chunk_size)
    else:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_snapshot)
        print(f"Snapshot saved to {output_file}")

        # Create SHA256 hash
        sha256_hash = hashlib.sha256(full_snapshot.encode("utf-8")).hexdigest()
        with open(f"{output_file}.sha256", "w", encoding="utf-8") as f:
            f.write(sha256_hash)
        print(f"SHA256 hash saved to {output_file}.sha256")

        # Create tarball if requested
        if tar:
            tar_path = f"{output_file}.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(output_file, arcname=os.path.basename(output_file))
                tar.add(f"{output_file}.sha256", arcname=f"{os.path.basename(output_file)}.sha256")
            print(f"Tarball saved to {tar_path}")

    return full_snapshot


def redact_sensitive_info(content):
    """Redact sensitive information from content."""
    # Load patterns from .xsarena/redact.yml if it exists
    redact_patterns = [
        r'(?i)(api[_-]?key|secret|token)\s*[:=]\s*[^\s"\'\n]+',
        r'(?i)(password|pwd)\s*[:=]\s*[^\s"\'\n]+',
        # Add more patterns as needed
    ]

    # Add patterns from config file if it exists
    config_path = pathlib.Path(".xsarena") / "redact.yml"
    if config_path.exists():
        try:
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config and "patterns" in config:
                    redact_patterns.extend(config["patterns"])
        except Exception:
            pass  # If config file is invalid, continue with default patterns

    # Apply redaction patterns
    redacted_content = content
    for pattern in redact_patterns:
        try:
            redacted_content = re.sub(pattern, r"\1: <REDACTED>", redacted_content)
        except re.error:
            # Skip invalid regex patterns
            continue

    return redacted_content


def generate_tree(project_path):
    """Generate a tree-like structure of the project."""
    tree_lines = []
    for root, dirs, files in os.walk(project_path):
        # Skip hidden directories and build directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ["__pycache__", "build", "dist", ".git", ".pytest_cache", ".ruff_cache"]
        ]

        level = root.replace(str(project_path), "").count(os.sep)
        indent = " " * 2 * level
        tree_lines.append(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 2 * (level + 1)
        for file in files:
            if not file.startswith("."):
                tree_lines.append(f"{subindent}{file}")
    return "\n".join(tree_lines)


def collect_project_files(project_path, max_size):
    """Collect relevant project files."""
    files_content = []

    # Define relevant file patterns
    relevant_patterns = [
        "*.py",
        "*.md",
        "*.txt",
        "*.yaml",
        "*.yml",
        "*.json",
        "*.toml",
        "Dockerfile",
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
        "README*",
        "LICENSE*",
    ]

    for pattern in relevant_patterns:
        for file_path in project_path.rglob(pattern):
            if any(part.startswith(".") for part in file_path.parts):
                continue  # Skip hidden directories
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    if size <= max_size:
                        relative_path = file_path.relative_to(project_path)
                        files_content.append(f"\nFILE: {relative_path}")
                        files_content.append("-" * len(f"FILE: {relative_path}"))
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            files_content.append(content)
                        files_content.append("\n" + "=" * 50 + "\n")
                except Exception:
                    continue

    return "\n".join(files_content)


def get_git_info(project_path):
    """Get git status and info."""
    git_info = []

    # Get current branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            git_info.append(f"Branch: {branch}")
    except Exception:
        git_info.append("Branch: Unable to determine")

    # Get short commit hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=project_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            commit_hash = result.stdout.strip()
            git_info.append(f"Commit: {commit_hash}")
    except Exception:
        git_info.append("Commit: Unable to determine")

    # Get last commit subject
    try:
        result = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=project_path, capture_output=True, text=True)
        if result.returncode == 0:
            commit_subject = result.stdout.strip()
            git_info.append(f"Last commit: {commit_subject}")
    except Exception:
        git_info.append("Last commit: Unable to determine")

    # Get git status
    try:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=project_path, capture_output=True, text=True)
        if result.returncode == 0:
            status_output = result.stdout or "No changes"
            git_info.append(f"Status:\n{status_output}")
        else:
            git_info.append("Status: Error getting git status")
    except Exception:
        git_info.append("Status: Git not available or error")

    return "\n".join(git_info)


def get_pip_freeze():
    """Get pip freeze output (top 200 lines)."""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
        if result.returncode == 0:
            # Limit to first 200 lines to avoid huge output
            lines = result.stdout.split("\n")[:200]
            return "\n".join(lines)
        return "Error running pip freeze"
    except Exception:
        return "Pip freeze not available"


def chunk_snapshot(snapshot_content, chunk_size):
    """Split snapshot into chunks."""
    chunks = []
    for i in range(0, len(snapshot_content), chunk_size):
        chunk = snapshot_content[i : i + chunk_size]
        chunks.append(chunk)

    # Save chunks to separate files
    for i, chunk in enumerate(chunks):
        chunk_file = f"snapshot_chunk_{i:03d}.txt"
        with open(chunk_file, "w", encoding="utf-8") as f:
            f.write(chunk)
        print(f"Saved {chunk_file}")


def diff_snapshots(path_a, path_b):
    """Create a diff between two snapshot files."""
    import difflib

    try:
        with open(path_a, "r", encoding="utf-8") as f:
            content_a = f.readlines()
        with open(path_b, "r", encoding="utf-8") as f:
            content_b = f.readlines()

        diff = difflib.unified_diff(content_a, content_b, fromfile="snapshot_a", tofile="snapshot_b", lineterm="")

        diff_content = "\n".join(diff)

        # Write diff to file
        diff_file = f"snapshot_diff_{os.path.basename(path_a)}_vs_{os.path.basename(path_b)}.txt"
        with open(diff_file, "w", encoding="utf-8") as f:
            f.write(diff_content)

        print(f"Diff saved to {diff_file}")
        return diff_content
    except Exception as e:
        print(f"Error creating diff: {e}")
        return str(e)


if __name__ == "__main__":
    # Get command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Create a project snapshot")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output", default="snapshot.txt", help="Output file name")
    parser.add_argument("--max-file-size", type=int, default=10000, help="Max file size to include (bytes)")
    parser.add_argument("--no-tree", action="store_true", help="Exclude project tree")
    parser.add_argument("--no-files", action="store_true", help="Exclude file contents")
    parser.add_argument("--no-git", action="store_true", help="Exclude git info")
    parser.add_argument("--no-pip", action="store_true", help="Exclude pip freeze")
    parser.add_argument("--no-env", action="store_true", help="Exclude environment info")
    parser.add_argument("--chunk", action="store_true", help="Split output into chunks")
    parser.add_argument("--chunk-size", type=int, default=100000, help="Chunk size in bytes")
    parser.add_argument("--no-redact", action="store_true", help="Don't redact sensitive info")
    parser.add_argument("--tar", action="store_true", help="Create tarball with sha256")

    # Diff subcommand
    parser.add_argument(
        "--diff", nargs=2, metavar=("SNAPSHOT_A", "SNAPSHOT_B"), help="Create diff between two snapshot files"
    )

    args = parser.parse_args()

    if args.diff:
        # Run diff command
        diff_snapshots(args.diff[0], args.diff[1])
    else:
        # Run regular snapshot command
        create_snapshot(
            project_root=args.project_root,
            output_file=args.output,
            max_file_size=args.max_file_size,
            include_tree=not args.no_tree,
            include_files=not args.no_files,
            include_git=not args.no_git,
            include_pip=not args.no_pip,
            include_env=not args.no_env,
            chunk=args.chunk,
            chunk_size=args.chunk_size,
            redact=not args.no_redact,
            tar=args.tar,
        )
