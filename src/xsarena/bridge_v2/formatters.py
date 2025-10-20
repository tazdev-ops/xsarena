"""Formatting functions for the XSArena Bridge API."""

import json
import time


def format_openai_chunk(content, model, request_id):
    """Format a text chunk as an OpenAI SSE chunk."""
    # Check if this is an image markdown
    if isinstance(content, str) and content.startswith("![Image]("):
        # For image content, we'll include it as content but may need special handling
        chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {"index": 0, "delta": {"content": content}, "finish_reason": None}
            ],
        }
    else:
        chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {"index": 0, "delta": {"content": str(content)}, "finish_reason": None}
            ],
        }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def format_openai_finish_chunk(model, request_id, reason="stop"):
    """Format a finish chunk as an OpenAI SSE chunk."""
    chunk = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": reason}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def add_content_filter_explanation(content, finish_reason):
    """Add explanation for content-filter finish reason."""
    if finish_reason == "content_filter":
        return (
            content
            + "\n\nResponse was truncated (filter/limit). Consider reducing length or simplifying."
        )
    return content
