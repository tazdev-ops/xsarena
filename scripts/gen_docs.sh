#!/bin/bash
echo "Generating CLI help documentation..."
xsarena --help > docs/_help_root.txt || true
xsarena doctor --help > docs/_help_doctor.txt || true
xsarena interactive --help > docs/_help_interactive.txt || true
echo "Done."