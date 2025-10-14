#!/usr/bin/env python3
"""
minimal_snapshot_optimized.py — an optimized minimal snapshot within 300-400KB range.

What it captures (minimal, deterministic, size-optimized):
Code files: Essential .py under src/xsarena/ (core, cli; limited to most important files).
Rules: directives/_rules/rules.merged.md (canonical, merged from sources).
Recipes: All .yml under recipes/ (only small ones).
Review: All .txt/.json under review/ (only small ones).
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
    """Collect essential .py files under src/xsarena/ (limited to most important)"""
    files: list[Path] = []
    
    # Essential core files only
    essential_core = [
        "src/xsarena/core/config.py",
        "src/xsarena/core/redact.py",
        "src/xsarena/core/prompt.py",
        "src/xsarena/core/jobs2_runner.py",
        "src/xsarena/core/recipes.py",
        "src/xsarena/core/specs.py",
        "src/xsarena/core/artifacts.py",
        "src/xsarena/core/orchestrator.py",
        "src/xsarena/core/profiles.py",
        "src/xsarena/core/backends.py",
        "src/xsarena/core/chunking.py",
        "src/xsarena/core/engine.py",
        "src/xsarena/core/state.py",
        "src/xsarena/core/tools.py",
        "src/xsarena/core/templates.py",
    ]
    
    for f in essential_core:
        p = Path(f)
        if p.exists() and p.is_file():
            files.append(p)
    
    # Essential CLI files only
    essential_cli = [
        "src/xsarena/cli/main.py",
        "src/xsarena/cli/context.py",
        "src/xsarena/cli/cmds_backend.py",
        "src/xsarena/cli/cmds_book.py",
        "src/xsarena/cli/cmds_continue.py",
        "src/xsarena/cli/cmds_debug.py",
        "src/xsarena/cli/cmds_fix.py",
        "src/xsarena/cli/cmds_jobs.py",
        "src/xsarena/cli/cmds_report.py",
        "src/xsarena/cli/cmds_adapt.py",
        "src/xsarena/cli/cmds_boot.py",
        "src/xsarena/cli/cmds_snapshot.py",
        "src/xsarena/cli/cmds_run.py",
        "src/xsarena/cli/cmds_quick.py",
        "src/xsarena/cli/cmds_plan.py",
        "src/xsarena/cli/cmds_clean.py",
        "src/xsarena/cli/cmds_config.py",
        "src/xsarena/cli/cmds_fast.py",
        "src/xsarena/cli/cmds_metrics.py",
        "src/xsarena/cli/cmds_mixer.py",
        "src/xsarena/cli/cmds_preview.py",
        "src/xsarena/cli/cmds_publish.py",
        "src/xsarena/cli/cmds_audio.py",
        "src/xsarena/cli/cmds_pipeline.py",
        "src/xsarena/cli/cmds_tools.py",
        "src/xsarena/cli/cmds_people.py",
        "src/xsarena/cli/cmds_modes.py",
        "src/xsarena/cli/cmds_lossless.py",
    ]
    
    for f in essential_cli:
        p = Path(f)
        if p.exists() and p.is_file():
            files.append(p)
    
    # Add specific files
    specific_files = ["tools/min_snapshot.py", "pyproject.toml", "mypy.ini"]
    for f in specific_files:
        p = Path(f)
        if p.exists() and p.is_file():
            files.append(p)
    
    # Add essential .sh files under scripts/ (limit to essential ones)
    essential_scripts = [
        "scripts/merge_session_rules.sh",
        "scripts/gen_docs.sh",
        "scripts/prepush_check.sh",
    ]
    for f in essential_scripts:
        p = Path(f)
        if p.exists() and p.is_file():
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
    """Collect all .yml files under recipes/ (only small ones)"""
    files: list[Path] = []
    
    recipes_dir = Path("recipes")
    if recipes_dir.exists():
        for p in recipes_dir.rglob("*.yml"):
            if p.is_file():
                # Only include if file is reasonably small
                if p.stat().st_size < 50000:  # 50KB limit per recipe
                    files.append(p)
    
    return files


def _collect_review_files() -> list[Path]:
    """Collect all .txt/.json files under review/ (only small ones)"""
    files: list[Path] = []
    
    review_dir = Path("review")
    if review_dir.exists():
        for ext in [".txt", ".json"]:
            for p in review_dir.rglob(f"*{ext}"):
                if p.is_file():
                    # Only include if file is reasonably small
                    if p.stat().st_size < 20000:  # 20KB limit per review file
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
        w.write("XSArena Minimal Snapshot (Optimized)\n")
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

        # Write LS (file lists) for the same directories (limit output size)
        w.write("===== LS (books|recipes|directives|.xsarena/jobs|review) =====\n")
        for name in tree_dirs:
            rp = Path(name)
            if rp.exists():
                files = sorted([*rp.rglob("*")], key=lambda x: str(x).lower())
                # Limit the number of files listed to keep size down
                for p in files[:50]:  # Only first 50 files per directory
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
    
    # Print size info
    size = out.stat().st_size
    print(f"Snapshot size: {size} bytes ({size/1024:.1f} KB)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) > 1 else main())