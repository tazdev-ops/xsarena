#!/usr/bin/env python3
import runpy
import sys

print(
    "Deprecated: LMA TUI moved to legacy/lma_tui.py; prefer `xsarena serve`.",
    file=sys.stderr,
)
sys.exit(runpy.run_path("legacy/lma_tui.py") or 0)
