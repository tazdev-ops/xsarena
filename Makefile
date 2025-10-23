.PHONY: bridge book dry continue snap verify jobs lint lint-fix snapshot-ultra snapshot-pro debloat-plan debloat-apply
bridge: ; xsarena ops service start-bridge-v2
book:   ; xsarena run book "$(SUBJECT)" --length long --span book --dry-run
dry:    ; xsarena run book "$(SUBJECT)" --dry-run
continue: ; xsarena run continue "$(BOOK)" --length long --span book --wait false --follow
snap:   ; xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000
verify: ; xsarena ops snapshot verify
jobs:   ; xsarena ops jobs ls
lint:   ; python -m ruff check . --output-format=concise
lint-fix: ; python -m ruff check . --fix --output-format=concise

# Snapshot Reform targets
snapshot-ultra: ## Create ultra-tight snapshot (for sharing)
	@echo "Creating ultra-tight snapshot..."
	xsarena ops snapshot verify --mode ultra-tight --max-per-file 180000 --total-max 2500000 --fail-on oversize --fail-on disallowed --fail-on binary --fail-on missing_required --quiet && \\
	xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt && \\
	xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected --quiet
	@echo "Ultra-tight snapshot created at ~/repo_flat.txt"

snapshot-pro: ## Create debug report (for development)
	@echo "Creating debug report..."
	xsarena ops snapshot debug-report --out ~/xsa_debug_report.txt
	@echo "Debug report created at ~/xsa_debug_report.txt"

# Debloat targets
debloat-plan:
	@python3 tools/debloat_scan.py | tee debloat_plan.json

debloat-apply:
	@python3 - <<'PY'
import json, os, sys
from pathlib import Path
plan = json.load(open("debloat_plan.json"))
to_remove = []
for c in plan.get("candidates", []):
    if not c["referenced"]:
        to_remove.append(c["path"])
if not to_remove:
    print("No safe removals detected.")
    sys.exit(0)
print("Will remove:")
for p in to_remove:
    print(" -", p)
for p in to_remove:
    try:
        Path(p).unlink()
    except Exception as e:
        print("[warn] could not remove", p, e)
PY
