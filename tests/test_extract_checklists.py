"""Tests for checklist extraction functionality."""

import os
import tempfile

from src.xsarena.utils.extractors import (
    ChecklistItem,
    extract_checklists,
    group_checklist_items_by_section,
    normalize_checklist_items,
)


def test_extract_checklists():
    """Test extraction of checklist items from content."""
    content = """
# Introduction
This is the introduction section.

## Section 1
- Add the required dependencies
- Configure the database connection
- Initialize the application
- Start the server

## Section 2
1. Verify the installation
2. Run the initial setup
3. Test the basic functionality
4. Deploy to production

## Section 3
This section has normal content without checklists.

## Section 4
- Check the logs for errors
- Validate the configuration
- Update the settings if needed
"""

    items = extract_checklists(content)

    # Should find checklist items
    assert len(items) > 0

    # Check that items are properly identified
    expected_items = [
        "the required dependencies",
        "the database connection",
        "the application",
        "the server",
        "the installation",
        "the initial setup",
        "the basic functionality",
        "to production",
        "the logs for errors",
        "the configuration",
        "the settings if needed",
    ]

    found_items = [item.item for item in items]
    for expected in expected_items:
        assert any(expected in found_item for found_item in found_items)

    print("✓ Checklist extraction test passed")


def test_normalize_checklist_items():
    """Test normalization of checklist items."""
    items = [
        ChecklistItem(
            "Section 1",
            "Add the required dependencies",
            "- Add the required dependencies",
            5,
        ),
        ChecklistItem(
            "Section 1",
            "Add the required dependencies",
            "- Add the required dependencies",
            10,
        ),  # Duplicate
        ChecklistItem(
            "Section 2", "Configure the database", "- Configure the database", 8
        ),
    ]

    normalized = normalize_checklist_items(items)

    # Should remove duplicates
    assert len(normalized) == 2  # Two unique items

    print("✓ Checklist normalization test passed")


def test_group_checklist_items_by_section():
    """Test grouping of checklist items by section."""
    items = [
        ChecklistItem("Section 1", "Add dependencies", "- Add dependencies", 5),
        ChecklistItem("Section 1", "Configure database", "- Configure database", 6),
        ChecklistItem("Section 2", "Run tests", "- Run tests", 10),
    ]

    grouped = group_checklist_items_by_section(items)

    # Should have 2 sections
    assert len(grouped) == 2
    assert "Section 1" in grouped
    assert "Section 2" in grouped
    assert len(grouped["Section 1"]) == 2
    assert len(grouped["Section 2"]) == 1

    print("✓ Checklist grouping test passed")


def test_extract_checklists_imperative_verbs():
    """Test extraction of checklist items starting with imperative verbs."""
    content = """
# Setup Guide
- Follow the installation steps carefully
- Configure the environment variables properly
- Test the connection before proceeding
- Document any issues encountered

## Troubleshooting
1. Check the logs for errors
2. Verify the configuration settings
3. Restart the service if needed
4. Contact support if problems persist
"""

    items = extract_checklists(content)

    # Should find items starting with imperative verbs
    assert len(items) >= 6  # Should find several items

    # Check that some expected items are found
    found_items = [item.item for item in items]
    assert any("installation steps" in item for item in found_items)
    assert any("environment variables" in item for item in found_items)
    assert any("connection before proceeding" in item for item in found_items)

    print("✓ Imperative verb checklist extraction test passed")


def test_extract_checklists_from_file():
    """Test extracting checklists from a file."""
    content = """
# Installation
- Install the required packages
- Set up the configuration

## Configuration
1. Configure the database
2. Set environment variables
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "test_book.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        from src.xsarena.utils.extractors import extract_checklists_from_file

        items = extract_checklists_from_file(file_path)

        # Should extract items from the file
        assert len(items) >= 4

        print("✓ File-based checklist extraction test passed")


def run_all_tests():
    """Run all checklist extraction tests."""
    print("Running checklist extraction tests...")

    test_extract_checklists()
    test_normalize_checklist_items()
    test_group_checklist_items_by_section()
    test_extract_checklists_imperative_verbs()
    test_extract_checklists_from_file()

    print("All checklist extraction tests passed! ✓")


if __name__ == "__main__":
    run_all_tests()
