"""Recipes module for XSArena - contains functions to create job recipes."""

from typing import Any, Dict


def recipe_from_mixer(
    subject: str,
    task: str,
    system_text: str,
    out_path: str,
    min_chars: int = 4200,
    passes: int = 1,
    max_chunks: int = 12,
) -> Dict[str, Any]:
    """
    Create a recipe dictionary from mixer parameters.

    Args:
        subject: The subject of the book/article
        task: The task to perform (e.g., "book.zero2hero")
        system_text: The system prompt text
        out_path: Output file path
        min_chars: Minimum characters per chunk
        passes: Number of auto-extend passes
        max_chunks: Maximum number of chunks

    Returns:
        Dictionary containing the recipe configuration
    """
    recipe = {
        "task": task,
        "subject": subject,
        "system_text": system_text,
        "max_chunks": max_chunks,
        "continuation": {
            "mode": "anchor",
            "minChars": min_chars,
            "pushPasses": passes,
            "repeatWarn": True,
        },
        "io": {"output": "file", "outPath": out_path},
    }

    return recipe
