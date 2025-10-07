"""Quality lint for chunks (catch broken pedagogy)"""

import re
from typing import Dict, List


def check_teach_before_use(text: str) -> Dict[str, any]:
    """
    Check if terms are defined before use.
    Naive: look for bold terms followed by parenthetical definitions at first occurrence.
    """
    findings = []

    # Find all bold terms (markdown format: **term** or __term__)
    bold_terms = re.findall(r"\*\*([^\*]+)\*\*|__([^_]+)__", text)
    terms = [term[0] if term[0] else term[1] for term in bold_terms if term[0] or term[1]]

    # Track which terms have been defined
    defined_terms = set()
    undefined_usages = []

    for term in terms:
        # Check if this is the first occurrence and if it has a definition following
        first_occurrence_pos = min(
            text.lower().find(term.lower()),
            text.lower().find(f"**{term.lower()}**"),
            text.lower().find(f"__{term.lower()}__"),
        )
        if first_occurrence_pos != -1:
            # Look for definition pattern (e.g., term (definition))
            snippet = text[first_occurrence_pos : first_occurrence_pos + min(200, len(text) - first_occurrence_pos)]
            definition_pattern = re.search(rf"{re.escape(term)}[^.]*?\(([^)]+)\)", snippet, re.IGNORECASE)

            if definition_pattern:
                defined_terms.add(term)
            else:
                # Check if term is followed by a colon or dash that might introduce a definition
                colon_pattern = re.search(rf"{re.escape(term)}\s*[:\-]\s+([^,.]+)", snippet, re.IGNORECASE)
                if not colon_pattern:
                    undefined_usages.append(term)

    score = max(0.0, 1.0 - (len(undefined_usages) / len(terms)) if terms else 1.0)

    return {
        "score": score,
        "findings": findings,
        "undefined_terms": list(set(undefined_usages)),
        "total_terms": len(terms),
        "hint": "Define terms in parentheses at first use: **term** (definition) or use colons like: **term**: definition.",
    }


def check_next_marker(text: str) -> Dict[str, any]:
    """
    Check if NEXT marker is present in the text.
    """
    has_next = bool(re.search(r"^\s*NEXT:\s*", text, re.MULTILINE))

    return {
        "has_next": has_next,
        "hint": "Ensure NEXT: marker is present to guide continuation" if not has_next else "",
    }


def lint_chunk(text: str, subject: str = "") -> Dict[str, any]:
    """
    Run both lint checks on a text chunk.
    """
    teach_results = check_teach_before_use(text)
    next_results = check_next_marker(text)

    issues = []
    if teach_results["undefined_terms"]:
        issues.append(f"Undefined terms found: {', '.join(teach_results['undefined_terms'])}")
    if not next_results["has_next"]:
        issues.append("NEXT: marker missing")

    return {
        "teach_before_use": teach_results,
        "next_marker": next_results,
        "has_issues": len(issues) > 0,
        "issues": issues,
        "overall_score": (teach_results["score"] + (1.0 if next_results["has_next"] else 0.0)) / 2.0,
    }


def check_plan_continuity(plan_json: Dict) -> List[str]:
    """
    Check if the plan has proper continuity between sections/chapters.
    """
    issues = []

    if "chapters" in plan_json:
        chapters = plan_json["chapters"]
        for i, chapter in enumerate(chapters):
            if i > 0:
                # Simple check that there's some connection between chapters
                prev_title = chapters[i - 1].get("title", "")
                current_title = chapter.get("title", "")

                # Could add more sophisticated checks here
                if not prev_title or not current_title:
                    issues.append(f"Chapter {i+1} or previous has missing title")

    return issues
