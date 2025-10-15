#!/usr/bin/env python3
"""
Minimal snapshot tool for XSArena.
Creates a single-file snapshot with essential files only (target ~400KB).
"""
import sys
from pathlib import Path
from datetime import datetime

def create_minimal_snapshot(output_path: Path = None):
    if output_path is None:
        output_path = Path.home() / "xsa_min_snapshot.txt"
    
    # Store the original working directory
    original_cwd = Path.cwd()
    
    # Open the output file for writing
    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write(f"# XSArena Minimal Snapshot\n")
        outfile.write(f"# Generated on: {datetime.now().isoformat()}\n")
        outfile.write(f"# Project root: {original_cwd}\n\n")
        
        # Add all essential files with specific inclusion patterns
        items_to_process = [
            # Project definition files
            ("files", ["pyproject.toml", "README.md", "mypy.ini", "config.jsonc", "models.json", "model_endpoint_map.json"]),
            
            # Source code directories
            ("dirs", ["src"]),
            
            # Test files
            ("dirs", ["tests"]),
            
            # Tool files
            ("files", ["tools/id_updater.py"]),
            
            # Script files
            ("dirs", ["scripts"]),
            
            # Directive files (rules, etc.)
            ("dirs", ["directives"]),
            
            # Documentation
            ("dirs", ["docs"]),
        ]
        
        for item_type, items in items_to_process:
            if item_type == "files":
                for file_path_str in items:
                    file_path = original_cwd / file_path_str
                    if file_path.exists() and file_path.is_file():
                        add_file_to_snapshot(outfile, file_path, original_cwd)
            elif item_type == "dirs":
                for dir_path_str in items:
                    dir_path = original_cwd / dir_path_str
                    if dir_path.exists() and dir_path.is_dir():
                        for file_path in dir_path.rglob("*"):
                            if file_path.is_file():
                                # Skip cache files and legacy content
                                file_str = str(file_path)
                                # Ensure the file path does not contain legacy or other excluded directories
                                should_skip = False
                                excluded_dirs = ["__pycache__", "legacy", "snapshot", "gomobile-matsuri-src", 
                                               ".pytest_cache", ".ruff_cache", ".git", "venv", "target", "dist", "build"]
                                excluded_exts = [".pyc", ".pyo", ".tar.gz", ".zip", ".egg-info"]
                                
                                for excl_dir in excluded_dirs:
                                    if f"/{excl_dir}/" in file_str or file_str.startswith(excl_dir + "/") or file_str == excl_dir:
                                        should_skip = True
                                        break
                                
                                if not should_skip:
                                    for excl_ext in excluded_exts:
                                        if file_str.endswith(excl_ext):
                                            should_skip = True
                                            break
                                
                                if not should_skip:
                                    add_file_to_snapshot(outfile, file_path, original_cwd)
    
    print(f"Minimal snapshot created at: {output_path}")

def add_file_to_snapshot(outfile, file_path, project_root):
    """Helper function to add a single file to the snapshot"""
    if file_path.exists() and file_path.is_file():
        try:
            # Get the relative path from the project root
            relative_path = file_path.relative_to(project_root)
            outfile.write(f"--- START OF FILE {relative_path} ---\n")
            content = file_path.read_text(encoding='utf-8')
            outfile.write(content)
            outfile.write("\n")
            outfile.write(f"--- END OF FILE {relative_path} ---\n\n")
        except ValueError:
            # If the file is not relative to the project root, skip it
            pass
        except Exception as e:
            outfile.write(f"# Error reading file {file_path}: {e}\n")

if __name__ == "__main__":
    output_path = None
    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])
    create_minimal_snapshot(output_path)