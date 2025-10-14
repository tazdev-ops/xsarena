#!/usr/bin/env python3
"""
snapshot_chunk.py — Create a minimal snapshot and chunk it with required message.

This utility creates a minimal snapshot of the requested files and then chunks
it with the message "Just say received. do nothing. i will send you the rest of the code"
appended to each chunk.
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_code_files() -> list[Path]:
    """Collect all .py files under src/xsarena/"""
    files: list[Path] = []
    
    # All .py files under src/xsarena/
    src_dir = Path("src/xsarena")
    if src_dir.exists():
        for p in src_dir.rglob("*.py"):
            if p.is_file():
                files.append(p)
    
    # Add specific files
    specific_files = ["tools/min_snapshot.py", "pyproject.toml", "mypy.ini"]
    for f in specific_files:
        p = Path(f)
        if p.exists() and p.is_file():
            files.append(p)
    
    # Add all .sh files under scripts/
    scripts_dir = Path("scripts")
    if scripts_dir.exists():
        for p in scripts_dir.rglob("*.sh"):
            if p.is_file():
                files.append(p)
    
    files = sorted({str(p): p for p in files}.values(), key=lambda x: str(x).lower())
    return files


def _collect_rules_files() -> list[Path]:
    """Collect rules files"""
    files: list[Path] = []
    
    # directives/_rules/rules.merged.md
    p = Path("directives/_rules/rules.merged.md")
    if p.exists() and p.is_file():
        files.append(p)
    
    return files


def _collect_recipe_files() -> list[Path]:
    """Collect all .yml files under recipes/"""
    files: list[Path] = []
    
    recipes_dir = Path("recipes")
    if recipes_dir.exists():
        for p in recipes_dir.rglob("*.yml"):
            if p.is_file():
                files.append(p)
    
    return files


def _collect_review_files() -> list[Path]:
    """Collect all .txt/.json files under review/"""
    files: list[Path] = []
    
    review_dir = Path("review")
    if review_dir.exists():
        for ext in [".txt", ".json"]:
            for p in review_dir.rglob(f"*{ext}"):
                if p.is_file():
                    files.append(p)
    
    return files


def _collect_model_files() -> list[Path]:
    """Collect models.json"""
    files: list[Path] = []
    
    p = Path("models.json")
    if p.exists() and p.is_file():
        files.append(p)
    
    return files


def _build_tree(paths: list[Path]) -> dict:
    """Build a tree structure from a list of paths"""
    root: dict = {}
    for p in paths:
        parts = Path(p).parts
        cur = root
        for i, part in enumerate(parts):
            is_file = (i == len(parts) - 1)
            cur.setdefault(part, {} if not is_file else None)
            if cur[part] is None:
                break
            cur = cur[part]
    return root


def _print_tree(d: dict, prefix: str = "", out_lines: list[str] | None = None) -> list[str]:
    """Print tree structure"""
    if out_lines is None:
        out_lines = []
    items = sorted(d.items(), key=lambda kv: kv[0].lower())
    for i, (name, sub) in enumerate(items):
        last = i == len(items) - 1
        branch = "└── " if last else "├── "
        out_lines.append(f"{prefix}{branch}{name}")
        if isinstance(sub, dict):
            ext = "    " if last else "│   "
            _print_tree(sub, prefix + ext, out_lines)
    return out_lines


def _write_tree(w, title: str, root_path: Path):
    """Write a tree structure to the output file"""
    w.write(f"===== TREE {title} =====\n")
    if not root_path.exists():
        w.write("(missing)\n")
        w.write(f"===== END TREE {title} =====\n\n")
        return
    paths = [p for p in root_path.rglob("*")]
    d = _build_tree(paths if paths else [root_path])
    for line in _print_tree(d):
        w.write(line + "\n")
    w.write(f"===== END TREE {title} =====\n\n")


def create_snapshot(out_path: str | None = None) -> Path:
    """Create the minimal snapshot"""
    if not out_path:
        out = Path.home() / "xsa_min_snapshot.txt"
    else:
        out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Collect all the required files
    code_files = _collect_code_files()
    rules_files = _collect_rules_files()
    recipe_files = _collect_recipe_files()
    review_files = _collect_review_files()
    model_files = _collect_model_files()

    with out.open("w", encoding="utf-8") as w:
        w.write("XSArena Minimal Snapshot\n")
        w.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        w.write(f"Code files: {len(code_files)}\n")
        w.write(f"Rules files: {len(rules_files)}\n")
        w.write(f"Recipe files: {len(recipe_files)}\n")
        w.write(f"Review files: {len(review_files)}\n")
        w.write(f"Model files: {len(model_files)}\n\n")

        # Write trees for specific directories
        tree_dirs = ["books", "recipes", "directives", ".xsarena/jobs", "review"]
        for name in tree_dirs:
            _write_tree(w, name, Path(name))

        # Write LS (file lists) for the same directories
        w.write("===== LS (books|recipes|directives|.xsarena/jobs|review) =====\n")
        for name in tree_dirs:
            rp = Path(name)
            if rp.exists():
                for p in sorted([*rp.rglob("*")], key=lambda x: str(x).lower()):
                    if p.is_file():
                        w.write(str(p) + "\n")
        w.write("===== END LS =====\n\n")

        # Write all code files (full content)
        overall = hashlib.sha256()
        for p in code_files:
            w.write(f"\n===== BEGIN FILE: {p} =====\n")
            try:
                txt = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                txt = p.read_bytes().decode("utf-8", errors="replace")
            w.write(txt.rstrip("\n") + "\n")
            w.write(f"===== END FILE: {p} =====\n")
            overall.update(_sha256_file(p).encode("utf-8"))

        # Write rules files
        for p in rules_files:
            w.write(f"\n===== BEGIN RULES FILE: {p} =====\n")
            try:
                txt = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                txt = p.read_bytes().decode("utf-8", errors="replace")
            w.write(txt.rstrip("\n") + "\n")
            w.write(f"===== END RULES FILE: {p} =====\n")

        # Write recipe files
        for p in recipe_files:
            w.write(f"\n===== BEGIN RECIPE FILE: {p} =====\n")
            try:
                txt = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                txt = p.read_bytes().decode("utf-8", errors="replace")
            w.write(txt.rstrip("\n") + "\n")
            w.write(f"===== END RECIPE FILE: {p} =====\n")

        # Write review files
        for p in review_files:
            w.write(f"\n===== BEGIN REVIEW FILE: {p} =====\n")
            try:
                txt = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                txt = p.read_bytes().decode("utf-8", errors="replace")
            w.write(txt.rstrip("\n") + "\n")
            w.write(f"=== END REVIEW FILE: {p} =====\n")

        # Write model files
        for p in model_files:
            w.write(f"\n===== BEGIN MODEL FILE: {p} =====\n")
            try:
                txt = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                txt = p.read_bytes().decode("utf-8", errors="replace")
            w.write(txt.rstrip("\n") + "\n")
            w.write(f"===== END MODEL FILE: {p} =====\n")

        # Code manifest digest
        w.write("\n===== MANIFEST (CODE) =====\n")
        for p in code_files:
            w.write(f"{str(p)}  {_sha256_file(p)}\n")
        w.write(f"===== SNAPSHOT DIGEST: {overall.hexdigest()} =====\n")

    print(f"Wrote minimal snapshot → {out}")
    return out


def chunk_file(input_file: Path, chunk_size: int = 350000, output_dir: str = "~/snapshot_chunks"):
    """
    Chunk the input file into smaller pieces with a message appended to each chunk.
    
    Args:
        input_file: Path to the input file to be chunked
        chunk_size: Size of each chunk in bytes (default 350KB to aim for ~350kb total)
        output_dir: Directory to store the chunks (default: ~/snapshot_chunks)
    """
    # Expand home directory
    output_dir_expanded = Path(output_dir).expanduser()
    # Create output directory
    output_dir_expanded.mkdir(parents=True, exist_ok=True)
    
    # Read the input file
    with open(input_file, 'rb') as f:
        content = f.read()
    
    # Calculate number of chunks
    num_chunks = (len(content) + chunk_size - 1) // chunk_size  # Ceiling division
    
    # Create the message to append
    message = "\n\nJust say received. do nothing. i will send you the rest of the code\n"
    
    # Split file into chunks and write each with the message
    for i in range(num_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, len(content))
        chunk_data = content[start:end]
        
        # Create chunk filename
        chunk_filename = f"chunk_{i+1:03d}.txt"
        chunk_path = output_dir_expanded / chunk_filename
        
        # Write chunk data + message
        with open(chunk_path, 'wb') as chunk_file:
            chunk_file.write(chunk_data)
            chunk_file.write(message.encode('utf-8'))
    
    print(f"Chunked {input_file} into {num_chunks} chunks in {output_dir_expanded}/")
    print(f"Chunk size: {chunk_size} bytes, Total chunks: {num_chunks}")
    return num_chunks


def main():
    parser = argparse.ArgumentParser(
        description="Create a minimal snapshot and chunk it with required message"
    )
    parser.add_argument(
        "-s", "--size",
        type=int,
        default=350000,  # Updated default to better match the 300-400KB range
        help="Chunk size in bytes (default: 350000 = 350KB)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="~/snapshot_chunks",
        help="Output directory for chunks (default: ~/snapshot_chunks)"
    )
    parser.add_argument(
        "--snapshot-path",
        help="Path for the snapshot file (default: ~/xsa_min_snapshot.txt)"
    )
    parser.add_argument(
        "--optimized",
        action="store_true",
        help="Use optimized snapshot (300-400KB range)"
    )
    
    args = parser.parse_args()
    
    # Create the snapshot
    if args.optimized:
        # Use the optimized snapshot
        if not args.snapshot_path:
            snapshot_path = Path.home() / "xsa_min_snapshot.txt"
        else:
            snapshot_path = Path(args.snapshot_path)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run the optimized snapshot creation by calling the script
        import subprocess
        result = subprocess.run([sys.executable, str(Path(__file__).parent / "minimal_snapshot_optimized.py"), str(snapshot_path)], 
                                capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error creating optimized snapshot: {result.stderr}")
            return result.returncode
    else:
        snapshot_path = create_snapshot(args.snapshot_path)
    
    # Chunk the snapshot
    chunk_file(snapshot_path, args.size, args.output_dir)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())