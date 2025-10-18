#!/bin/bash
echo "Generating CLI help documentation..."
xsarena --help > docs/_help_root.txt || true
xsarena service --help > docs/_help_serve.txt || true
xsarena snapshot --help > docs/_help_snapshot.txt || true
xsarena jobs --help > docs/_help_jobs.txt || true
xsarena doctor --help > docs/_help_doctor.txt || true
xsarena book --help > docs/_help_z2h.txt || true
xsarena interactive --help > docs/_help_interactive.txt || true
echo "Done."
