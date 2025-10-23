# tests/unit/test_strip_next_lines_basic.py
import pytest
from xsarena.core.jobs.helpers import strip_next_lines


@pytest.mark.asyncio
async def test_strip_next_lines_bracketed_tail_hint():
    content = "Intro paragraph.\n\nBody continues.\n\nNEXT: [Begin Chapter 1]"
    stripped, hint = await strip_next_lines(content)
    assert "NEXT:" not in stripped
    assert hint == "Begin Chapter 1"


@pytest.mark.asyncio
async def test_strip_next_lines_mid_body_purge():
    content = "Intro.\n\nNEXT: [Continue]\n\nBody."
    stripped, hint = await strip_next_lines(content)
    # Mid-body NEXT is removed from body; no tail hint extracted in this case.
    assert "NEXT:" not in stripped
    # Depending on how you treat mid-body lines, hint may be None or captured earlier.
    # Current implementation only captures tail; so expect None.
    assert hint is None
