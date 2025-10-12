#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "legacy"
CONTRIB_TUI = ROOT / "contrib" / "tui"


def ensure_dirs():
    LEGACY.mkdir(parents=True, exist_ok=True)
    CONTRIB_TUI.mkdir(parents=True, exist_ok=True)


def backup_if_exists(p: Path):
    if p.exists():
        ts = time.strftime("%Y%m%d-%H%M%S")
        bak = p.with_suffix(p.suffix + f".bak.{ts}")
        try:
            shutil.copy2(p, bak)
            return str(bak)
        except Exception:
            return None
    return None


def move_if_exists(src: Path, dst: Path):
    if not src.exists():
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    # if same file already there, skip
    if dst.exists():
        return f"already @ {dst}"
    shutil.move(str(src), str(dst))
    return f"moved → {dst}"


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def stub_xsarena_tui():
    path = ROOT / "xsarena_tui.py"
    content = """#!/usr/bin/env python3
import sys, runpy
print("Deprecated: TUI moved to contrib/tui/xsarena_tui.py; prefer `xsarena serve`.", file=sys.stderr)
sys.exit(runpy.run_path("contrib/tui/xsarena_tui.py") or 0)
"""
    write_file(path, content)
    try:
        os.chmod(path, 0o755)
    except Exception:
        pass


def stub_lma_tui():
    path = ROOT / "lma_tui.py"
    content = """#!/usr/bin/env python3
import sys, runpy
print("Deprecated: LMA TUI moved to legacy/lma_tui.py; prefer `xsarena serve`.", file=sys.stderr)
sys.exit(runpy.run_path("legacy/lma_tui.py") or 0)
"""
    write_file(path, content)
    try:
        os.chmod(path, 0o755)
    except Exception:
        pass


def write_deprecations():
    p = ROOT / "DEPRECATIONS.md"
    text = """# DEPRECATIONS

These entrypoints are deprecated and retained for one release cycle.

- xsarena_tui.py — moved to contrib/tui/xsarena_tui.py. Prefer `xsarena serve` for web preview.
- lma_tui.py — moved to legacy/lma_tui.py (compat only).
- lma_cli.py — already a deprecation shim; prefer `xsarena`.
- lma_stream.py / lma_templates.py — retained for compatibility with legacy clients; will be pruned in a later phase.

Policy: Keep shims one cycle with a stderr warning, then remove once downstream scripts are updated.
"""
    write_file(p, text)


def fix_init_docstring():
    initp = ROOT / "src" / "xsarena" / "__init__.py"
    if not initp.exists():
        return "skip (file not found)"
    txt = initp.read_text(encoding="utf-8")
    new = txt.replace("LMASudio", "XSArena")
    if new != txt:
        backup_if_exists(initp)
        write_file(initp, new)
        return "docstring fixed"
    return "ok (unchanged)"


def main():
    print("== declutter phase 1 ==")
    ensure_dirs()

    # Moves
    results = {}
    results["xsarena_tui.py"] = move_if_exists(
        ROOT / "xsarena_tui.py", CONTRIB_TUI / "xsarena_tui.py"
    )
    results["lma_tui.py"] = move_if_exists(ROOT / "lma_tui.py", LEGACY / "lma_tui.py")

    # Stubs
    stub_xsarena_tui()
    stub_lma_tui()

    # Docs + init fix
    write_deprecations()
    init_status = fix_init_docstring()

    print("Moves:", results)
    print("init:", init_status)
    print("Done. Phase 1 complete.")


if __name__ == "__main__":
    sys.exit(main() or 0)
