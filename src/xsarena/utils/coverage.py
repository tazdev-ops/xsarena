"""Coverage tracking utilities for XSArena."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class CoverageItem:
    """Represents a single item in the outline and its coverage status."""

    title: str
    level: int  # H1=1, H2=2, etc.
    content: str
    status: str  # "Covered", "Partial", "Missing"
    confidence: float  # 0.0 to 1.0


def parse_outline(outline_path: str) -> List[CoverageItem]:
    """Parse an outline file and return a list of CoverageItems."""
    outline_content = Path(outline_path).read_text(encoding="utf-8")

    items = []
    lines = outline_content.split("\n")

    for line in lines:
        # Match markdown headers: #, ##, ###, etc.
        header_match = re.match(r"^(\s*)(#{1,6})\s+(.+)$", line)
        if header_match:
            len(header_match.group(1))
            level = len(header_match.group(2))
            title = header_match.group(3).strip()

            items.append(
                CoverageItem(
                    title=title,
                    level=level,
                    content="",
                    status="Missing",
                    confidence=0.0,
                )
            )

    return items


def parse_book_content(book_path: str) -> str:
    """Parse the book content for coverage analysis."""
    return Path(book_path).read_text(encoding="utf-8")


def analyze_coverage(outline_path: str, book_path: str) -> List[CoverageItem]:
    """Analyze the coverage of a book against an outline."""
    outline_items = parse_outline(outline_path)
    book_content = parse_book_content(book_path)

    # Simple keyword matching approach
    for item in outline_items:
        # Create search patterns for the item title
        patterns = [
            item.title.lower(),
            item.title.lower().replace(" ", "-"),
            item.title.lower().replace(" ", "_"),
        ]

        found = False
        for pattern in patterns:
            if pattern in book_content.lower():
                found = True
                break

        if found:
            # Check if there's substantial content near the match
            title_pos = book_content.lower().find(patterns[0])
            if title_pos != -1:
                # Look at content around the title match
                context_start = max(0, title_pos - 200)
                context_end = min(len(book_content), title_pos + len(item.title) + 500)
                context = book_content[context_start:context_end]

                # Count words in context to determine if it's covered substantially
                word_count = len(context.split())
                if word_count > 50:  # Arbitrary threshold for "covered"
                    item.status = "Covered"
                    item.confidence = 0.9
                else:
                    item.status = "Partial"
                    item.confidence = 0.5
            else:
                item.status = "Covered"
                item.confidence = 0.7
        else:
            item.status = "Missing"
            item.confidence = 0.0

    return outline_items


def generate_coverage_report(
    coverage_items: List[CoverageItem], outline_path: str, book_path: str
) -> str:
    """Generate a markdown report of the coverage analysis."""
    report = f"""# Coverage Report

**Outline:** {outline_path}
**Book:** {book_path}

## Coverage Summary

"""

    # Count status
    covered = sum(1 for item in coverage_items if item.status == "Covered")
    partial = sum(1 for item in coverage_items if item.status == "Partial")
    missing = sum(1 for item in coverage_items if item.status == "Missing")
    total = len(coverage_items)

    report += f"- **Total items:** {total}\n"
    report += f"- **Covered:** {covered}\n"
    report += f"- **Partial:** {partial}\n"
    report += f"- **Missing:** {missing}\n\n"

    # Progress bar
    if total > 0:
        progress = covered / total
        filled = int(progress * 20)
        empty = 20 - filled
        progress_bar = "█" * filled + "░" * empty
        report += f"Progress: [{progress_bar}] {progress:.1%}\n\n"

    # Detailed table
    report += "## Detailed Coverage\n\n"
    report += "| Section | Status | Confidence |\n"
    report += "|--------|--------|------------|\n"

    for item in coverage_items:
        indent = "  " * (item.level - 1)
        report += f"| {indent}{item.title} | {item.status} | {item.confidence:.1%} |\n"

    # Suggested NEXT hints
    report += "\n## Suggested NEXT Hints\n\n"
    missing_items = [item for item in coverage_items if item.status == "Missing"]
    if missing_items:
        report += "Focus on these missing sections:\n\n"
        for item in missing_items[:5]:  # Limit to first 5 missing items
            report += f"- {item.title}\n"
    else:
        report += "All outline sections are covered! Consider:\n"
        report += "- Expanding existing sections\n"
        report += "- Adding deeper detail to covered sections\n"
        report += "- Reviewing for completeness\n"

    return report


def save_coverage_report(report: str, output_path: str):
    """Save the coverage report to a file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report, encoding="utf-8")
