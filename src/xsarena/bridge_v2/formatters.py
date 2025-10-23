"""Formatting functions for the XSArena Bridge API."""

import json
import time


def format_text_chunk(content, finish_reason):
    """Format a text chunk as an OpenAI SSE chunk."""
    # Check if this is an image markdown
    if isinstance(content, str) and content.startswith("![Image]("):
        # For image content, we'll include it as content but may need special handling
        chunk = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "unknown",  # Will be filled in by caller
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": content},
                    "finish_reason": finish_reason,
                }
            ],
        }
    else:
        chunk = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "unknown",  # Will be filled in by caller
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": str(content)},
                    "finish_reason": finish_reason,
                }
            ],
        }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def format_image_chunk(content):
    """Format an image chunk as an OpenAI SSE chunk."""
    chunk = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "unknown",  # Will be filled in by caller
        "choices": [
            {"index": 0, "delta": {"content": str(content)}, "finish_reason": None}
        ],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def format_error_chunk(message, error_type):
    """Format an error chunk as an OpenAI SSE chunk."""
    chunk = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "unknown",  # Will be filled in by caller
        "error": {"type": error_type, "message": message},
        "choices": [{"index": 0, "delta": {}, "finish_reason": "error"}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def format_final_chunk(finish_reason):
    """Format a final chunk as an OpenAI SSE chunk."""
    chunk = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "unknown",  # Will be filled in by caller
        "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


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
