#!/usr/bin/env bash
TS="$(date -u +'%Y%m%d-%H%M%S')"
OUT_DIR="review"
SNAP_TXT="${SNAP_TXT:-.xsarena/snapshots/final_snapshot.txt}"
HEALTH="$OUT_DIR/SNAPSHOT_HEALTHCHECK.$TS.md"

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