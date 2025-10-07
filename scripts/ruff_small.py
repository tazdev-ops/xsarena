#!/usr/bin/env python3
"""
Pure-Python ruff_small alternative to replace ruff_small.sh without bash/jq dependencies.
This allows XSArena to work on Windows and other platforms without shell requirements.
"""

import argparse
import os
import subprocess
import sys


def run_ruff_small(file_path: str, rules: str = "E,F,I", format_type: str = "concise"):
    """
    Run ruff on a specific file with specified rules and format.

    Args:
        file_path: Path to the file to check
        rules: Comma-separated list of ruff rules (default "E,F,I")
        format_type: Output format (default "concise")
    """
    try:
        # Build the ruff command
        cmd = ["ruff", "check"]

        if rules:
            cmd.extend(["--select", rules.replace(" ", "")])  # Ensure no spaces in rules

        if format_type:
            cmd.extend(["--output-format", format_type])

        cmd.extend([file_path, "--exit-zero"])  # Always exit 0 so the agent can read output without halting

        # Run the command
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Print stdout (the ruff output)
        print(result.stdout, end="")

        # If there are errors, also print stderr
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        # Return 0 always, as requested
        return 0

    except FileNotFoundError:
        print("Error: ruff is not installed or not in PATH", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running ruff: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run ruff small check on a file")
    parser.add_argument("--file", required=True, help="File to check")
    parser.add_argument("--rules", default="E,F,I", help="Rules to check (default: E,F,I)")
    parser.add_argument("--format", default="concise", help="Output format (default: concise)")

    args = parser.parse_args()

    # Check if file exists
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} does not exist", file=sys.stderr)
        sys.exit(1)

    # Run ruff_small
    exit_code = run_ruff_small(args.file, args.rules, args.format)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
