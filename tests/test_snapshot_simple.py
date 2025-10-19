"""Test snapshot functionality."""
import tempfile
import shutil
from pathlib import Path
import zipfile

def test_snapshot_simple():
    """Test basic snapshot functionality."""
    from xsarena.utils.snapshot_simple import write_zip_snapshot
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Change to the temp directory to run the snapshot
        original_cwd = Path.cwd()
        import os
        os.chdir(tmp_dir)
        
        try:
            # Create some test files in the current directory
            src_dir = Path("src")
            src_dir.mkdir()
            (src_dir / "test.py").write_text("# Test file\nprint('hello')")
            
            # Create a snapshot file
            snapshot_path = Path("test_snapshot.zip")
            
            # Test building snapshot
            write_zip_snapshot(
                out_path=str(snapshot_path),
                mode="minimal",  # Use minimal mode to avoid including too many files
            )
            
            # Verify snapshot was created
            assert snapshot_path.exists()
            
            # Verify it's a zip file (has zip signature)
            with open(snapshot_path, 'rb') as f:
                header = f.read(4)
                # ZIP files start with 0x504B0304 (PK♥♦)
                assert header[:2] == b'PK'
            
            # Verify it's a valid zip by trying to read it
            with zipfile.ZipFile(snapshot_path, 'r') as zip_file:
                file_list = zip_file.namelist()
                # Should have at least snapshot.txt manifest
                assert 'snapshot.txt' in file_list
                
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
        
        print("✓ Snapshot test passed")