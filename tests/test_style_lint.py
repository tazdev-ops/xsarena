"""Tests for style_lint functionality."""

import os
import tempfile

from xsarena.utils.style_lint import (
    LintIssue,
    analyze_style,
    generate_style_report,
    save_style_report,
)


def test_style_lint_bullet_walls():
    """Test detection of bullet walls in content."""
    content = """
# Introduction
This is a section with normal content.

## Section 1
- First point
- Second point
- Third point
- Fourth point
- Fifth point
- Sixth point
- Seventh point
- Eighth point
- Ninth point
- Tenth point
- Eleventh point
- Twelfth point
- Thirteenth point

## Section 2
This is a normal paragraph with appropriate length and good structure.
"""

    issues = analyze_style(content, "narrative")

    # Should detect bullet wall in Section 1
    bullet_wall_issues = [issue for issue in issues if issue.type == "bullet_wall"]
    assert len(bullet_wall_issues) > 0
    assert any("Section 1" in issue.section for issue in bullet_wall_issues)

    print("✓ Bullet wall detection test passed")


def test_style_lint_paragraph_length():
    """Test detection of paragraph length issues."""
    content = """
# Introduction
Short.
Another short.
Yet another short.
This is a much longer paragraph that has more than the minimum required words to be considered properly formed and well-structured for readability purposes.
"""

    issues = analyze_style(content, "narrative")

    # Should detect short paragraphs
    para_len_issues = [issue for issue in issues if issue.type == "paragraph_len"]
    assert len(para_len_issues) > 0

    print("✓ Paragraph length detection test passed")


def test_style_lint_heading_density():
    """Test detection of heading density issues."""
    content = """
# Introduction
Content here.

## Heading 1
Content here.

### Subheading 1
Content here.

### Subheading 2
Content here.

### Subheading 3
Content here.

### Subheading 4
Content here.

### Subheading 5
Content here.

### Subheading 6
Content here.

### Subheading 7
Content here.

### Subheading 8
Content here.

### Subheading 9
Content here.

### Subheading 10
Content here.

### Subheading 11
Content here.

### Subheading 12
Content here.

# Section 2
Normal content.
"""

    issues = analyze_style(content, "narrative")

    # Should detect high heading density in Introduction section
    heading_density_issues = [
        issue for issue in issues if issue.type == "heading_density"
    ]
    assert len(heading_density_issues) > 0

    print("✓ Heading density detection test passed")


def test_style_lint_term_definitions():
    """Test detection of undefined terms."""
    content = """
# Introduction
This section uses **technical_term** without defining it first.
Another paragraph mentions **another_term** that should be defined.
The term **technical_term** is used again here.
"""

    issues = analyze_style(content, "narrative")

    # Should detect undefined terms
    term_def_issues = [issue for issue in issues if issue.type == "term_definition"]
    assert len(term_def_issues) > 0

    print("✓ Term definition detection test passed")


def test_generate_style_report():
    """Test generation of style report."""
    issues = [
        LintIssue(
            type="bullet_wall",
            section="Section 1",
            severity="high",
            message="Section has 15 bullet points - potential bullet wall",
            suggestion="Consider converting some bullets to prose paragraphs",
        ),
        LintIssue(
            type="paragraph_len",
            section="Section 2",
            severity="medium",
            message="Average paragraph length is 1.5 words - too short",
            suggestion="Increase to ~5-15 words per paragraph for better readability",
        ),
    ]

    report = generate_style_report(issues, "test_book.md", "narrative")

    # Check that report contains expected elements
    assert "Style Lint Report" in report
    assert "test_book.md" in report
    assert "narrative" in report
    assert "Bullet Wall" in report
    assert "Paragraph Len" in report

    print("✓ Style report generation test passed")


def test_save_style_report():
    """Test saving style report to file."""
    [
        LintIssue(
            type="bullet_wall",
            section="Section 1",
            severity="high",
            message="Section has 15 bullet points - potential bullet wall",
            suggestion="Consider converting some bullets to prose paragraphs",
        )
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "style_report.md")
        save_style_report("Test report content", output_path)

        # Check that file was created
        assert os.path.exists(output_path)

        # Check that file contains expected content
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Test report content" in content

    print("✓ Style report save test passed")


def run_all_tests():
    """Run all style_lint tests."""
    print("Running style_lint tests...")

    test_style_lint_bullet_walls()
    test_style_lint_paragraph_length()
    test_style_lint_heading_density()
    test_style_lint_term_definitions()
    test_generate_style_report()
    test_save_style_report()

    print("All style_lint tests passed! ✓")


if __name__ == "__main__":
    run_all_tests()
