"""Atomic I/O operations for crash-safe file handling."""

import os
import tempfile
from pathlib import Path
from typing import Union


def atomic_write(
    path: Union[str, Path], content: Union[str, bytes], encoding: str = "utf-8"
) -> None:
    """
    Atomically write content to a file using a temporary file and rename.

    This ensures that the file is either completely written or remains unchanged,
    preventing partial writes during crashes.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create a temporary file in the same directory to ensure atomic rename
    with tempfile.NamedTemporaryFile(
        mode="w" if isinstance(content, str) else "wb",
        dir=path.parent,
        delete=False,
        encoding=encoding if isinstance(content, str) else None,
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)
        if isinstance(content, str):
            tmp_file.write(content)
        else:
            tmp_file.write(content)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())  # Ensure data is written to disk

    # Atomic rename - this either succeeds completely or fails without changing the target
    os.replace(str(tmp_path), str(path))


def atomic_append(
    path: Union[str, Path], content: str, encoding: str = "utf-8"
) -> None:
    """
    Atomically append content to a file.

    Reads existing content, appends new content, then writes atomically.
    """
    path = Path(path)
    existing_content = ""
    if path.exists():
        existing_content = path.read_text(encoding=encoding)

    new_content = existing_content + content
    atomic_write(path, new_content, encoding=encoding)
