"""Secrets scanning utilities for XSArena."""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


class SecretsScanner:
    """Scans for potential secrets and sensitive information in files."""

    def __init__(self):
        # Regex patterns for common secrets
        self.patterns = {
            "api_key": re.compile(
                r"(?i)(api[_-]?key|api[_-]?token|secret[_-]?key)\s*[=:]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]"
            ),
            "aws_access_key": re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
            "aws_secret_key": re.compile(
                r"(?i)aws[_-]?(secret[_-]?)?access[_-]?key\s*[=:]\s*['\"][a-zA-Z0-9/+]{20,}['\"]"
            ),
            "private_key": re.compile(
                r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
            ),
            "password": re.compile(
                r"(?i)(password|pwd|pass)\s*[=:]\s*['\"][^'\"]{6,}['\"]"
            ),
            "ip_address": re.compile(
                r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
            ),
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "phone": re.compile(
                r"\b(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
            ),
        }

    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Scan a single file for secrets."""
        findings = []

        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            # If we can't read the file, skip it
            return findings

        # Check each pattern
        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(content)
            for match in matches:
                findings.append(
                    {
                        "file": str(file_path),
                        "type": pattern_name,
                        "match": match if isinstance(match, str) else str(match),
                        "line_number": self._find_line_number(
                            content, match if isinstance(match, str) else str(match)
                        ),
                    }
                )

        return findings

    def _find_line_number(self, content: str, match: str) -> int:
        """Find the line number of a match in content."""
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if match in line:
                return i
        return 0

    def scan_directory(
        self, directory: Path, exclude_patterns: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Scan a directory for secrets."""
        if exclude_patterns is None:
            exclude_patterns = [
                ".git",
                "node_modules",
                "__pycache__",
                ".venv",
                "venv",
                ".xsarena",
            ]

        findings = []

        # Walk through all files in directory
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                # Skip excluded patterns
                should_skip = False
                for exclude in exclude_patterns:
                    if exclude in str(file_path):
                        should_skip = True
                        break
                if should_skip:
                    continue

                # Only scan text files
                if self._is_text_file(file_path):
                    findings.extend(self.scan_file(file_path))

        return findings

    def _is_text_file(self, file_path: Path) -> bool:
        """Check if a file is likely a text file."""
        text_extensions = {
            ".txt",
            ".py",
            ".js",
            ".ts",
            ".json",
            ".yaml",
            ".yml",
            ".md",
            ".html",
            ".css",
            ".xml",
            ".csv",
            ".env",
            ".sh",
            ".bash",
            ".zsh",
            ".ini",
            ".cfg",
            ".conf",
            ".sql",
            ".log",
            ".toml",
        }
        return file_path.suffix.lower() in text_extensions


def scan_secrets(
    directory: str = ".", fail_on_hits: bool = True
) -> Tuple[List[Dict[str, Any]], bool]:
    """Scan for secrets in the working tree."""
    scanner = SecretsScanner()
    findings = scanner.scan_directory(Path(directory))

    if findings:
        print(f"⚠️  Found {len(findings)} potential secrets:")
        for finding in findings:
            print(
                f"  - {finding['type']}: {finding['match']} in {finding['file']} (line {finding['line_number']})"
            )

        if fail_on_hits:
            return findings, True  # Return True to indicate failure
        else:
            return findings, False
    else:
        print("✅ No secrets found.")
        return [], False
