"""Tests for NEXT hint extraction robustness (anchored terminal only)."""

import pytest
from xsarena.core.jobs.helpers import strip_next_lines


@pytest.mark.asyncio
async def test_strip_next_lines_terminal_bracketed_extracted():
    """Extract bracketed NEXT only if it's at the end."""
    content = "Some text\nNEXT: [Continue with Chapter 2]"
    result, hint = await strip_next_lines(content)
    assert result.strip() == "Some text"
    assert hint == "Continue with Chapter 2"


@pytest.mark.asyncio
async def test_strip_next_lines_terminal_bracketed_with_trailing_ws():
    """Terminal bracketed NEXT with trailing whitespace also counts as terminal."""
    content = "Intro\nNEXT: [Begin Chapter 1]   \n"
    result, hint = await strip_next_lines(content)
    assert result.strip() == "Intro"
    assert hint == "Begin Chapter 1"


@pytest.mark.asyncio
async def test_strip_next_lines_unbracketed_not_extracted():
    """Unbracketed NEXT should not be extracted (avoid false positives)."""
    content = "Some text\nNEXT: Continue with Chapter 2]\nMore text"
    result, hint = await strip_next_lines(content)
    assert result.strip() == "Some text\nNEXT: Continue with Chapter 2]\nMore text"
    assert hint is None


@pytest.mark.asyncio
async def test_strip_next_lines_mid_body_bracketed_removed_no_extract():
    """Mid-body bracketed NEXT is removed but not extracted."""
    content = "Some text\nNEXT: [Continue with Chapter 2]\nMore text"
    result, hint = await strip_next_lines(content)
    assert result.strip() == "Some text\nMore text"
    assert hint is None


@pytest.mark.asyncio
async def test_strip_next_lines_multiple_hints_last_not_terminal():
    """If last NEXT is not terminal, no extraction; all bracketed NEXT occurrences are removed."""
    content = "Text 1\nNEXT: [Hint 1]\nText 2\nNEXT: [Hint 2]\nText 3"
    result, hint = await strip_next_lines(content)
    assert result.strip() == "Text 1\nText 2\nText 3"
    assert hint is None


@pytest.mark.asyncio
async def test_strip_next_lines_multiple_hints_last_terminal():
    """If the LAST NEXT is terminal, it is extracted; earlier bracketed ones are removed."""
    content = "Text 1\nNEXT: [Hint 1]\nText 2\nNEXT: [Hint 2]"
    result, hint = await strip_next_lines(content)
    assert result.strip() == "Text 1\nText 2"
    assert hint == "Hint 2"


@pytest.mark.asyncio
async def test_strip_next_lines_mixed_hints():
    """Only bracketed terminal is extracted; mid-body bracketed removed; unbracketed preserved."""
    content = "Text 1\nNEXT: Unbracketed hint]\nText 2\nNEXT: [Bracketed hint]\nText 3"
    result, hint = await strip_next_lines(content)
    assert result.strip() == "Text 1\nNEXT: Unbracketed hint]\nText 2\nText 3"
    assert hint is None
