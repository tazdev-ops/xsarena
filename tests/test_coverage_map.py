"""Tests for coverage map functionality."""

import os
import tempfile

from src.xsarena.utils.coverage import (
    CoverageItem,
    analyze_coverage,
    generate_coverage_report,
    save_coverage_report,
)


def test_parse_outline():
    """Test parsing of outline files."""
    from src.xsarena.utils.coverage import parse_outline

    outline_content = """# Introduction
## Background
## Goals
# Main Content
## Section 1
### Subsection 1.1
### Subsection 1.2
## Section 2
# Conclusion
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        outline_path = os.path.join(temp_dir, "outline.md")
        with open(outline_path, "w", encoding="utf-8") as f:
            f.write(outline_content)

        items = parse_outline(outline_path)

        # Should find all headings
        assert len(items) == 8  # All headings from the outline

        # Check that items have correct properties
        assert items[0].title == "Introduction"
        assert items[0].level == 1
        assert items[1].title == "Background"
        assert items[1].level == 2
        assert items[4].title == "Section 1"
        assert items[4].level == 2
        assert items[5].title == "Subsection 1.1"
        assert items[5].level == 3

        print("✓ Outline parsing test passed")


def test_coverage_analysis():
    """Test coverage analysis between outline and book."""

    outline_content = """# Introduction
## Background
## Goals
# Main Content
## Section 1
## Section 2
# Conclusion
"""

    book_content = """# Introduction
This is the introduction content that covers the introduction topic.

## Background
This section covers the background information in detail.

## Goals
The goals of this document are clearly outlined here.

# Main Content
This section covers the main content of the document.

## Section 1
This is the content for section 1, which is well covered.

## Section 2
This section is also well covered with substantial content.

# Conclusion
Finally, we conclude with a summary of what was covered.
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        outline_path = os.path.join(temp_dir, "outline.md")
        book_path = os.path.join(temp_dir, "book.md")

        with open(outline_path, "w", encoding="utf-8") as f:
            f.write(outline_content)

        with open(book_path, "w", encoding="utf-8") as f:
            f.write(book_content)

        items = analyze_coverage(outline_path, book_path)

        # All items should be covered since the book contains all outline topics
        covered_count = sum(
            1 for item in items if item.status in ["Covered", "Partial"]
        )
        assert covered_count == len(items)

        print("✓ Coverage analysis test passed")


def test_coverage_analysis_missing_items():
    """Test coverage analysis with missing items."""
    outline_content = """# Introduction
## Background
## Goals
# Advanced Topics
## Deep Learning
## Neural Networks
"""

    book_content = """# Introduction
This is the introduction content.

## Background
This section covers the background information.

# Advanced Topics
This section covers advanced topics but not all of them.
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        outline_path = os.path.join(temp_dir, "outline.md")
        book_path = os.path.join(temp_dir, "book.md")

        with open(outline_path, "w", encoding="utf-8") as f:
            f.write(outline_content)

        with open(book_path, "w", encoding="utf-8") as f:
            f.write(book_content)

        items = analyze_coverage(outline_path, book_path)

        # Should have some missing items (Goals, Deep Learning, Neural Networks)
        missing_items = [item for item in items if item.status == "Missing"]
        assert (
            len(missing_items) >= 2
        )  # Goals, Deep Learning, and Neural Networks are missing

        print("✓ Coverage analysis with missing items test passed")


def test_generate_coverage_report():
    """Test generation of coverage report."""
    items = [
        CoverageItem(
            title="Introduction", level=1, content="", status="Covered", confidence=0.9
        ),
        CoverageItem(
            title="Background", level=2, content="", status="Partial", confidence=0.5
        ),
        CoverageItem(
            title="Goals", level=2, content="", status="Missing", confidence=0.0
        ),
        CoverageItem(
            title="Main Content", level=1, content="", status="Covered", confidence=0.8
        ),
    ]

    report = generate_coverage_report(items, "outline.md", "book.md")

    # Check that report contains expected elements
    assert "Coverage Report" in report
    assert "outline.md" in report
    assert "book.md" in report
    assert "Total items: 4" in report
    assert "Covered: 2" in report
    assert "Partial: 1" in report
    assert "Missing: 1" in report
    assert "Introduction" in report
    assert "Background" in report
    assert "Goals" in report
    assert "Main Content" in report

    print("✓ Coverage report generation test passed")


def test_save_coverage_report():
    """Test saving coverage report to file."""
    items = [
        CoverageItem(
            title="Introduction", level=1, content="", status="Covered", confidence=0.9
        ),
    ]

    report = generate_coverage_report(items, "outline.md", "book.md")

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "coverage_report.md")
        save_coverage_report(report, output_path)

        # Check that file was created
        assert os.path.exists(output_path)

        # Check that file contains expected content
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Coverage Report" in content
            assert "outline.md" in content

    print("✓ Coverage report save test passed")


def run_all_tests():
    """Run all coverage map tests."""
    print("Running coverage map tests...")

    test_parse_outline()
    test_coverage_analysis()
    test_coverage_analysis_missing_items()
    test_generate_coverage_report()
    test_save_coverage_report()

    print("All coverage map tests passed! ✓")


if __name__ == "__main__":
    run_all_tests()
