"""Utilities for linting directive files."""

import re
from pathlib import Path
from typing import Dict, List, Optional


class LintIssue:
    """Represents a single linting issue."""

    def __init__(
        self,
        line: str = "1",
        code: str = "",
        message: str = "",
        type: Optional[str] = None,
        section: Optional[str] = None,
        severity: Optional[str] = None,
        suggestion: Optional[str] = None,
    ):
        self.line = line
        self.code = code
        self.message = message
        # Use the provided type if available, otherwise derive from code
        self.type = (
            type
            if type is not None
            else (code.split("-")[0].lower() if code else "general")
        )
        self.section = section
        self.severity = severity
        self.suggestion = suggestion


def analyze_style(content: str, file_path: Optional[Path] = None) -> List[LintIssue]:
    """Analyze content for style issues."""
    issues = []

    # Check for term definitions
    import re

    bold_terms = re.findall(r"\*\*([^\*]+)\*\*", content)
    for term in set(bold_terms):
        # For now, we'll just flag all bold terms as potentially undefined
        # A real implementation would check for definitions
        issues.append(
            LintIssue(
                line="1",
                code="TERM-DEFINITION",
                message=f"Term '{term}' may be undefined",
                type="term_definition",
                section="General",
                severity="medium",
                suggestion=f"Define '{term}' when first introduced",
            )
        )

    # Check for bullet walls (too many consecutive bullet points)
    lines = content.splitlines()
    consecutive_bullets = 0
    current_section = "General"

    for i, line in enumerate(lines):
        if line.strip().startswith(("-", "*", "+")):
            consecutive_bullets += 1
            # Identify the current section based on the most recent heading
            for j in range(i, -1, -1):
                if j < len(lines) and lines[j].strip().startswith("#"):
                    current_section = lines[j].strip("# ")
                    break
        else:
            # If we had a long sequence of bullets, record an issue
            if consecutive_bullets >= 10:
                issues.append(
                    LintIssue(
                        line=str(i - consecutive_bullets + 1),
                        code="STYLE-BULLET-WALL",
                        message=f"Section '{current_section}' has {consecutive_bullets} consecutive bullet points - potential bullet wall",
                        type="bullet_wall",
                        section=current_section,
                        severity="high",
                        suggestion="Consider converting some bullets to prose paragraphs",
                    )
                )
            consecutive_bullets = 0  # Reset counter

    # Check for paragraph length (too short paragraphs)
    paragraphs = content.split("\n\n")
    for i, para in enumerate(paragraphs):
        para_words = len(para.split())
        if 0 < para_words < 10:  # Very short paragraphs
            issues.append(
                LintIssue(
                    line=str(i + 1),
                    code="STYLE-PARAGRAPH-LENGTH",
                    message=f"Paragraph length is {para_words} words - too short",
                    type="paragraph_len",  # Note: test expects "paragraph_len", not "paragraph_length"
                    section=f"Paragraph {i + 1}",
                    severity="medium",
                    suggestion="Increase to ~5-15 words per paragraph for better readability",
                )
            )

    # Also check for very short individual lines that might be separate paragraphs
    lines = content.splitlines()
    for i, line in enumerate(lines):
        line_words = len(line.split())
        if 0 < line_words < 5:  # Very short lines
            # Check if it's not a heading or list item
            if not line.strip().startswith(("#", "-", "*", "+")):
                issues.append(
                    LintIssue(
                        line=str(i + 1),
                        code="STYLE-PARAGRAPH-LENGTH",
                        message=f"Line length is {line_words} words - too short",
                        type="paragraph_len",
                        section="General",
                        severity="medium",
                        suggestion="Increase to ~5-15 words per paragraph for better readability",
                    )
                )

    # Check for heading density
    all_lines = content.splitlines()
    headings = [line for line in all_lines if line.strip().startswith("#")]
    if (
        len(all_lines) > 0 and len(headings) / len(all_lines) > 0.1
    ):  # More than 10% are headings
        issues.append(
            LintIssue(
                line="1",
                code="STYLE-HEADING-DENSITY",
                message=f"Document has high heading density: {len(headings)}/{len(all_lines)} lines are headings",
                type="heading_density",
                section="General",
                severity="medium",
                suggestion="Consider reducing the number of headings or adding more content between headings",
            )
        )

    return issues


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


def generate_style_report(
    issues: List[LintIssue], file_path: str, narrative: str = None
) -> str:
    """Generate a formatted style report."""
    if not issues:
        report = f"Style Lint Report\n\nFile: {file_path}"
        if narrative:
            report += f"\nNarrative: {narrative}"
        report += "\n\nNo style issues detected."
        return report

    report = f"Style Lint Report\n\nFile: {file_path}"
    if narrative:
        report += f"\nNarrative: {narrative}"
    report += "\n\nSummary:\n\n"

    # Count issue types
    issue_counts = {}
    for issue in issues:
        issue_type = issue.type or "general"  # Use "general" if type is None
        issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

    for issue_type, count in issue_counts.items():
        report += f"- {issue_type.replace('_', ' ').title()} issues: {count}\n"

    report += "\nIssues:\n\n"
    for issue in issues:
        report += f"- Line {issue.line} ({issue.code}): {issue.message}\n"

    return report


def save_style_report(report: str, output_path: str) -> None:
    """Save the style report to a file."""
    Path(output_path).write_text(report, encoding="utf-8")
