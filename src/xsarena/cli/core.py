"""
Console script entry point for xsarena interactive CLI.
This module provides the main entry point for the console script.
"""

import sys
import os
import subprocess

def main():
    """Main entry point for the xsarena console script."""
    # Find the xsarena_cli.py file in the project root
    # The __file__ is in src/xsarena/cli/core.py, so go up 3 levels to get to project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    script_path = os.path.join(project_root, 'xsarena_cli.py')
    
    # Execute the script with subprocess
    result = subprocess.run([sys.executable, script_path] + sys.argv[1:])
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()