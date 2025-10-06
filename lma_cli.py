#!/usr/bin/env python3
import sys
import subprocess

if __name__ == "__main__":
    print("Deprecated: use `xsarena` (this wrapper calls xsarena).", file=sys.stderr)
    result = subprocess.run(["xsarena"] + sys.argv[1:])
    sys.exit(result.returncode)