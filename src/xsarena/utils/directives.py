from pathlib import Path
from typing import Optional, Tuple


def find_directive(name: str) -> Optional[Tuple[Path, Optional[Path]]]:
    """Find a directive prompt and its corresponding schema."""
    base_dirs = [
        Path("directives"),
        Path("directives/_mixer"),
        Path("directives/_preview"),
    ]

    prompt_path: Optional[Path] = None
    for base in base_dirs:
        p = base / f"{name}.prompt.md"
        if p.exists():
            prompt_path = p
            break
        p = base / f"prompt.{name}.json.md"
        if p.exists():
            prompt_path = p
            break
    if not prompt_path:
        return None

    schema_path = Path("data/schemas") / f"{name}.schema.json"
    if not schema_path.exists():
        schema_path = None
    return prompt_path, schema_path
