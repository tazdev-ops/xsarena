"""Text utilities for XSArena."""


def slugify(s: str, default: str = "default") -> str:
    """
    Convert a string to a URL-safe slug.
    
    Args:
        s: Input string to slugify
        default: Default value to return if result is empty
        
    Returns:
        Slugified string with only alphanumeric characters and hyphens
    """
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or default