#!/usr/bin/env python3
import sys
import subprocess

if __name__ == "__main__":
    print("Deprecated: use `python xsarena_tui.py` (this wrapper calls xsarena_tui.py).", file=sys.stderr)
    result = subprocess.run([sys.executable, "xsarena_tui.py"] + sys.argv[1:])
    sys.exit(result.returncode)