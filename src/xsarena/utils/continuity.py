"""Continuity analysis utilities for XSArena."""

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class ContinuityIssue:
    """Represents a continuity issue in the text."""

    type: str  # "drift", "reintro", "repetition"
    position: int
    description: str
    severity: str  # "low", "medium", "high"
    suggestion: str


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using difflib."""
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def analyze_continuity(book_path: str) -> List[ContinuityIssue]:
    """Analyze the book for continuity issues."""
    book_content = Path(book_path).read_text(encoding="utf-8")

    issues = []

    # Split the book into chunks by sections (H1/H2)
    sections = []
    lines = book_content.split("\n")

    current_section = []
    current_title = "Introduction"

    for line in lines:
        # Check if this is a heading
        heading_match = re.match(r"^(#{1,2})\s+(.+)$", line.strip())
        if heading_match:
            # Save previous section
            if current_section:
                sections.append(
                    {"title": current_title, "content": "\n".join(current_section)}
                )

            # Start new section
            current_title = heading_match.group(2)
            current_section = [line]
        else:
            current_section.append(line)

    # Add the last section
    if current_section:
        sections.append({"title": current_title, "content": "\n".join(current_section)})

    # Analyze transitions between sections for anchor drift
    for i in range(1, len(sections)):
        prev_section = sections[i - 1]
        curr_section = sections[i]

        # Get the end of the previous section and the start of the current
        prev_end = prev_section["content"][-200:]  # Last 200 chars
        curr_start = curr_section["content"][:200]  # First 200 chars

        # Calculate similarity
        similarity = calculate_similarity(prev_end, curr_start)

        # If similarity is low, it might indicate anchor drift
        if similarity < 0.1:  # Arbitrary threshold
            issues.append(
                ContinuityIssue(
                    type="drift",
                    position=i,
                    description=f"Low continuity between '{prev_section['title']}' and '{curr_section['title']}'",
                    severity="high",
                    suggestion="Consider increasing anchor_length to 360-420 and improving transitions",
                )
            )
        elif similarity < 0.3:
            issues.append(
                ContinuityIssue(
                    type="drift",
                    position=i,
                    description=f"Moderate continuity issue between '{prev_section['title']}' and '{curr_section['title']}'",
                    severity="medium",
                    suggestion="Consider increasing anchor_length to 300-360",
                )
            )

    # Look for re-introduction phrases at section beginnings
    reintro_patterns = [
        r"^(what|who|where|when|why|how)\s+is\s+\w+",
        r"^in\s+this\s+(section|chapter|part)",
        r"^to\s+begin",
        r"^first",
        r"^initially",
        r"^let\'?s\s+(begin|start|explore)",
    ]

    for i, section in enumerate(sections):
        # Get the first few lines of the section
        first_lines = section["content"][:200].lower()
        first_lines.split(".")

        for pattern in reintro_patterns:
            if re.search(pattern, first_lines):
                issues.append(
                    ContinuityIssue(
                        type="reintro",
                        position=i,
                        description=f"Potential re-introduction phrase in '{section['title']}'",
                        severity="medium",
                        suggestion="Consider reducing re-introduction phrases to avoid chapter restarts",
                    )
                )

    # Look for repetition within the text
    content = book_content.lower()
    sentences = re.split(r"[.!?]+", content)

    # Check for repeated sentences
    sentence_counts = {}
    for sent in sentences:
        sent = sent.strip()
        if len(sent) > 20:  # Only consider sentences with meaningful content
            if sent in sentence_counts:
                sentence_counts[sent] += 1
            else:
                sentence_counts[sent] = 1

    for sent, count in sentence_counts.items():
        if count > 2:  # Repeated more than twice
            issues.append(
                ContinuityIssue(
                    type="repetition",
                    position=content.find(sent),
                    description=f"Repeated sentence: '{sent[:50]}...'",
                    severity="high",
                    suggestion="Consider lowering repetition_threshold to ~0.32 to catch more repetitions",
                )
            )

    return issues


def generate_continuity_report(issues: List[ContinuityIssue], book_path: str) -> str:
    """Generate a markdown report of continuity issues."""
    report = f"""# Continuity Report

**Book:** {book_path}

## Summary

"""

    # Count issue types
    issue_counts = {}
    for issue in issues:
        issue_counts[issue.type] = issue_counts.get(issue.type, 0) + 1

    for issue_type, count in issue_counts.items():
        report += f"- **{issue_type.title()} issues:** {count}\n"

    if not issues:
        report += "\nNo continuity issues detected!\n"
        return report

    report += f"\n## Issues Found ({len(issues)})\n\n"

    # Group issues by severity
    severity_order = {"high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.severity, 99))

    for issue in sorted_issues:
        report += f"### {issue.type.title()} Issue\n"
        report += f"- **Severity:** {issue.severity.title()}\n"
        report += f"- **Description:** {issue.description}\n"
        report += f"- **Suggestion:** {issue.suggestion}\n\n"

    # Provide control suggestions
    report += "## Control Recommendations\n\n"
    drift_issues = [i for i in issues if i.type == "drift"]
    reintro_issues = [i for i in issues if i.type == "reintro"]
    repetition_issues = [i for i in issues if i.type == "repetition"]

    if drift_issues:
        report += (
            "- **For anchor drift:** Consider increasing `anchor_length` to 360-420\n"
        )

    if reintro_issues:
        report += "- **For re-introductions:** Review section openings to reduce restart patterns\n"

    if repetition_issues:
        report += (
            "- **For repetitions:** Consider lowering `repetition_threshold` to ~0.32\n"
        )

    return report


def save_continuity_report(report: str, output_path: str):
    """Save the continuity report to a file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report, encoding="utf-8")
