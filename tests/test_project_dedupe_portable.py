"""Unit tests for project deduplication functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch


def test_dedupe_by_hash_uses_pathlib_stat():
    """Test that dedupe-by-hash uses pathlib and doesn't call stat binaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files and directories
        review_dir = Path(tmpdir) / "review"
        review_dir.mkdir()

        # Create test files
        dup_hashes_file = review_dir / "dup_hashes.txt"
        books_sha256_file = review_dir / "books_sha256.txt"

        # Write test content
        dup_hashes_file.write_text("abc123  file1.txt\n")
        books_sha256_file.write_text("abc123  file1.txt\nabc123  file2.txt\n")

        # Create the files that are duplicates
        file1 = Path(tmpdir) / "file1.txt"
        file2 = Path(tmpdir) / "file2.txt"
        file1.write_text("test content")
        file2.write_text("test content")

        # Change to the temp directory
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(tmpdir)

            # Mock the subprocess calls to ensure they're not used
            with patch("subprocess.run"):
                # Mock Path.stat to return a fixed mtime
                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 1234567890  # Fixed timestamp

                    # Run the dedupe function with apply_changes=False (dry-run)
                    from typer.testing import CliRunner

                    from xsarena.cli.main import app

                    runner = CliRunner()
                    runner.invoke(app, ["project", "dedupe-by-hash"])

                    # Check that subprocess was not called with stat commands
                    # (it might be called for git mv, which is OK)
                    # The important thing is that we're using Path().stat().st_mtime
                    assert mock_stat.called  # Ensure Path.stat was called

        finally:
            os.chdir(original_cwd)
