#!/usr/bin/env python3
import sys

try:
    from xsarena.cli.main import run  # canonical
except Exception:
    # Fallback if import path differs in your tree
    from src.xsarena.cli.main import run  # type: ignore

if __name__ == "__main__":
    print(
        "Deprecated: use `xsarena` (this wrapper calls xsarena.cli.main:run).",
        file=sys.stderr,
    )
    run()
