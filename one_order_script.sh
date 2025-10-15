#!/usr/bin/env bash
set -euo pipefail

TS="$(date -u +'%Y%m%d-%H%M%S')"
OUT_DIR="review"
SNAP_TXT="$OUT_DIR/xsa_snapshot_pro.$TS.txt"
SNAP_TGZ="$SNAP_TXT.tar.gz"
MAP_DOC="docs/PROJECT_MAP.md"
MAP_SUM="$OUT_DIR/PROJECT_MAP_SUMMARY.$TS.md"
HEALTH="$OUT_DIR/SNAPSHOT_HEALTHCHECK.$TS.md"

mkdir -p "$OUT_DIR" docs

echo "=== 1) Baseline investigation ==="
# Ensure canonical rules merged if merge script exists
if [ -x scripts/merge_session_rules.sh ]; then
  bash scripts/merge_session_rules.sh || true
fi
# Startup + drift + backend
xsarena boot read || true
xsarena adapt inspect --no-save || true
xsarena backend test || true
# Optional checks (best-effort)
xsarena config show || true
xsarena debug state || true
xsarena checklist status || true 2>/dev/null || true

echo "=== 2) Explanation from docs → maps ==="
# Rebuild CLI help if possible (best‑effort)
if [ -x scripts/gen_docs.sh ]; then
  bash scripts/gen_docs.sh || true
fi

{
  echo "# Project Map (from documentation)"
  echo "Generated: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
  echo
  # Sources: adjust list as needed
  for f in README.md MODULES.md ARCHITECTURE.md STATE.md CONFIG_REFERENCE.md docs/INDEX.md docs/QUICK_GUIDE.md docs/STYLES.md docs/AGENT_MANUAL.md; do
    if [ -f "$f" ]; then
      echo "## Source: $f"
      # Headings + bullets
      awk '/^#/{print} /^- |^[0-9]+\./{print}' "$f" | sed -e 's/^[[:space:]]\{1,\}//' | head -n 250
      echo
    fi
  done
  echo "## CLI Surface (from docs/_help_*.txt)"
  for hf in docs/_help_*.txt; do
    [ -f "$hf" ] && { echo "### $(basename "$hf")"; sed -n '1,80p' "$hf"; echo; }
  done
  echo "## Canonical Rules (head)"
  if [ -f directives/_rules/rules.merged.md ]; then
    sed -n '1,120p' directives/_rules/rules.merged.md
  else
    echo "(rules.merged.md missing)"
  fi
} > "$MAP_DOC"

# Compressed summary (dense)
awk 'NF' "$MAP_DOC" | head -n 400 > "$MAP_SUM"

echo "Wrote maps:"
echo " - $MAP_DOC"
echo " - $MAP_SUM"

echo "=== 3) Snapshot run (existing code; no changes) ==="
python - <<'PY'
import sys, pathlib
p = pathlib.Path("tools/snapshot_pro.py")
assert p.exists(), "tools/snapshot_pro.py missing"
print("snapshot_pro.py present")
PY

python tools/snapshot_pro.py --out "$SNAP_TXT" --tar
test -f "$SNAP_TXT" || { echo "[err] snapshot text missing"; exit 1; }
[ -f "$SNAP_TGZ" ] && echo "Snapshot tar.gz: $SNAP_TGZ" || echo "[warn] snapshot tar.gz not created"

