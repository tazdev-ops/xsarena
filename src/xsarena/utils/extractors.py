"""Extractor utilities for XSArena."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class ChecklistItem:
    """Represents a single checklist item."""

    section: str
    item: str
    original_line: str
    line_number: int


def extract_checklists(content: str) -> List[ChecklistItem]:
    """Extract checklist items from markdown content."""
    lines = content.split("\n")
    checklists = []
    current_section = "Introduction"

    for line_num, line in enumerate(lines, 1):
        # Check if this is a heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if heading_match:
            current_section = heading_match.group(2).strip()
        else:
            # Check for checklist patterns
            # Patterns: bullets starting with imperative verbs or "Checklist:" blocks
            checklist_patterns = [
                r"^\s*[\*\-\+]\s+(?P<item>(?:Add|Apply|Assign|Attach|Avoid|Begin|Build|Calculate|Choose|Clean|Collect|Combine|Compare|Complete|Consider|Create|Define|Delete|Describe|Determine|Develop|Document|Draw|Edit|Enable|Execute|Expand|Explain|Extract|Find|Follow|Generate|Identify|Implement|Include|Install|Integrate|Limit|Load|Maintain|Manage|Mark|Measure|Modify|Move|Note|Observe|Open|Optimize|Organize|Perform|Prepare|Process|Provide|Record|Reduce|Refine|Register|Remove|Replace|Report|Request|Reset|Restore|Review|Run|Save|Schedule|Select|Send|Set|Share|Show|Sort|Start|Stop|Store|Submit|Take|Test|Track|Update|Upload|Use|Validate|View|Watch|Write|Check|Verify|Confirm|Ensure|Establish|Configure|Troubleshoot|Debug)\s+.+)",
                r"^\s*\d+\.\s+(?P<item>(?:Add|Apply|Assign|Attach|Avoid|Begin|Build|Calculate|Choose|Clean|Collect|Combine|Compare|Complete|Consider|Create|Define|Delete|Describe|Determine|Develop|Document|Draw|Edit|Enable|Execute|Expand|Explain|Extract|Find|Follow|Generate|Identify|Implement|Include|Install|Integrate|Limit|Load|Maintain|Manage|Mark|Measure|Modify|Move|Note|Observe|Open|Optimize|Organize|Perform|Prepare|Process|Provide|Record|Reduce|Refine|Register|Remove|Replace|Report|Request|Reset|Restore|Review|Run|Save|Schedule|Select|Send|Set|Share|Show|Sort|Start|Stop|Store|Submit|Take|Test|Track|Update|Upload|Use|Validate|View|Watch|Write|Check|Verify|Confirm|Ensure|Establish|Configure|Troubleshoot|Debug)\s+.+)",
                r"^\s*[\*\-\+]\s+(?P<item>.+\s+(checklist|list|steps?):?\s*.+)",  # Lines with checklist keywords
            ]

            for pattern in checklist_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    item = match.group("item").strip()
                    # Clean up the item text
                    item = re.sub(
                        r"^[Aa]dd\s+", "", item
                    )  # Remove "Add " prefix if present
                    item = re.sub(
                        r"^[Ii]nclude\s+", "", item
                    )  # Remove "Include " prefix if present
                    item = re.sub(
                        r"^[Ff]ollow\s+", "", item
                    )  # Remove "Follow " prefix if present

                    checklists.append(
                        ChecklistItem(
                            section=current_section,
                            item=item,
                            original_line=line.strip(),
                            line_number=line_num,
                        )
                    )
                    break  # Only add once even if multiple patterns match

    return checklists


def normalize_checklist_items(items: List[ChecklistItem]) -> List[ChecklistItem]:
    """Normalize checklist items by removing duplicates and standardizing format."""
    normalized = []
    seen_items = set()

    for item in items:
        # Create a normalized version for comparison
        normalized_text = re.sub(r"\s+", " ", item.item.lower().strip())

        # Remove common prefixes/suffixes for better deduplication
        normalized_text = re.sub(
            r"^\s*(step|item|point)\s+\d+\s*:?\s*", "", normalized_text
        )
        normalized_text = re.sub(
            r"\s*\([^)]*\)\s*$", "", normalized_text
        )  # Remove parentheses

        if normalized_text and normalized_text not in seen_items:
            seen_items.add(normalized_text)
            # Use the original item but with cleaned content
            normalized.append(item)

    return normalized


def group_checklist_items_by_section(
    items: List[ChecklistItem],
) -> Dict[str, List[ChecklistItem]]:
    """Group checklist items by section."""
    grouped = {}
    for item in items:
        if item.section not in grouped:
            grouped[item.section] = []
        grouped[item.section].append(item)

    return grouped


def generate_checklist_report(items: List[ChecklistItem], book_path: str) -> str:
    """Generate a markdown report of extracted checklists."""
    report = f"""# Extracted Checklists

**Source Book:** {book_path}

"""

    # Group items by section
    grouped = group_checklist_items_by_section(items)

    for section, section_items in grouped.items():
        report += f"## {section}\n\n"
        for item in section_items:
            report += f"- {item.item}\n"
        report += "\n"

    return report


def save_checklist_report(report: str, output_path: str):
    """Save the checklist report to a file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report, encoding="utf-8")


def extract_checklists_from_file(book_path: str) -> List[ChecklistItem]:
    """Extract checklists from a book file."""
    content = Path(book_path).read_text(encoding="utf-8")
    raw_items = extract_checklists(content)
    normalized_items = normalize_checklist_items(raw_items)
    return normalized_items
