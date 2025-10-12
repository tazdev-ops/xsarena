#!/usr/bin/env python3
"""
Advanced Project Snapshot with Chunking - Just Works™
Creates one text file or multiple chunks with all your source code.
"""

import os
import math
from pathlib import Path

# What to skip (add your own as needed)
SKIP_DIRS = {
    '__pycache__', '.git', '.venv', 'venv', 'node_modules',
    '.pytest_cache', '.mypy_cache', '.ruff_cache',
    'snapshot_chunks', 'snapshots', '.xsarena',
    'dist', 'build', 'src/xsarena.egg-info',
}

SKIP_EXTENSIONS = {
    '.pyc', '.pyo', '.png', '.jpg', '.pdf', '.zip', 
    '.tar', '.gz', '.mp4', '.mp3',
}

SKIP_FILES = {
    'snapshot.txt', 'preview_snapshot.txt', 'final_snapshot.txt',
}

def should_skip(path, root):
    """Simple check: should we skip this?"""
    rel = path.relative_to(root)
    
    # Skip hidden files/dirs
    if any(p.startswith('.') for p in rel.parts):
        if not rel.parts[0] in {'.', '..'}:  # Allow current dir
            return True
    
    # Skip specific directories
    if any(p in SKIP_DIRS for p in rel.parts):
        return True
    
    # Skip specific files
    if path.name in SKIP_FILES:
        return True
    
    # Skip by extension
    if path.suffix in SKIP_EXTENSIONS:
        return True
    
    return False

def is_text(path):
    """Quick text check."""
    # Check extension first
    text_exts = {'.py', '.md', '.txt', '.yml', '.yaml', '.json', 
                 '.toml', '.sh', '.js', '.css', '.html', '.xml'}
    if path.suffix in text_exts:
        return True
    
    # Try reading a bit
    try:
        with open(path, 'rb') as f:
            sample = f.read(1024)
            return b'\x00' not in sample  # No null bytes = probably text
    except:
        return False

def create_snapshot_chunked(chunk_size=100000):
    """Create a chunked project snapshot."""
    root = Path('.').resolve()
    
    # Collect files
    files = []
    for f in root.rglob('*'):
        if f.is_file() and not should_skip(f, root) and is_text(f):
            files.append(f)
    
    files.sort()  # Consistent order
    
    print(f"📦 Found {len(files)} files")
    
    # Build full snapshot content
    content = []
    content.append(f"PROJECT: {root.name}")
    content.append(f"FILES: {len(files)}")
    content.append("=" * 80)
    content.append("")
    
    # Table of contents
    content.append("CONTENTS:")
    for i, f in enumerate(files, 1):
        content.append(f"  {i}. {f.relative_to(root)}")
    content.append("")
    content.append("=" * 80)
    content.append("")
    
    # Each file
    for f in files:
        rel = f.relative_to(root)
        content.append(f"\n{'=' * 80}")
        content.append(f"FILE: {rel}")
        content.append(f"{'=' * 80}")
        
        try:
            file_content = f.read_text(encoding='utf-8', errors='replace')
            content.append(file_content)
            if not file_content.endswith('\n'):
                content.append('\n')
        except Exception as e:
            content.append(f"[Could not read: {e}]\n")
        
        content.append(f"\n{'─' * 80}")
    
    full_content = "\n".join(content)
    
    # Create directory for chunks if it doesn't exist
    os.makedirs('snapshot_chunks', exist_ok=True)
    
    # Calculate number of chunks needed
    total_size = len(full_content)
    num_chunks = math.ceil(total_size / chunk_size)
    
    print(f"File size: {total_size} characters")
    print(f"Chunk size: {chunk_size} characters")
    print(f"Number of chunks: {num_chunks}")
    
    # Write each chunk
    for i in range(num_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, total_size)
        chunk_content = full_content[start:end]
        
        chunk_filename = f'snapshot_chunks/snapshot_chunk_{i+1:03d}.txt'
        with open(chunk_filename, 'w', encoding='utf-8') as f:
            f.write(f'# Chunk {i+1}/{num_chunks}\n')
            f.write(f'# Characters {start+1} to {end} of {total_size}\n')
            f.write('# ---\n')
            f.write(chunk_content)
        
        print(f'Created: {chunk_filename} ({len(chunk_content)} chars)')
    
    print(f'✅ Chunking complete! {num_chunks} chunks created in snapshot_chunks/ directory')
    
    # Also save the full version
    with open('snapshot.txt', 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    size = Path('snapshot.txt').stat().st_size / 1024 / 1024
    print(f"✅ Full snapshot written to snapshot.txt ({size:.1f}MB)")

def main():
    create_snapshot_chunked()

if __name__ == '__main__':
    main()