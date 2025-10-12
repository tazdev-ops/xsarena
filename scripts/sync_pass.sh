#!/usr/bin/env bash
set -euo pipefail
mkdir -p .sync docs/_help_cache
# 1) top-level scan
timeout 10s bash -lc 'find . -maxdepth 1 -mindepth 1 \( -type d -o -type f \) | sed "s#^\\./##" | sort > .sync/_top.txt'
echo "[sync] top-level list → .sync/_top.txt"
# 2) help scrape (for README drift)
timeout 60s xsarena --help | tee docs/_help_root.txt >/dev/null || true
# Extract subcommands (best-effort):
awk '/Commands:/,0' docs/_help_root.txt | sed '1d' | awk '{print $1}' | sed 's/[:]$//' | sort -u > .sync/_subs.txt || true
while read -r sub; do
  [[ -z "$sub" ]] && continue
  timeout 60s xsarena "$sub" --help > "docs/_help_${sub}.txt" || true
done < .sync/_subs.txt
echo "[sync] help cached in docs/_help_*.txt (non-fatal if missing)"
# 3) .gitignore check (propose; don't write)
echo "[sync] PROPOSE add ignores if missing:"
for pat in "xsarena.egg-info/" "docs/_help_*.txt" ".xsarena/agent/journal*.jsonl" ".xsarena/agent/session_*.md" ".ruff_cache/" ".pytest_cache/" "snapshot_chunks/"; do
  if ! grep -qF "$pat" .gitignore 2>/dev/null; then
    echo "  + $pat"
  fi
done
# 4) snapshot excludes (print canonical)
echo "[sync] Snapshot excludes should include: .git, __pycache__, books, dist, build, node_modules, snapshot_chunks, .xsarena (except SNAPSHOT+JOBS)."
# 5) docs index presence (print missing)
for f in README.md CLI_AGENT_RULES.md docs/SHORTCUTS.md docs/RUNBOOKS.md docs/SNAPSHOT_POLICY.md docs/TROUBLESHOOTING.md docs/AGENT_JOURNAL.md docs/HANDOFF.md docs/INBOX.md docs/OUTBOX.md docs/PROFILES.md DEPRECATIONS.md; do
  [[ -e "$f" ]] || echo "[sync] missing doc: $f"
done
echo "[sync] Done. Review proposals and apply with your rules."
