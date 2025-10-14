#!/usr/bin/env python3
"""
minimal_snapshot.py — a minimal, deterministic snapshot capturing exactly what was requested.

What it captures (minimal, deterministic):
Code files: All .py under src/xsarena/, tools/min_snapshot.py, scripts/.sh, pyproject.toml, mypy.ini.
Rules: directives/_rules/rules.merged.md (canonical, merged from sources).
Recipes: All .yml under recipes/ (e.g., america-political-history.yml, clinical.en.yml).
Review: All .txt/.json under review/ (probes, inventories, summaries).
Models: models.json.
Trees/LS: For books, recipes, directives, .xsarena/jobs, review (structure + file lists).
"""

from __future__ import annotations
import hashlib
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


def main(out_path: str | None = None) -> int:
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
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) > 1 else main())