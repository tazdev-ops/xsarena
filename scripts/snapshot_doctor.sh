#!/usr/bin/env bash
set -euo pipefail
SNAP="${1:-$HOME/snapshot.txt}"
CHDIR="${2:-$HOME/snapshot_chunks}"
limit="${SNAP_LIMIT:-110000}"

echo "== Snapshot Doctor =="
echo "Snapshot: $SNAP"
echo "Chunks dir: $CHDIR"
echo "Limit (chars): $limit"
echo

if [[ -f "$SNAP" ]]; then
  echo "-- Header preview --"
  sed -n '1,80p' "$SNAP"
  echo
  echo "-- Chunk markers --"
  grep -n '^== CHUNK ' "$SNAP" | tee /tmp/chunk_idx.txt || true
  echo "Chunks (count): $(wc -l < /tmp/chunk_idx.txt)"
  echo
  echo "-- Manifest markers --"
  grep -h '^MANIFEST_SHA256:' "$SNAP" 2>/dev/null | sort -u || true
  echo
  echo "-- BEGIN/END counts --"
  echo -n "BEGIN: "; grep -c '^--- BEGIN FILE ' "$SNAP" || true
  echo -n "END:   "; grep -c '^--- END FILE ' "$SNAP" || true
  echo
  echo "-- Longest line (chars) --"
  awk '{ if (length > L) L=length } END { print L }' "$SNAP"
  echo
fi

if [[ -d "$CHDIR" ]]; then
  echo "-- Chunk size (chars) --"
  wc -m "$CHDIR"/snapshot_part_* 2>/dev/null | sort -n | tail -n 10 || true
  echo "-- Chunk size (bytes) --"
  wc -c "$CHDIR"/snapshot_part_* 2>/dev/null | sort -n | tail -n 10 || true
  echo "-- Manifest markers in chunks --"
  grep -h '^MANIFEST_SHA256:' "$CHDIR"/snapshot_part_* 2>/dev/null | sort -u || true
fi

echo
echo "-- Verify --"
python -m xsarena.utils.snapshot_pro verify --out "$SNAP" --chunks "$CHDIR" || true

echo
# Verdict rules
FAIL=0
LL=$(awk '{ if (length > L) L=length } END { print L }' "$SNAP" 2>/dev/null || echo 0)
if [[ "$LL" -gt 10000 ]]; then echo "FAIL: Longest line > 10k chars ($LL)"; FAIL=1; fi

if ls "$CHDIR"/snapshot_part_* >/dev/null 2>&1; then
  while read -r n c; do
    if [[ "$n" == "total" ]]; then continue; fi
    if [[ "$c" -gt "$limit" ]]; then echo "FAIL: $n exceeds limit ($c > $limit chars)"; FAIL=1; fi
  done < <(wc -m "$CHDIR"/snapshot_part_* 2>/dev/null | awk '{print $2, $1}')
fi

if [[ "$FAIL" -eq 0 ]]; then
  echo "OK: Snapshot looks healthy under current policy."
else
  echo "ERR: Snapshot policy violations detected."
  exit 2
fi
