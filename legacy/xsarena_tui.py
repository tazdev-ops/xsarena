#!/usr/bin/env python3
import runpy
import sys

print(
    "Deprecated: TUI moved to contrib/tui/xsarena_tui.py; prefer `xsarena serve`.",
    file=sys.stderr,
)
sys.exit(runpy.run_path("contrib/tui/xsarena_tui.py") or 0)
