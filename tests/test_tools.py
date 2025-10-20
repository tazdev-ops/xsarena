"""Tests for tools functionality."""

import tempfile
from pathlib import Path

import pytest

from xsarena.core.tools import PathJail, append_file, list_dir, read_file, write_file


def test_path_jail_safe_paths():
    """Test that PathJail allows safe paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        jail = PathJail(temp_dir)

        # Create a safe subdirectory
        safe_path = Path(temp_dir) / "safe_dir"
        safe_path.mkdir(exist_ok=True)

        # Test safe path resolution
        result = jail.resolve_path("safe_dir")
        assert str(result).startswith(temp_dir)


def test_path_jail_escape_prevention():
    """Test that PathJail prevents path escape."""
    with tempfile.TemporaryDirectory() as temp_dir:
        jail = PathJail(temp_dir)

        # Try to escape the jail with .. sequences
        with pytest.raises(ValueError):
            jail.resolve_path("../../etc/passwd")

        with pytest.raises(ValueError):
            jail.resolve_path("/absolute/path/outside/jail")


def test_path_jail_file_operations():
    """Test file operations using the tools functions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        jail = PathJail(temp_dir)

        # Create a file within the jail
        test_content = "test content"
        write_file("test.txt", test_content, path_jail=jail)

        # Read it back
        content = read_file("test.txt", path_jail=jail)
        assert content == test_content

        # Append to it
        append_file("test.txt", " additional content", path_jail=jail)
        content = read_file("test.txt", path_jail=jail)
        assert "additional content" in content


def test_path_jail_directory_operations():
    """Test directory operations within the jail."""
    with tempfile.TemporaryDirectory() as temp_dir:
        jail = PathJail(temp_dir)

        # Create a subdirectory using the tools function
        subdir_path = Path(temp_dir) / "subdir"
        subdir_path.mkdir(exist_ok=True)

        # List directory contents
        contents = list_dir(".", path_jail=jail)
        assert "subdir" in [Path(p).name for p in contents]
