.PHONY: bridge book dry continue snap verify jobs snapshot-ultra snapshot-pro
bridge: ; xsarena ops service start-bridge-v2
book:   ; xsarena run book "$(SUBJECT)" --length long --span book --dry-run
dry:    ; xsarena run book "$(SUBJECT)" --dry-run
continue: ; xsarena run continue "$(BOOK)" --length long --span book --wait false --follow
snap:   ; xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --no-repo-map
verify: ; xsarena ops snapshot verify
jobs:   ; xsarena ops jobs ls

# Snapshot Reform targets
snapshot-ultra: ## Create ultra-tight snapshot (for sharing)
	@echo "Creating ultra-tight snapshot..."
	xsarena ops snapshot verify --mode author-core --policy .xsarena/ops/snapshot_policy.yml --quiet && \\
	xsarena ops snapshot create --mode ultra-tight --total-max 2500000 --max-per-file 180000 --out ~/repo_flat.txt --no-repo-map && \\
	xsarena ops snapshot verify --file ~/repo_flat.txt --max-per-file 180000 --fail-on oversize --fail-on secrets --redaction-expected --quiet
	@echo "Ultra-tight snapshot created at ~/repo_flat.txt"

snapshot-pro: ## Create debug report (for development)
	@echo "Creating debug report..."
	xsarena ops snapshot debug-report --out ~/xsa_debug_report.txt
	@echo "Debug report created at ~/xsa_debug_report.txt"
