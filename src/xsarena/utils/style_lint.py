"""Utilities for linting directive files."""

import re
from pathlib import Path
from typing import Dict, List


def lint_directive_file(file_path: Path) -> List[Dict[str, str]]:
    issues = []
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        if file_path.parent.name == "style" and not re.search(
            r"^OVERLAY:", content, re.MULTILINE
        ):
            issues.append(
                {
                    "line": "1",
                    "code": "STYLE-001",
                    "message": "Style overlay file is missing an 'OVERLAY:' header.",
                }
            )

        for i, line in enumerate(lines, 1):
            if "[FIELD]" in line or "[TOPIC]" in line:
                issues.append(
                    {
                        "line": str(i),
                        "code": "PROMPT-001",
                        "message": "Uses outdated placeholder like [FIELD]. Use {SUBJECT} instead.",
                    }
                )

        if ".json.md" in file_path.name and "json" not in content.lower():
            issues.append(
                {
                    "line": "1",
                    "code": "JSON-001",
                    "message": "Structured JSON prompt does not explicitly mention 'JSON' in its instructions.",
                }
            )

    except Exception as e:
        issues.append(
            {
                "line": "0",
                "code": "LINT-ERR",
                "message": f"Error reading or parsing file: {e}",
            }
        )

    return issues
