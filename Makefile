.PHONY: setup fmt lint test docs health bridge
setup:
 @src/xsarena/cli/cmds_pipeline.py install -U pip && pip install -e ".[dev]"
fmt:
 @ruff --fix . || true && black .
lint:
 @ruff check . && black --check . && mypy .
test:
 @pytest -q
docs:
 @bash scripts/gen_docs.sh
health:
 @SNAP_TXT=.xsarena/snapshots/final_snapshot.txt bash healthcheck_script.sh
bridge:
 @legacy/xsarena_cli.py service start-bridge
