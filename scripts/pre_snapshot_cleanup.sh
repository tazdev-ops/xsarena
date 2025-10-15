#!/usr/bin/env bash
set -euo pipefail
APPLY="${APPLY:-}"
say(){ echo "$@"; }
do_rm(){ [[ -n "$APPLY" ]] && rm -f "$@" || :; }
do_rmdir(){ [[ -n "$APPLY" ]] && rmdir "$@" 2>/dev/null || true; }
say "== Pre-snapshot cleanup (dry-run unless APPLY=1) =="
for pat in situation_report.*.txt situation_report.*.health situation_report.*.part* xsa_snapshot_pro*.txt xsa_snapshot_pro*.txt.tar.gz xsa_min_snapshot*.txt xsa_final_snapshot*.txt xsa_final_cleanup_snapshot*.txt; do
  for f in $pat; do [[ -e "$f" ]] && { say " - root: $f"; do_rm "$f"; }; done
done
if [[ -d snapshot_chunks ]]; then find snapshot_chunks -type f -print -exec bash -lc '[[ -n "$APPLY" ]] && rm -f "$0"' {} \; ; do_rmdir snapshot_chunks || true; say " - cleaned snapshot_chunks/"; fi
for pat in "$HOME/xsa_min_snapshot*.txt" "$HOME/xsa_snapshot_pro*.txt" "$HOME/xsa_snapshot_pro*.txt.tar.gz" "$HOME/situation_report.*.txt" "$HOME/situation_report.*.txt.part*"; do
  for f in $pat; do [[ -e "$f" ]] && { say " - home: $f"; do_rm "$f"; }; done
done
[[ -z "$APPLY" ]] && say "(dry-run) Set APPLY=1 to delete" || say "[OK ] deletions applied"