echo "=== 4) Health‑check snapshot content & references ==="
{
  echo "# Snapshot Healthcheck"
  echo "Generated: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
  echo "Snapshot: $SNAP_TXT"
  echo

  echo "## Section presence"
  sections=("===== TREE " "===== LS" "===== RULES DIGEST" "===== CONFIG & SESSION" "===== RECIPES DIGEST" "===== BOOKS SAMPLES" "===== REVIEW SIGNALS" "===== JOBS SUMMARY" "===== MANIFEST (CODE)" "===== SNAPSHOT DIGEST:")
  for key in "${sections[@]}"; do
    if grep -qF "$key" "$SNAP_TXT"; then
      echo "- [$key] OK"
    else
      echo "- [$key] MISSING"
    fi
  done
  echo

  echo "## Code manifest sanity"
  MAN_LINES=$(awk '/^===== MANIFEST \(CODE\) =====/{flag=1;next}/^===== SNAPSHOT DIGEST:/{flag=0}flag' "$SNAP_TXT" | wc -l | tr -d ' ')
  echo "- manifest lines: $MAN_LINES"
  echo "- sample verification:"
  awk '/^===== MANIFEST \(CODE\) =====/{flag=1;next}/^===== SNAPSHOT DIGEST:/{flag=0}flag' "$SNAP_TXT" | head -n 5 | \
  while read -r path hash; do
    if [ -f "$path" ]; then
      calc=$(python - "$path" <<'PY'
import sys, hashlib
from pathlib import Path
p=Path(sys.argv[1])
h=hashlib.sha256()
with p.open("rb") as f:
  for chunk in iter(lambda:f.read(65536), b""):
    h.update(chunk)
print(h.hexdigest())
PY
)
      if [ "$calc" = "$hash" ]; then
        echo "  • OK: $path"
      else
        echo "  • HASH-MISMATCH: $path"
      fi
    else
      echo "  • MISSING-FILE: $path"
    fi
  done
  echo

  echo "## Rules digest presence"
  if grep -q "===== RULES DIGEST =====" "$SNAP_TXT"; then
    echo "- rules digest present"
  else
    echo "- rules digest missing"
  fi
  echo

  echo "## Jobs summary check"
  if grep -q "===== JOBS SUMMARY =====" "$SNAP_TXT"; then
    if [ -d ".xsarena/jobs" ]; then
      JCOUNT=$(find .xsarena/jobs -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
      echo "- jobs dir present: $JCOUNT job dir(s)"
      echo "- spot-check last events:"
      sed -n '/===== JOBS SUMMARY =====/,/===== END JOBS SUMMARY =====/p' "$SNAP_TXT" | grep -n "Last events:" | head -n 5 || echo "  (no last events lines found)"
    else
      echo "- jobs dir missing; snapshot should show (none)"
    fi
  else
    echo "- jobs summary section missing"
  fi
  echo

  echo "## Books and recipes presence"
  grep -q "===== BOOKS SAMPLES =====" "$SNAP_TXT" && echo "- books samples present" || echo "- books samples missing"
  grep -q "===== RECIPES DIGEST =====" "$SNAP_TXT" && echo "- recipes digest present" || echo "- recipes digest missing"
  echo

  echo "## LS referential spot-check"
  awk '/^===== LS \(selected\) =====/{flag=1;next}/^===== END LS =====/{flag=0}flag' "$SNAP_TXT" | shuf -n 10 | \
  while read -r f; do
    [ -f "$f" ] && echo "  • OK: $f" || echo "  • MISSING (listed in LS but not found): $f"
  done
  echo

  echo "## Final snapshot digest"
  awk '/^===== SNAPSHOT DIGEST:/{print}' "$SNAP_TXT" || echo "(digest line missing)"
} > "$HEALTH"

echo "Wrote healthcheck → $HEALTH"

echo "=== 5) Ensure final diagnostic report bundle exists and validate ==="
# Generate a fresh redacted report bundle
xsarena report quick || true
LATEST_TGZ="$(ls -1t review/report_*.tar.gz 2>/dev/null | head -n 1 || true)"
if [ -n "${LATEST_TGZ:-}" ] && [ -f "$LATEST_TGZ" ]; then
  echo "Final report bundle: $LATEST_TGZ" | tee -a "$HEALTH"
  # Validate tar contents minimally
  echo "## Final report contents:" >> "$HEALTH"
  tar -tzf "$LATEST_TGZ" | sort | sed -n '1,200p' >> "$HEALTH" || echo "[warn] tar list failed" >> "$HEALTH"
  # Required files (at least one of these sets)
  NEED=("config.yml" "session_state.json")
  MISS=0
  for req in "${NEED[@]}"; do
    if ! tar -tzf "$LATEST_TGZ" | grep -q "/$req$"; then
      echo "[warn] missing in report: $req" | tee -a "$HEALTH"
      MISS=1
    fi
  done
  if [ "$MISS" -eq 0 ]; then
    echo "Report minimal set present (config.yml, session_state.json)" | tee -a "$HEALTH"
  fi
else
  echo "[warn] No report tar.gz found under review/" | tee -a "$HEALTH"
fi

echo
echo "=== DONE ==="
echo "Snapshot: $SNAP_TXT"
[ -f "$SNAP_TGZ" ] && echo "Snapshot tar.gz: $SNAP_TGZ" || true
echo "Project map: $MAP_DOC"
echo "Map summary: $MAP_SUM"
echo "Healthcheck: $HEALTH"
echo "Final report: ${LATEST_TGZ:-'(missing)'}"