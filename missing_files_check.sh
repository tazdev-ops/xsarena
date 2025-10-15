#!/usr/bin/env bash
set -euo pipefail

# 0) Paths
OUT_DIR="review"
KNOWN="$OUT_DIR/assistant_known_files.quick.txt"
ALL="$OUT_DIR/all_files.quick.list"
MISS="$OUT_DIR/missing_files.quick.list"

mkdir -p "$OUT_DIR"

# 1) Seed: files the assistant already knows (best‑effort)
cat > "$KNOWN" <<'LIST'
mypy.ini
pyproject.toml
models.json
tools/min_snapshot.py
tools/snapshot_pro.py
tools/situation_report.py
scripts/gen_docs.sh
scripts/merge_session_rules.sh
scripts/prepush_check.sh
directives/_rules/rules.merged.md
recipes/america-political-history.yml
recipes/arche_professor.yml
recipes/britain-political-history.yml
recipes/clinical.en.yml
recipes/mastery.yml
recipes/mixer_modern-political-history-of-britain-elections-and-power-c-1832-present.yml
recipes/mixer_quick-test.yml
recipes/mixer_test-subject.yml
recipes/psychology_masters_clinical.yml
recipes/role_launcher.yml
recipes/fast_psychology-foundations-to-master-s-clinical-focus.yml
src/xsarena/cli/cmds_adapt.py
src/xsarena/cli/cmds_audio.py
src/xsarena/cli/cmds_backend.py
src/xsarena/cli/cmds_book.py
src/xsarena/cli/cmds_boot.py
src/xsarena/cli/cmds_clean.py
src/xsarena/cli/cmds_config.py
src/xsarena/cli/cmds_continue.py
src/xsarena/cli/cmds_debug.py
src/xsarena/cli/cmds_fast.py
src/xsarena/cli/cmds_fix.py
src/xsarena/cli/cmds_jobs.py
src/xsarena/cli/cmds_lossless.py
src/xsarena/cli/cmds_metrics.py
src/xsarena/cli/cmds_mixer.py
src/xsarena/cli/cmds_modes.py
src/xsarena/cli/cmds_people.py
src/xsarena/cli/cmds_pipeline.py
src/xsarena/cli/cmds_plan.py
src/xsarena/cli/cmds_preview.py
src/xsarena/cli/cmds_publish.py
src/xsarena/cli/cmds_quick.py
src/xsarena/cli/cmds_report.py
src/xsarena/cli/cmds_run.py
src/xsarena/cli/cmds_snapshot.py
src/xsarena/cli/cmds_tools.py
src/xsarena/cli/context.py
src/xsarena/cli/main.py
src/xsarena/core/artifacts.py
src/xsarena/core/backends.py
src/xsarena/core/chunking.py
src/xsarena/core/config.py
src/xsarena/core/engine.py
src/xsarena/core/jobs2_runner.py
src/xsarena/core/orchestrator.py
src/xsarena/core/profiles.py
src/xsarena/core/prompt.py
src/xsarena/core/recipes.py
src/xsarena/core/redact.py
src/xsarena/core/specs.py
src/xsarena/core/state.py
src/xsarena/core/templates.py
src/xsarena/core/tools.py
LIST

# 2) Build repo file list (text/code only), sorted
git ls-files -co --exclude-standard \
| awk '/\.(md|markdown|txt|yml|yaml|json|py|toml|ini|js|sh)$/' \
| sort -u > "$ALL"

# 3) Compute "assistant-missing" files (repo − known)
sort -u "$KNOWN" -o "$KNOWN"
comm -23 "$ALL" "$KNOWN" > "$MISS"

echo "=== Missing files (vs assistant-known seed) ==="
if [ -s "$MISS" ]; then
  nl -ba "$MISS"
else
  echo "(none)"
fi
echo

# 4) Print all rule-related files
echo "=== Rule files (canonical + sources + styles/roles/quickref/profiles) ==="
# Canonical merged + sources
[ -f directives/_rules/rules.merged.md ] && echo "directives/_rules/rules.merged.md"
find directives/_rules -type f -print 2>/dev/null | sort -f || true
# Style/role/quickref/profile cards commonly used by rules
find directives -maxdepth 1 -type f -name "style*.md" -print 2>/dev/null | sort -f || true
find directives/roles directives/quickref directives/profiles -type f -name "*.md" -print 2>/dev/null | sort -f || true
echo

# 5) Remove other snapshotting utilities and their outputs (keep situation_report)
echo "=== Removing other snapshot utilities and outputs ==="
REMOVED=0
remove_if() { [ -e "$1" ] && { rm -f "$1" && echo "rm $1"; REMOVED=$((REMOVED+1)); }; }

# Utilities to remove
for f in \
  tools/min_snapshot.py \
  tools/minimal_snapshot.py \
  tools/minimal_snapshot_optimized.py \
  tools/snapshot_chunk.py \
  tools/chunk_with_message.py \
  tools/snapshot_pro.py
do
  remove_if "$f"
done

# Known outputs (home + repo review)
remove_if "$HOME/xsa_min_snapshot.txt"
remove_if "$HOME/xsa_snapshot_pro.txt"
remove_if "$HOME/xsa_snapshot_pro.txt.tar.gz"
# Review artifacts created by snapshot_pro or prior probes
find review -maxdepth 1 -type f \( \
  -name "xsa_snapshot_pro*.txt" -o \
  -name "xsa_snapshot_pro*.txt.tar.gz" -o \
  -name "missing_from_assistant_snapshot*.txt" -o \
  -name "xsa_min_snapshot*.txt" \
\) -print -delete 2>/dev/null || true

echo "Removed items: $REMOVED"
echo
echo "[done]"