"""Helper functions for job execution in XSArena."""

import asyncio
import re
from typing import Dict, List, Optional


async def strip_next_lines(content: str) -> tuple[str, Optional[str]]:
    """Strip terminal NEXT directive variants and return hint."""
    patterns = [
        r"\s*NEXT\s*:\s*([^\]]+)\]\s*$",
        r"\s*Next\s*:\s*([^\]]+)\]\s*$",
        r"\s*next\s*:\s*([^\]]+)\]\s*$",
    ]
    hint = None
    for pat in patterns:
        m = re.search(pat, content, flags=re.IGNORECASE)
        if m:
            if m.groups():
                hint = m.group(1).strip()
            content = re.sub(pat, "", content, count=1, flags=re.IGNORECASE)
            break
    # Purge any mid-body NEXT hints safely
    content = re.sub(
        r"\n?\s*NEXT\s*:\s*[^\]]*\]\s*\n?", "\n", content, flags=re.IGNORECASE
    )
    return content.strip(), hint


async def drain_next_hint(
    jid: str, control_queues: Dict[str, asyncio.Queue]
) -> Optional[str]:
    """Drain queued 'next' hints and return the latest text if any; requeue other messages."""
    q = control_queues.get(jid)
    if not q:
        return None
    pending: List[dict] = []
    latest: Optional[str] = None
    while True:
        try:
            msg = q.get_nowait()
            if msg.get("type") == "next":
                latest = msg.get("text") or latest
            else:
                pending.append(msg)
        except asyncio.QueueEmpty:
            break
    for m in pending:
        await q.put(m)
    return latest
